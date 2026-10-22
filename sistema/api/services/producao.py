"""
Regras da produção: gera as pizzas do pedido, guarda a fila, calcula o saldo de massa aberta e a estimativa de entrega.
A unidade de trabalho é a pizza (ou calzone). Bebida e acompanhamento não entram na produção.
"""
import math
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from api.services.parametros import vigentes

MOTIVOS_RETROCESSO_PADRAO = (("Falta de insumo", True), ("Saída do pizzaiolo", False), ("Erro na borda", False), ("Outros", False))
MOTIVOS_PERDA_PADRAO = ("Queimou", "Saiu errada", "Caiu", "Outros")
MOTIVO_CANCELAMENTO = "Cancelamento do pedido"
EM_ANDAMENTO = ("em montagem", "no forno", "saiu do forno", "acabada")


def evento(conn, pizza_id: int, situacao: str, usuario_id, quando) -> None:
    conn.execute("INSERT INTO evento_producao (pizza_id, situacao, usuario_id, criado_em) VALUES (%s,%s,%s,%s)",
                 (pizza_id, situacao, usuario_id, quando))


def mover(conn, pizza_id: int, nova: str, usuario_id, quando, responsavel="manter") -> None:
    if responsavel == "manter":
        conn.execute("UPDATE pizza_producao SET situacao = %s WHERE id = %s", (nova, pizza_id))
    else:
        conn.execute("UPDATE pizza_producao SET situacao = %s, responsavel_id = %s WHERE id = %s", (nova, responsavel, pizza_id))
    evento(conn, pizza_id, nova, usuario_id, quando)


def _proxima_ordem(conn, loja_id: int) -> Decimal:
    conn.execute("SELECT pg_advisory_xact_lock(5, %s)", (loja_id,))  # duas recepções não geram a mesma posição
    return conn.execute("SELECT COALESCE(max(ordem), 0) + 1 AS o FROM pizza_producao WHERE loja_id = %s", (loja_id,)).fetchone()["o"]


