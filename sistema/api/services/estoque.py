"""Estoques: saldo pelos movimentos, PEPS por lote, custo médio móvel e baixa automática pela ficha técnica."""
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

ZERO = Decimal("0")
CASAS = Decimal("0.0001")
SAIDAS = ("saida_venda", "saida_producao", "perda", "consumo_interno", "devolucao_fornecedor", "transferencia_saida")


def q4(v) -> Decimal:
    return Decimal(v).quantize(CASAS)


def txt(v) -> str | None:
    """Quantidade ou custo como texto, sem zeros à direita."""
    return None if v is None else format(Decimal(v).normalize(), "f")


def trava_item(conn, item_id: int) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(11, %s)", (item_id,))


def config_item(conn, loja_id: int, item_id: int) -> dict:
    """Parâmetros do item; sem linha vale o padrão: lote nos insumos e preparos, nada obrigatório nos demais."""
    it = conn.execute("SELECT id, nome, classe, unidade, ativo FROM item WHERE id = %s AND loja_id = %s", (item_id, loja_id)).fetchone()
    if not it:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    c = conn.execute("SELECT * FROM item_estoque WHERE item_id = %s", (item_id,)).fetchone()
    if c:
        return {**it, **{k: c[k] for k in ("unidade_compra", "fator_compra", "local_padrao_id", "estoque_minimo", "ponto_pedido", "estoque_maximo",
                                          "controla_lote", "critico", "fornecedor_habitual_id")}}
    return {**it, "unidade_compra": None, "fator_compra": Decimal(1), "local_padrao_id": None, "estoque_minimo": None, "ponto_pedido": None,
            "estoque_maximo": None, "controla_lote": it["classe"] in ("insumo", "preparo"), "critico": False, "fornecedor_habitual_id": None}


def local_padrao(conn, loja_id: int, item_id: int, cfg: dict | None = None) -> int:
    cfg = cfg or config_item(conn, loja_id, item_id)
    if cfg["local_padrao_id"]:
        ok = conn.execute("SELECT 1 FROM local_estoque WHERE id = %s AND ativo", (cfg["local_padrao_id"],)).fetchone()
        if ok:
            return cfg["local_padrao_id"]
    r = conn.execute("SELECT id FROM local_estoque WHERE loja_id = %s AND ativo ORDER BY id LIMIT 1", (loja_id,)).fetchone()
    if r:
        return r["id"]
    conn.execute("SELECT pg_advisory_xact_lock(12, %s)", (loja_id,))
    r = conn.execute("SELECT id FROM local_estoque WHERE loja_id = %s ORDER BY ativo DESC, id LIMIT 1", (loja_id,)).fetchone()
    if r:
        return r["id"]
    return conn.execute("INSERT INTO local_estoque (loja_id, nome) VALUES (%s, 'Estoque geral') RETURNING id", (loja_id,)).fetchone()["id"]


def saldo_item(conn, item_id: int) -> Decimal:
    return conn.execute("SELECT COALESCE(sum(quantidade), 0) AS s FROM movimento_estoque WHERE item_id = %s", (item_id,)).fetchone()["s"]


def custo_atual(conn, item_id: int):
    r = conn.execute("SELECT custo_medio FROM custo_item WHERE item_id = %s ORDER BY id DESC LIMIT 1", (item_id,)).fetchone()
    return r["custo_medio"] if r else None


def lotes_com_saldo(conn, item_id: int, local_id: int | None = None) -> list[dict]:
    """Lotes com saldo positivo na ordem PEPS: validade mais próxima primeiro (sem validade por último), depois a entrada mais antiga."""
    filtro, args = ("", [item_id]) if local_id is None else (" AND m.local_id = %s", [item_id, local_id])
    return conn.execute(
        "SELECT l.id, l.codigo, l.validade, l.entrada_em, m.local_id, sum(m.quantidade) AS saldo FROM movimento_estoque m "
        "JOIN lote_estoque l ON l.id = m.lote_id WHERE m.item_id = %s" + filtro +
        " GROUP BY l.id, l.codigo, l.validade, l.entrada_em, m.local_id HAVING sum(m.quantidade) > 0 "
        "ORDER BY l.validade NULLS LAST, l.entrada_em, l.id", args).fetchall()


