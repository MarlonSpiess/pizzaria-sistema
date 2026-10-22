"""Vendas de balcão: pedidos, pagamento dividido, desconto com limite, cancelamento e situação."""
from datetime import date
from typing import Optional

import psycopg
import psycopg.errors
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, hoje, traduzir_erro
from api.schemas import PedidoCalcular, PedidoCancelar, PedidoCreate, PedidoSituacao, PedidoUrgente
from api.security import PERMISSOES, requer
from api.services import parametros as svc_parametros
from api.services.dinheiro import fmt
from api.services.vendas import SITUACOES, autorizar, excede_limite, limite_desconto, repartir_pagamentos, totais

router = APIRouter(prefix="/pedidos", tags=["vendas"])
_COLS = ("id, data, id_dia, canal, id_canal, cliente_id, tipo, situacao, urgente, subtotal, desconto, acrescimo, taxa_entrega, "
         "taxa_motivo, total, observacoes, entrega_calculada, entrega_real, numero_cf, criado_em")
_DINHEIRO = ("subtotal", "desconto", "acrescimo", "taxa_entrega", "total")


def _out(p: dict) -> dict:
    p = dict(p)
    for c in _DINHEIRO:
        p[c] = fmt(p[c])
    return p


def _resumo_calculo(t: dict) -> dict:
    return {"itens": [{"descricao": i["descricao"], "quantidade": i["quantidade"], "preco_unit": fmt(i["preco_unit"]),
                       "adicionais": [{"nome": a["nome"], "valor": fmt(a["valor"])} for a in i["adicionais"]],
                       "total": fmt(i["preco_unit"] * i["quantidade"])} for i in t["itens"]],
            "subtotal": fmt(t["subtotal"]), "desconto": fmt(t["desconto"]), "acrescimo": fmt(t["acrescimo"]),
            "taxa_entrega": fmt(t["taxa"]), "taxa_entrega_padrao": fmt(t["taxa_padrao"]), "total": fmt(t["total"]),
            "desconto_pct": fmt(t["desconto_pct"])}


def _gerencia(sessao) -> bool:
    return "vendas.gerir" in PERMISSOES.get(sessao["perfil"], set())


def _precisa_autorizacao(sessao, t, lim) -> bool:
    """Desconto acima do limite do perfil, ou taxa de entrega abaixo do padrão (que é desconto disfarçado), sem ser gerência."""
    return excede_limite(t["desconto"], t["subtotal"], lim) or (t["tipo"] == "entrega" and t["taxa"] < t["taxa_padrao"] and not _gerencia(sessao))


@router.post("/calcular")
def calcular(d: PedidoCalcular, sessao=Depends(requer("vendas.criar")), conn=Depends(get_db)):
    """Simulação: mesmos preços e regras do pedido, sem gravar."""
    t = totais(conn, LOJA_ID, d)
    lim = limite_desconto(conn, LOJA_ID, sessao["perfil"])
    r = _resumo_calculo(t)
    r["limite_desconto_pct"] = None if lim is None else fmt(lim)
    r["precisa_autorizacao"] = _precisa_autorizacao(sessao, t, lim)
    return r