def gerar_pizzas(conn, loja_id: int, pedido_id: int, usuario_id, quando) -> int:
    """Uma linha por pizza ou calzone de cada item (quantidade 3 vira 3 pizzas). Mesma transação do pedido."""
    itens = conn.execute("SELECT id, tipo, tamanho, descricao, quantidade, observacoes FROM item_pedido "
                         "WHERE pedido_id = %s AND tipo IN ('pizza','calzone') ORDER BY seq", (pedido_id,)).fetchall()
    n = 0
    for it in itens:
        sabores = it["descricao"].split(": ", 1)[-1]
        ad = ", ".join(r["nome"] for r in conn.execute("SELECT nome FROM item_adicional WHERE item_id = %s ORDER BY id", (it["id"],)).fetchall()) or None
        for _ in range(it["quantidade"]):
            ordem = _proxima_ordem(conn, loja_id)
            novo = conn.execute(
                "INSERT INTO pizza_producao (loja_id, pedido_id, item_id, tipo, tamanho, sabores, adicionais, observacoes, ordem, criado_em) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (loja_id, pedido_id, it["id"], it["tipo"], it["tamanho"], sabores, ad, it["observacoes"], ordem, quando)).fetchone()
            evento(conn, novo["id"], "na lista", usuario_id, quando)
            n += 1
    return n


def estimativa_entrega(conn, loja_id: int, tipo_pedido: str, quando, novas: int):
    """Pizzas na frente divididas pelos pizzaiolos, mais forno, acabamento e deslocamento. Sem os parâmetros, não estima."""
    p = vigentes(conn, loja_id)
    chaves = ("producao_montagem_min", "producao_pizzaiolos_ativos", "forno_tempo_min", "producao_acabamento_min")
    if any(p[c]["valor"] is None for c in chaves) or (tipo_pedido == "entrega" and p["entrega_deslocamento_min"]["valor"] is None):
        return None
    na_frente = conn.execute("SELECT count(*) AS n FROM pizza_producao WHERE loja_id = %s AND situacao IN ('na lista','em montagem')",
                             (loja_id,)).fetchone()["n"]  # já inclui as pizzas deste pedido
    rodadas = math.ceil(max(na_frente, novas) / int(p["producao_pizzaiolos_ativos"]["valor"]))
    minutos = (rodadas * Decimal(p["producao_montagem_min"]["valor"]) + Decimal(p["forno_tempo_min"]["valor"])
               + Decimal(p["producao_acabamento_min"]["valor"])
               + (Decimal(p["entrega_deslocamento_min"]["valor"]) if tipo_pedido == "entrega" else 0))
    return quando + timedelta(minutes=float(minutos))


def motivo_perda_cancelamento(conn, loja_id: int) -> int:
    r = conn.execute("SELECT id FROM motivo_perda WHERE loja_id = %s AND lower(nome) = lower(%s)", (loja_id, MOTIVO_CANCELAMENTO)).fetchone()
    if r:
        return r["id"]
    return conn.execute("INSERT INTO motivo_perda (loja_id, nome) VALUES (%s,%s) RETURNING id", (loja_id, MOTIVO_CANCELAMENTO)).fetchone()["id"]


def registrar_perda_pizza(conn, loja_id: int, pizza: dict, motivo_id: int, usuario_id, quando) -> None:
    conn.execute("INSERT INTO perda (loja_id, tipo, tamanho, quantidade, pizza_id, motivo_id, usuario_id, criado_em) VALUES (%s,'pizza',%s,1,%s,%s,%s,%s)",
                 (loja_id, pizza["tamanho"], pizza["id"], motivo_id, usuario_id, quando))


def cancelar_pizzas(conn, loja_id: int, pedido_id: int, usuario_id, quando) -> None:
    """Pedido cancelado: o que não começou some da fila; o que já foi feito vira perda, com o motivo do cancelamento."""
    for p in conn.execute("SELECT id, tamanho, situacao FROM pizza_producao WHERE pedido_id = %s AND situacao IN "
                          "('na lista','em montagem','no forno','saiu do forno','acabada') FOR UPDATE", (pedido_id,)).fetchall():
        if p["situacao"] == "na lista":
            mover(conn, p["id"], "cancelada", usuario_id, quando)
        else:
            mover(conn, p["id"], "perdida", usuario_id, quando)
            registrar_perda_pizza(conn, loja_id, p, motivo_perda_cancelamento(conn, loja_id), usuario_id, quando)


def tamanho_massa(conn, loja_id: int, p: dict):
    """Tamanho de massa que a pizza consome. O calzone depende do parâmetro; sem ele não consome massa até Marlon definir."""
    if p["tipo"] == "pizza":
        return p["tamanho"]
    return vigentes(conn, loja_id)["calzone_massa_tamanho"]["valor"]


def saldo_massa(conn, loja_id: int) -> dict:
    """Por tamanho: última contagem + lotes depois dela - massas usadas e perdidas depois dela. Necessidade vem das pizzas ainda na lista."""
    calz = vigentes(conn, loja_id)["calzone_massa_tamanho"]["valor"]
    saida = {}
    for t in ("grande", "broto"):
        c = conn.execute("SELECT quantidade, criado_em FROM contagem_massa WHERE loja_id = %s AND tamanho = %s ORDER BY id DESC LIMIT 1",
                         (loja_id, t)).fetchone()
        base, desde = (c["quantidade"], c["criado_em"]) if c else (0, None)
        filtro = "" if desde is None else " AND criado_em > %s"
        args = [] if desde is None else [desde]
        lotes = conn.execute("SELECT COALESCE(sum(quantidade),0) AS n FROM lote_massa WHERE loja_id = %s AND tamanho = %s" + filtro, [loja_id, t] + args).fetchone()["n"]
        perdas = conn.execute("SELECT COALESCE(sum(quantidade),0) AS n FROM perda WHERE loja_id = %s AND tipo = 'massa' AND tamanho = %s" + filtro, [loja_id, t] + args).fetchone()["n"]
        usadas = conn.execute(
            "SELECT count(*) AS n FROM evento_producao e JOIN pizza_producao p ON p.id = e.pizza_id WHERE p.loja_id = %s AND e.situacao = 'no forno' "
            "AND ((p.tipo = 'pizza' AND p.tamanho = %s) OR (p.tipo = 'calzone' AND %s::text = %s::text))" + filtro.replace("criado_em", "e.criado_em"),
            [loja_id, t, calz, t] + args).fetchone()["n"]
        nec = conn.execute("SELECT count(*) AS n FROM pizza_producao p WHERE p.loja_id = %s AND p.situacao = 'na lista' "
                           "AND ((p.tipo = 'pizza' AND p.tamanho = %s) OR (p.tipo = 'calzone' AND %s::text = %s::text))", (loja_id, t, calz, t)).fetchone()["n"]
        saldo = base + lotes - perdas - usadas
        saida[t] = {"saldo": saldo, "necessidade": nec, "falta": max(0, nec - saldo), "ultima_contagem": c["criado_em"] if c else None}
    return saida