def _mov(conn, loja_id, item_id, local_id, lote_id, tipo, qtd, custo, motivo, origem, usuario_id, quando) -> int:
    return conn.execute(
        "INSERT INTO movimento_estoque (loja_id, data, item_id, local_id, lote_id, tipo, quantidade, custo_unit, motivo, origem_tipo, origem_id, usuario_id, criado_em) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (loja_id, quando.date(), item_id, local_id, lote_id, tipo, qtd, custo, motivo, origem[0] if origem else None, origem[1] if origem else None,
         usuario_id, quando)).fetchone()["id"]


def entrada(conn, loja_id, item_id, qtd: Decimal, custo_unit, tipo, usuario_id, quando, motivo=None, origem=None, local_id=None,
            lote_codigo=None, validade: date | None = None, fornecedor_origem="compra") -> int:
    """Entrada de estoque: cria ou reaproveita o lote (se o item controla lote) e atualiza o custo médio móvel."""
    qtd = q4(qtd)
    if qtd <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
    trava_item(conn, item_id)
    cfg = config_item(conn, loja_id, item_id)
    local = local_id or local_padrao(conn, loja_id, item_id, cfg)
    lote_id = None
    if cfg["controla_lote"]:
        padrao = quando.strftime("L%Y%m%d") + (f"-{origem[0][:3]}{origem[1]}" if origem else "")  # um lote por entrega: validades diferentes não se misturam
        codigo = (lote_codigo or padrao).strip()[:40]
        lote = conn.execute("SELECT id, validade FROM lote_estoque WHERE item_id = %s AND codigo = %s", (item_id, codigo)).fetchone()
        if lote:
            if validade and lote["validade"] != validade:
                raise HTTPException(status_code=409, detail=f"O lote {codigo} já existe com outra validade: use outro código de lote.")
            lote_id = lote["id"]
        else:
            lote_id = conn.execute("INSERT INTO lote_estoque (loja_id, item_id, codigo, validade, entrada_em, custo_unit, origem) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                                   (loja_id, item_id, codigo, validade, quando, custo_unit, fornecedor_origem)).fetchone()["id"]
    saldo_antes = max(saldo_item(conn, item_id), ZERO)
    mov = _mov(conn, loja_id, item_id, local, lote_id, tipo, qtd, custo_unit, motivo, origem, usuario_id, quando)
    if custo_unit is not None:
        medio_antes = custo_atual(conn, item_id) or ZERO
        novo = (saldo_antes * medio_antes + qtd * Decimal(custo_unit)) / (saldo_antes + qtd)
        conn.execute("INSERT INTO custo_item (loja_id, item_id, custo_medio, saldo_apos, movimento_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s)",
                     (loja_id, item_id, novo.quantize(Decimal("0.000001")), saldo_antes + qtd, mov, quando))
    return mov


def saida(conn, loja_id, item_id, qtd: Decimal, tipo, usuario_id, quando, motivo=None, origem=None, permitir_negativo=False,
          local_id=None, lote_id=None) -> list[int]:
    """Saída pelo PEPS (ou do lote escolhido). Sem saldo: recusa, ou, na baixa automática, deixa o saldo negativo para a falta ficar visível."""
    qtd = q4(qtd)
    if qtd <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
    trava_item(conn, item_id)
    cfg = config_item(conn, loja_id, item_id)
    if not permitir_negativo and qtd > saldo_item(conn, item_id):
        raise HTTPException(status_code=400, detail="Saldo insuficiente para esta saída.")
    custo = custo_atual(conn, item_id)
    restante, movs = qtd, []
    if lote_id is not None:
        lote = conn.execute("SELECT m.local_id, sum(m.quantidade) AS saldo FROM movimento_estoque m WHERE m.item_id = %s AND m.lote_id = %s "
                            "GROUP BY m.local_id HAVING sum(m.quantidade) > 0", (item_id, lote_id)).fetchall()
        if local_id is not None:
            lote = [x for x in lote if x["local_id"] == local_id]
        if not lote:
            raise HTTPException(status_code=400, detail="O lote escolhido não tem saldo neste local.")
        lotes = [{"id": lote_id, "local_id": x["local_id"], "saldo": x["saldo"]} for x in lote]
    else:
        lotes = lotes_com_saldo(conn, item_id, local_id)
    for lt in lotes:
        if restante <= 0:
            break
        usa = min(restante, lt["saldo"])
        movs.append(_mov(conn, loja_id, item_id, lt["local_id"], lt["id"], tipo, -usa, custo, motivo, origem, usuario_id, quando))
        restante -= usa
    if restante > 0:
        sem_lote = ZERO
        local = local_id or local_padrao(conn, loja_id, item_id, cfg)
        if lote_id is None:  # parte sem lote (item sem controle de lote, ou saldo antigo sem lote)
            sem_lote = max(conn.execute("SELECT COALESCE(sum(quantidade), 0) AS s FROM movimento_estoque WHERE item_id = %s AND lote_id IS NULL"
                                        + ("" if local_id is None else " AND local_id = %s"), [item_id] + ([] if local_id is None else [local_id])).fetchone()["s"], ZERO)
        usa = min(restante, sem_lote)
        if usa > 0:
            movs.append(_mov(conn, loja_id, item_id, local, None, tipo, -usa, custo, motivo, origem, usuario_id, quando))
            restante -= usa
        if restante > 0:
            if not permitir_negativo:
                raise HTTPException(status_code=400, detail="Saldo insuficiente para esta saída.")
            movs.append(_mov(conn, loja_id, item_id, local, None, tipo, -restante, custo, motivo, origem, usuario_id, quando))
    return movs


# ---------------------------------------------------------------- baixa automática pela ficha técnica
def _ficha(conn, loja_id: int, cond: str, params: list) -> list[dict]:
    v = conn.execute(f"SELECT id FROM ficha_versao WHERE loja_id = %s AND {cond} ORDER BY id DESC LIMIT 1", (loja_id, *params)).fetchone()
    if not v:
        return []
    return conn.execute("SELECT l.item_id, i.classe, l.quantidade, l.perda_pct, l.fase FROM ficha_linha l JOIN item i ON i.id = l.item_id WHERE l.versao_id = %s",
                        (v["id"],)).fetchall()


def _expandir(conn, loja_id: int, linhas: list[dict], mult: Decimal, so_montagem: bool, saida_: dict, nivel=0) -> None:
    """Soma o consumo por item. Preparo com ficha própria vira os insumos dele; sem ficha, consome o próprio preparo."""
    for l in linhas:
        if so_montagem and l["fase"] != "montagem":
            continue
        qtd = Decimal(l["quantidade"]) * mult * (1 + Decimal(l["perda_pct"]) / 100)
        if l["classe"] == "preparo" and nivel < 5:
            sub = _ficha(conn, loja_id, "item_id = %s", [l["item_id"]])
            if sub:
                _expandir(conn, loja_id, [s | {"fase": "montagem"} for s in sub], qtd, False, saida_, nivel + 1)
                continue
        saida_[l["item_id"]] = saida_.get(l["item_id"], ZERO) + qtd


def _pendencia(conn, loja_id, tipo, produto_id, origem, detalhe, quando) -> None:
    conn.execute("INSERT INTO pendencia_estoque (loja_id, tipo, produto_id, origem_tipo, origem_id, detalhe, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (loja_id, tipo, produto_id, origem[0], origem[1], detalhe, quando))


def _ficha_produto(conn, loja_id, produto_id, mult, so_montagem, consumo, falta) -> None:
    f = _ficha(conn, loja_id, "produto_id = %s", [produto_id])
    if not f:
        falta.append(produto_id)
        return
    _expandir(conn, loja_id, f, mult, so_montagem, consumo)


def _gravar_baixa(conn, loja_id, consumo: dict, tipo: str, usuario_id, quando, motivo, origem) -> None:
    for item_id in sorted(consumo):  # ordem fixa evita impasse entre duas baixas ao mesmo tempo
        if consumo[item_id] > 0:
            saida(conn, loja_id, item_id, consumo[item_id], tipo, usuario_id, quando, motivo, origem, permitir_negativo=True)


def consumo_ficha(conn, loja_id: int, tipo: str, tamanho: str, produto_id: int, sabor2_id, adicionais: list, so_montagem: bool = False) -> tuple[dict, list]:
    """Consumo de insumos de uma unidade vendida (pizza, calzone, bebida, acompanhamento) e os produtos sem ficha. Serve à baixa e ao custo."""
    consumo, falta = {}, []
    if tipo == "pizza":
        base = _ficha(conn, loja_id, "tamanho = %s AND produto_id IS NULL AND adicional_id IS NULL AND item_id IS NULL", [tamanho])
        _expandir(conn, loja_id, base, Decimal(1), so_montagem, consumo)
        if tamanho == "grande" and sabor2_id:
            _ficha_produto(conn, loja_id, produto_id, Decimal(1), so_montagem, consumo, falta)
            _ficha_produto(conn, loja_id, sabor2_id, Decimal(1), so_montagem, consumo, falta)
        else:
            _ficha_produto(conn, loja_id, produto_id, Decimal(2 if tamanho == "grande" else 1), so_montagem, consumo, falta)
    else:
        _ficha_produto(conn, loja_id, produto_id, Decimal(1), so_montagem, consumo, falta)
    for a in adicionais:
        _expandir(conn, loja_id, _ficha(conn, loja_id, "adicional_id = %s AND tamanho = %s", [a, tamanho]), Decimal(1), so_montagem, consumo)
    return consumo, falta


def baixar_pizza(conn, loja_id: int, pizza_id: int, fase: str, usuario_id, quando) -> None:
    """fase 'acabada': consome a ficha inteira. 'perdida': consome só o que já tinha entrado (montagem), como perda. Nunca bloqueia a produção."""
    try:
        with conn.transaction():
            p = conn.execute("SELECT p.id, p.tipo, p.tamanho, p.item_id FROM pizza_producao p WHERE p.id = %s", (pizza_id,)).fetchone()
            if not p or not p["item_id"]:
                return
            if fase == "perdida":
                montou = conn.execute("SELECT 1 FROM evento_producao WHERE pizza_id = %s AND situacao = 'em montagem' LIMIT 1", (pizza_id,)).fetchone()
                if not montou or conn.execute("SELECT 1 FROM baixa_origem WHERE origem_tipo = 'pizza' AND origem_id = %s AND fase = 'acabada'", (pizza_id,)).fetchone():
                    return
            if not conn.execute("INSERT INTO baixa_origem (origem_tipo, origem_id, fase, criado_em) VALUES ('pizza', %s, %s, %s) ON CONFLICT DO NOTHING RETURNING 1",
                                (pizza_id, fase, quando)).fetchone():
                return
            it = conn.execute("SELECT produto_id, sabor2_id, tamanho FROM item_pedido WHERE id = %s", (p["item_id"],)).fetchone()
            adicionais = [a["adicional_id"] for a in conn.execute("SELECT adicional_id FROM item_adicional WHERE item_id = %s AND adicional_id IS NOT NULL", (p["item_id"],)).fetchall()]
            consumo, falta = consumo_ficha(conn, loja_id, p["tipo"], it["tamanho"], it["produto_id"], it["sabor2_id"], adicionais, fase == "perdida")
            for pid_ in set(falta):
                _pendencia(conn, loja_id, "sem_ficha", pid_, ("pizza", pizza_id), "Produto sem ficha técnica: a baixa não foi feita.", quando)
            _gravar_baixa(conn, loja_id, consumo, "perda" if fase == "perdida" else "saida_venda", usuario_id, quando,
                          "Pizza perdida" if fase == "perdida" else None, ("pizza", pizza_id))
    except Exception as e:  # a produção segue; o estoque registra o problema
        conn.execute("INSERT INTO pendencia_estoque (loja_id, tipo, origem_tipo, origem_id, detalhe, criado_em) VALUES (%s,'erro_baixa','pizza',%s,%s,%s)",
                     (loja_id, pizza_id, f"{type(e).__name__}: {str(e)[:150]}", quando))


def baixar_itens_do_pedido(conn, loja_id: int, pedido_id: int, usuario_id, quando) -> None:
    """Bebidas e acompanhamentos saem do estoque quando o pedido fica acabado, pela ficha do produto."""
    try:
        with conn.transaction():
            if not conn.execute("INSERT INTO baixa_origem (origem_tipo, origem_id, fase, criado_em) VALUES ('pedido', %s, 'itens', %s) ON CONFLICT DO NOTHING RETURNING 1",
                                (pedido_id, quando)).fetchone():
                return
            consumo, falta = {}, []
            for it in conn.execute("SELECT produto_id, quantidade FROM item_pedido WHERE pedido_id = %s AND tipo IN ('bebida','acompanhamento')", (pedido_id,)).fetchall():
                _ficha_produto(conn, loja_id, it["produto_id"], Decimal(it["quantidade"]), False, consumo, falta)
            for pid_ in set(falta):
                _pendencia(conn, loja_id, "sem_ficha", pid_, ("pedido", pedido_id), "Produto sem ficha técnica: a baixa não foi feita.", quando)
            _gravar_baixa(conn, loja_id, consumo, "saida_venda", usuario_id, quando, None, ("pedido", pedido_id))
    except Exception as e:
        conn.execute("INSERT INTO pendencia_estoque (loja_id, tipo, origem_tipo, origem_id, detalhe, criado_em) VALUES (%s,'erro_baixa','pedido',%s,%s,%s)",
                     (loja_id, pedido_id, f"{type(e).__name__}: {str(e)[:150]}", quando))