@router.post("", status_code=201)
def criar(d: PedidoCreate, request: Request, response: Response, sessao=Depends(requer("vendas.criar")), conn=Depends(get_db)):
    if d.chave:  # reenvio do mesmo pedido (duplo clique, rede lenta): devolve o que já existe
        antigo = _por_chave(conn, d.chave)
        if antigo:
            response.status_code = 200
            return antigo
    t = totais(conn, LOJA_ID, d)
    if t["total"] <= 0:
        raise HTTPException(status_code=400, detail="O total do pedido deve ser maior que zero.")
    if d.tipo == "entrega":
        if d.cliente_id is None:
            raise HTTPException(status_code=400, detail="Entrega exige cliente com endereço.")
        if t["taxa"] != t["taxa_padrao"] and not d.taxa_motivo:
            raise HTTPException(status_code=400, detail="Informe o motivo de a taxa de entrega diferir do padrão.")
    cliente = None
    if d.cliente_id is not None:
        cliente = conn.execute("SELECT id, endereco, ativo FROM cliente WHERE id = %s AND loja_id = %s",
                               (d.cliente_id, LOJA_ID)).fetchone()
        if not cliente or not cliente["ativo"]:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")
        if d.tipo == "entrega" and not cliente["endereco"]:
            raise HTTPException(status_code=400, detail="O cliente não tem endereço cadastrado.")
    formas = svc_parametros.vigentes(conn, LOJA_ID)["formas_pagamento_aceitas"]["valor"]
    pagamentos = repartir_pagamentos(t["total"], d.pagamentos, formas)
    # Acima do limite do perfil: gerente (ou acima) confirma com login e senha, antes de gravar qualquer coisa.
    autorizador = None
    lim = limite_desconto(conn, LOJA_ID, sessao["perfil"])
    if _precisa_autorizacao(sessao, t, lim):
        if not d.autorizacao:
            raise HTTPException(status_code=403, detail="Esta operação passa do seu limite (desconto ou taxa de entrega menor que a padrão). "
                                                         "Peça a autorização de um gerente.")
        autorizador = autorizar(conn, request, d.autorizacao, sessao["usuario_id"],
                                t["desconto"] if excede_limite(t["desconto"], t["subtotal"], lim) else None, t["subtotal"])
    quando, dia = agora(), hoje()
    try:
        id_dia = conn.execute(
            "INSERT INTO contador_dia (loja_id, data, ultimo) VALUES (%s, %s, 1) "
            "ON CONFLICT (loja_id, data) DO UPDATE SET ultimo = contador_dia.ultimo + 1 RETURNING ultimo",
            (LOJA_ID, dia)).fetchone()["ultimo"]
        ped = conn.execute(
            f"INSERT INTO pedido (loja_id, data, id_dia, canal, cliente_id, tipo, urgente, subtotal, desconto, acrescimo, "
            f"taxa_entrega, taxa_motivo, total, observacoes, chave, criado_em, criado_por) "
            f"VALUES (%s,%s,%s,'balcao',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {_COLS}",
            (LOJA_ID, dia, id_dia, d.cliente_id, d.tipo, d.urgente, t["subtotal"], t["desconto"], t["acrescimo"], t["taxa"],
             d.taxa_motivo, t["total"], d.observacoes, d.chave, quando, sessao["usuario_id"])).fetchone()
        for seq, (it, calc) in enumerate(zip(d.itens, t["itens"]), start=1):
            item = conn.execute(
                "INSERT INTO item_pedido (pedido_id, seq, tipo, produto_id, sabor2_id, tamanho, descricao, preco_unit, quantidade, observacoes) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (ped["id"], seq, it.tipo, it.produto_id, it.sabor2_id, calc["tamanho"], calc["descricao"], calc["preco_unit"],
                 it.quantidade, it.observacoes)).fetchone()
            for a in calc["adicionais"]:
                conn.execute("INSERT INTO item_adicional (item_id, adicional_id, nome, valor) VALUES (%s,%s,%s,%s)",
                             (item["id"], a["id"], a["nome"], a["valor"]))
        for l in pagamentos:
            conn.execute("INSERT INTO pagamento (pedido_id, forma, valor, troco, criado_em) VALUES (%s,%s,%s,%s,%s)",
                         (ped["id"], l["forma"], l["valor"], l["troco"], quando))
        if d.ajuste:
            conn.execute("INSERT INTO ajuste_pedido (pedido_id, tipo, valor, motivo, usuario_id, autorizado_por, criado_em) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                         (ped["id"], d.ajuste.tipo, t["desconto"] or t["acrescimo"], d.ajuste.motivo, sessao["usuario_id"],
                          autorizador, quando))
        conn.execute("INSERT INTO evento_pedido (pedido_id, situacao, usuario_id, criado_em) VALUES (%s,'recebido',%s,%s)",
                     (ped["id"], sessao["usuario_id"], quando))
        auditar(conn, sessao, "criar", "pedido", ped["id"],
                depois={"id_dia": id_dia, "total": fmt(t["total"]), "tipo": d.tipo, "autorizado_por": autorizador})
        conn.commit()
    except psycopg.errors.UniqueViolation as e:
        conn.rollback()
        antigo = _por_chave(conn, d.chave) if d.chave else None
        if antigo:  # dois envios simultâneos com a mesma chave: vale o que ganhou a corrida
            response.status_code = 200
            return antigo
        raise traduzir_erro(e) from e
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _out(ped) | {"troco": fmt(sum(l["troco"] for l in pagamentos))}


def _por_chave(conn, chave: str):
    p = conn.execute(f"SELECT {_COLS} FROM pedido WHERE loja_id = %s AND chave = %s", (LOJA_ID, chave)).fetchone()
    if not p:
        return None
    troco = conn.execute("SELECT COALESCE(sum(troco), 0) AS t FROM pagamento WHERE pedido_id = %s", (p["id"],)).fetchone()["t"]
    return _out(p) | {"troco": fmt(troco)}


@router.get("")
def listar(data: Optional[date] = None, situacao: Optional[str] = Query(default=None, max_length=30),
           sessao=Depends(requer("vendas.ver")), conn=Depends(get_db)):
    if situacao is not None and situacao not in SITUACOES + ("cancelado",):
        raise HTTPException(status_code=400, detail="Situação inválida.")
    sql = (f"SELECT p.{_COLS.replace(', ', ', p.')}, c.nome AS cliente_nome FROM pedido p LEFT JOIN cliente c ON c.id = p.cliente_id "
           "WHERE p.loja_id = %s AND p.data = %s")
    params = [LOJA_ID, data or hoje()]
    if situacao:
        sql, params = sql + " AND p.situacao = %s", params + [situacao]
    return [_out(r) for r in conn.execute(sql + " ORDER BY p.id_dia", params).fetchall()]


def _pedido(conn, pid: int, travar=False) -> dict:
    p = conn.execute(f"SELECT {_COLS} FROM pedido WHERE id = %s AND loja_id = %s" + (" FOR UPDATE" if travar else ""),
                     (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return p


@router.get("/{pid}")
def detalhar(pid: int, sessao=Depends(requer("vendas.ver")), conn=Depends(get_db)):
    p = _pedido(conn, pid)
    itens = conn.execute("SELECT id, seq, tipo, descricao, tamanho, preco_unit, quantidade, observacoes FROM item_pedido "
                         "WHERE pedido_id = %s ORDER BY seq", (pid,)).fetchall()
    for i in itens:
        i["preco_unit"] = fmt(i["preco_unit"])
        i["adicionais"] = [{"nome": a["nome"], "valor": fmt(a["valor"])} for a in conn.execute(
            "SELECT nome, valor FROM item_adicional WHERE item_id = %s ORDER BY id", (i["id"],)).fetchall()]
    pags = [{"forma": r["forma"], "valor": fmt(r["valor"]), "troco": fmt(r["troco"])} for r in conn.execute(
        "SELECT forma, valor, troco FROM pagamento WHERE pedido_id = %s ORDER BY id", (pid,)).fetchall()]
    ajustes = [{"tipo": r["tipo"], "valor": fmt(r["valor"]), "motivo": r["motivo"], "autorizado": r["autorizado_por"] is not None}
               for r in conn.execute("SELECT tipo, valor, motivo, autorizado_por FROM ajuste_pedido WHERE pedido_id = %s", (pid,)).fetchall()]
    eventos = conn.execute("SELECT situacao, criado_em FROM evento_pedido WHERE pedido_id = %s ORDER BY id", (pid,)).fetchall()
    return _out(p) | {"itens": itens, "pagamentos": pags, "ajustes": ajustes, "eventos": eventos}


def mudar_situacao(conn, sessao, p: dict, nova: str) -> dict:
    """Avança um passo por vez. Reaproveitada pela Produção (fatia 1D). Quem chama já travou o pedido e comita."""
    atual = p["situacao"]
    if atual not in SITUACOES or nova not in SITUACOES or SITUACOES.index(nova) != SITUACOES.index(atual) + 1:
        raise HTTPException(status_code=409, detail=f"Não é possível ir de '{atual}' para '{nova}'.")
    quando = agora()
    conn.execute("UPDATE pedido SET situacao = %s, entrega_real = CASE WHEN %s = 'despachado ou retirado' THEN %s ELSE entrega_real END "
                 "WHERE id = %s", (nova, nova, quando, p["id"]))
    conn.execute("INSERT INTO evento_pedido (pedido_id, situacao, usuario_id, criado_em) VALUES (%s,%s,%s,%s)",
                 (p["id"], nova, sessao["usuario_id"], quando))
    auditar(conn, sessao, "situacao", "pedido", p["id"], antes={"situacao": atual}, depois={"situacao": nova})
    return _pedido(conn, p["id"])


@router.post("/{pid}/situacao")
def situacao(pid: int, d: PedidoSituacao, sessao=Depends(requer("vendas.criar")), conn=Depends(get_db)):
    # O balcão marca despachado ou retirado; as etapas anteriores são da Produção ou, à mão, da gerência.
    if d.situacao != "despachado ou retirado" and "vendas.gerir" not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=403, detail="Perfil insuficiente para esta operação")
    p = mudar_situacao(conn, sessao, _pedido(conn, pid, travar=True), d.situacao)
    conn.commit()
    return _out(p)


@router.post("/{pid}/urgente")
def urgente(pid: int, d: PedidoUrgente, sessao=Depends(requer("vendas.criar")), conn=Depends(get_db)):
    p = _pedido(conn, pid, travar=True)
    if p["situacao"] != "recebido":
        raise HTTPException(status_code=409, detail="Só pedido que ainda não entrou em produção pode virar urgente.")
    conn.execute("UPDATE pedido SET urgente = %s WHERE id = %s", (d.urgente, pid))
    auditar(conn, sessao, "urgente", "pedido", pid, depois={"urgente": d.urgente})
    conn.commit()
    return _out(_pedido(conn, pid))


@router.post("/{pid}/cancelar")
def cancelar(pid: int, d: PedidoCancelar, request: Request, sessao=Depends(requer("vendas.criar")), conn=Depends(get_db)):
    p = _pedido(conn, pid, travar=True)
    if p["situacao"] in ("cancelado", "despachado ou retirado"):
        raise HTTPException(status_code=409, detail=f"Pedido {p['situacao']} não pode ser cancelado.")
    autorizador = None
    if not _gerencia(sessao):  # atendente: o pedido está pago, então gerente confirma
        if not d.autorizacao:
            raise HTTPException(status_code=403, detail="Cancelar pedido pago exige a autorização de um gerente.")
        autorizador = autorizar(conn, request, d.autorizacao, sessao["usuario_id"])
        p = _pedido(conn, pid, travar=True)
        if p["situacao"] in ("cancelado", "despachado ou retirado"):
            raise HTTPException(status_code=409, detail=f"Pedido {p['situacao']} não pode ser cancelado.")
    quando = agora()
    try:
        conn.execute("INSERT INTO cancelamento (pedido_id, motivo, usuario_id, autorizado_por, situacao_anterior, criado_em) "
                     "VALUES (%s,%s,%s,%s,%s,%s)", (pid, d.motivo, sessao["usuario_id"], autorizador, p["situacao"], quando))
        conn.execute("UPDATE pedido SET situacao = 'cancelado' WHERE id = %s", (pid,))
        conn.execute("INSERT INTO evento_pedido (pedido_id, situacao, usuario_id, criado_em) VALUES (%s,'cancelado',%s,%s)",
                     (pid, sessao["usuario_id"], quando))
        auditar(conn, sessao, "cancelar", "pedido", pid, antes={"situacao": p["situacao"]},
                depois={"motivo": d.motivo, "autorizado_por": autorizador})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _out(_pedido(conn, pid))
