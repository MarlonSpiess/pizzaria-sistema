"""Estoques: locais, itens com parâmetros, saldos, movimentos, alertas e inventário (contagem cega, depois ajuste com motivo)."""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (ContagemInventarioIn, FecharInventarioIn, InventarioIn, ItemEstoqueIn, LocalIn, LocalUpdate, MovimentoEstoqueIn)
from api.security import requer
from api.services import estoque as svc
from api.services.dinheiro import fmt
from api.services.parametros import vigentes

router = APIRouter(prefix="/estoque", tags=["estoque"])
LOCAIS_PADRAO = ("Freezer", "Câmara fria", "Estoque seco")
_CFG = ("unidade_compra", "fator_compra", "local_padrao_id", "estoque_minimo", "ponto_pedido", "estoque_maximo", "controla_lote", "critico", "fornecedor_habitual_id")


def _cfg_out(c: dict) -> dict:
    return {**{k: c[k] for k in ("id", "nome", "classe", "unidade", "ativo")}, **{k: (svc.txt(c[k]) if k in ("fator_compra", "estoque_minimo", "ponto_pedido", "estoque_maximo") else c[k]) for k in _CFG}}


# ---------------------------------------------------------------- locais
def _locais(conn):
    return conn.execute("SELECT id, nome, ativo FROM local_estoque WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall()


@router.get("/locais")
def locais(sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    return _locais(conn)


@router.post("/locais/iniciar-padrao", status_code=201)
def iniciar_locais(sessao=Depends(requer("estoque.gerir")), conn=Depends(get_db)):
    conn.execute("SELECT pg_advisory_xact_lock(12, %s)", (LOJA_ID,))
    if conn.execute("SELECT count(*) AS n FROM local_estoque WHERE loja_id = %s AND nome <> 'Estoque geral'", (LOJA_ID,)).fetchone()["n"]:
        raise HTTPException(status_code=409, detail="Já existem locais cadastrados.")
    for n in LOCAIS_PADRAO:
        conn.execute("INSERT INTO local_estoque (loja_id, nome) VALUES (%s,%s) ON CONFLICT DO NOTHING", (LOJA_ID, n))
    auditar(conn, sessao, "iniciar_padrao", "local_estoque", None)
    conn.commit()
    return _locais(conn)


@router.post("/locais", status_code=201)
def criar_local(d: LocalIn, sessao=Depends(requer("estoque.gerir")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO local_estoque (loja_id, nome) VALUES (%s,%s) RETURNING id, nome, ativo", (LOJA_ID, d.nome)).fetchone()
        auditar(conn, sessao, "criar", "local_estoque", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.patch("/locais/{lid}")
def alterar_local(lid: int, d: LocalUpdate, sessao=Depends(requer("estoque.gerir")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute("SELECT 1 FROM local_estoque WHERE id = %s AND loja_id = %s", (lid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Local não encontrado.")
    if campos.get("ativo") is False:
        saldo = conn.execute("SELECT COALESCE(sum(quantidade) FILTER (WHERE quantidade > 0), 0) AS s FROM (SELECT item_id, lote_id, sum(quantidade) AS quantidade "
                             "FROM movimento_estoque WHERE local_id = %s GROUP BY item_id, lote_id) x WHERE quantidade > 0", (lid,)).fetchone()["s"]
        if saldo > 0:
            raise HTTPException(status_code=409, detail="Este local ainda tem estoque: transfira antes de inativar.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    try:
        r = conn.execute(f"UPDATE local_estoque SET {sets} WHERE id = %s RETURNING id, nome, ativo", (*campos.values(), lid)).fetchone()
        auditar(conn, sessao, "alterar", "local_estoque", lid, depois=campos)
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


# ---------------------------------------------------------------- itens, saldos e parâmetros
def _situacao(saldo: Decimal, c: dict) -> str:
    if saldo <= 0:
        return "sem estoque"
    if c["ponto_pedido"] is not None and saldo <= c["ponto_pedido"]:
        return "repor"
    if c["estoque_minimo"] is not None and saldo <= c["estoque_minimo"]:
        return "abaixo do mínimo"
    return "ok"


@router.get("/itens")
def itens(classe: Optional[str] = None, critico: Optional[bool] = None, atencao: bool = False, q: Optional[str] = Query(None, max_length=60),
          sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    """Itens ativos com saldo, custo médio e situação. atencao=true traz só o que pede ação."""
    sql = ("SELECT i.id, i.nome, i.classe, i.unidade, COALESCE((SELECT sum(quantidade) FROM movimento_estoque m WHERE m.item_id = i.id), 0) AS saldo, "
           "(SELECT custo_medio FROM custo_item c WHERE c.item_id = i.id ORDER BY c.id DESC LIMIT 1) AS custo_medio "
           "FROM item i WHERE i.loja_id = %s AND i.ativo")
    params: list = [LOJA_ID]
    if classe:
        sql, params = sql + " AND i.classe = %s", params + [classe]
    if q:
        sql, params = sql + " AND i.nome ILIKE %s", params + ["%" + q.replace("%", "").replace("_", "") + "%"]
    saida = []
    for r in conn.execute(sql + " ORDER BY i.nome", params).fetchall():
        c = svc.config_item(conn, LOJA_ID, r["id"])
        if critico is not None and c["critico"] != critico:
            continue
        sit = _situacao(r["saldo"], c)
        if atencao and sit == "ok":
            continue
        saida.append({"id": r["id"], "nome": r["nome"], "classe": r["classe"], "unidade": r["unidade"], "saldo": svc.txt(r["saldo"]), "situacao": sit,
                      "custo_medio": svc.txt(r["custo_medio"]), "critico": c["critico"], "estoque_minimo": svc.txt(c["estoque_minimo"]),
                      "ponto_pedido": svc.txt(c["ponto_pedido"]), "controla_lote": c["controla_lote"], "fator_compra": svc.txt(c["fator_compra"])})
    return saida


@router.get("/itens/{iid}")
def item(iid: int, sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    c = svc.config_item(conn, LOJA_ID, iid)
    por_local = conn.execute("SELECT l.id AS local_id, l.nome AS local, sum(m.quantidade) AS saldo FROM movimento_estoque m JOIN local_estoque l ON l.id = m.local_id "
                             "WHERE m.item_id = %s GROUP BY l.id, l.nome HAVING sum(m.quantidade) <> 0 ORDER BY l.nome", (iid,)).fetchall()
    lotes = svc.lotes_com_saldo(conn, iid)
    movs = conn.execute("SELECT m.id, m.criado_em, m.tipo, m.quantidade, m.custo_unit, m.motivo, l.nome AS local, lo.codigo AS lote, u.nome AS usuario "
                        "FROM movimento_estoque m JOIN local_estoque l ON l.id = m.local_id LEFT JOIN lote_estoque lo ON lo.id = m.lote_id "
                        "LEFT JOIN usuario u ON u.id = m.usuario_id WHERE m.item_id = %s ORDER BY m.id DESC LIMIT 30", (iid,)).fetchall()
    custos = conn.execute("SELECT custo_medio, saldo_apos, criado_em FROM custo_item WHERE item_id = %s ORDER BY id DESC LIMIT 3", (iid,)).fetchall()
    precos = conn.execute("SELECT p.preco_unit, p.data, f.nome AS fornecedor FROM preco_compra p LEFT JOIN fornecedor f ON f.id = p.fornecedor_id "
                          "WHERE p.item_id = %s ORDER BY p.id DESC LIMIT 3", (iid,)).fetchall()
    saldo = svc.saldo_item(conn, iid)
    return {**_cfg_out(c), "saldo": svc.txt(saldo), "situacao": _situacao(saldo, c),
            "por_local": [r | {"saldo": svc.txt(r["saldo"])} for r in por_local],
            "lotes": [r | {"saldo": svc.txt(r["saldo"])} for r in lotes],
            "movimentos": [r | {"quantidade": svc.txt(r["quantidade"]), "custo_unit": svc.txt(r["custo_unit"])} for r in movs],
            "ultimos_custos_medios": [{"custo_medio": svc.txt(r["custo_medio"]), "em": r["criado_em"]} for r in custos],
            "ultimos_precos_pagos": [{"preco_unit": svc.txt(r["preco_unit"]), "data": r["data"], "fornecedor": r["fornecedor"]} for r in precos]}


@router.put("/itens/{iid}/config")
def config(iid: int, d: ItemEstoqueIn, sessao=Depends(requer("estoque.gerir")), conn=Depends(get_db)):
    atual = svc.config_item(conn, LOJA_ID, iid)
    novo = {**{k: atual[k] for k in _CFG}}
    for k, v in d.model_dump(exclude_unset=True).items():
        novo[k] = Decimal(v) if k in ("fator_compra", "estoque_minimo", "ponto_pedido", "estoque_maximo") and v is not None else v
    mn, pp, mx = novo["estoque_minimo"], novo["ponto_pedido"], novo["estoque_maximo"]
    if (mn is not None and pp is not None and pp < mn) or (pp is not None and mx is not None and mx < pp) or (mn is not None and mx is not None and mx < mn):
        raise HTTPException(status_code=400, detail="Use mínimo menor ou igual ao ponto de pedido, e este menor ou igual ao máximo.")
    if novo["local_padrao_id"] is not None and not conn.execute("SELECT 1 FROM local_estoque WHERE id = %s AND loja_id = %s AND ativo", (novo["local_padrao_id"], LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Local não encontrado ou inativo.")
    if novo["fornecedor_habitual_id"] is not None and not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s AND ativo", (novo["fornecedor_habitual_id"], LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado ou inativo.")
    try:
        conn.execute(
            "INSERT INTO item_estoque (item_id, loja_id, unidade_compra, fator_compra, local_padrao_id, estoque_minimo, ponto_pedido, estoque_maximo, controla_lote, critico, "
            "fornecedor_habitual_id, atualizado_em, atualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (item_id) DO UPDATE SET unidade_compra = EXCLUDED.unidade_compra, fator_compra = EXCLUDED.fator_compra, local_padrao_id = EXCLUDED.local_padrao_id, "
            "estoque_minimo = EXCLUDED.estoque_minimo, ponto_pedido = EXCLUDED.ponto_pedido, estoque_maximo = EXCLUDED.estoque_maximo, controla_lote = EXCLUDED.controla_lote, "
            "critico = EXCLUDED.critico, fornecedor_habitual_id = EXCLUDED.fornecedor_habitual_id, atualizado_em = EXCLUDED.atualizado_em, atualizado_por = EXCLUDED.atualizado_por",
            (iid, LOJA_ID, novo["unidade_compra"], novo["fator_compra"], novo["local_padrao_id"], mn, pp, mx, novo["controla_lote"], novo["critico"],
             novo["fornecedor_habitual_id"], agora(), sessao["usuario_id"]))
        auditar(conn, sessao, "config", "item_estoque", iid, antes={k: str(atual[k]) for k in _CFG}, depois={k: str(novo[k]) for k in _CFG})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _cfg_out(svc.config_item(conn, LOJA_ID, iid))


# ---------------------------------------------------------------- movimentos manuais
@router.get("/movimentos")
def movimentos(item_id: Optional[int] = None, tipo: Optional[str] = None, limite: int = Query(100, ge=1, le=500),
               sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    sql = ("SELECT m.id, m.criado_em, m.data, i.nome AS item, i.unidade, m.tipo, m.quantidade, m.custo_unit, m.motivo, l.nome AS local, lo.codigo AS lote, u.nome AS usuario "
           "FROM movimento_estoque m JOIN item i ON i.id = m.item_id JOIN local_estoque l ON l.id = m.local_id LEFT JOIN lote_estoque lo ON lo.id = m.lote_id "
           "LEFT JOIN usuario u ON u.id = m.usuario_id WHERE m.loja_id = %s")
    params: list = [LOJA_ID]
    if item_id:
        sql, params = sql + " AND m.item_id = %s", params + [item_id]
    if tipo:
        sql, params = sql + " AND m.tipo = %s", params + [tipo]
    return [r | {"quantidade": svc.txt(r["quantidade"]), "custo_unit": svc.txt(r["custo_unit"])}
            for r in conn.execute(sql + " ORDER BY m.id DESC LIMIT %s", params + [limite]).fetchall()]


@router.post("/movimentos", status_code=201)
def movimentar(d: MovimentoEstoqueIn, sessao=Depends(requer("estoque.mover")), conn=Depends(get_db)):
    """Perda, consumo interno, estoque inicial e transferência entre locais. A entrada de compra vem do recebimento; o ajuste, do inventário."""
    if d.tipo in ("perda", "consumo_interno", "entrada_inicial") and not d.motivo:
        raise HTTPException(status_code=400, detail="Informe o motivo.")
    if d.tipo == "entrada_inicial" and "estoque.gerir" not in _permissoes(sessao):
        raise HTTPException(status_code=403, detail="Perfil insuficiente para esta operação")
    cfg = svc.config_item(conn, LOJA_ID, d.item_id)
    if not cfg["ativo"]:
        raise HTTPException(status_code=400, detail="Este item está inativo.")
    for lid in (d.local_id, d.destino_id):
        if lid is not None and not conn.execute("SELECT 1 FROM local_estoque WHERE id = %s AND loja_id = %s AND ativo", (lid, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Local não encontrado ou inativo.")
    quando, qtd = agora(), Decimal(d.quantidade)
    try:
        if d.tipo == "entrada_inicial":
            if d.custo_unit is None:
                raise HTTPException(status_code=400, detail="Informe o custo unitário do estoque inicial.")
            mov = svc.entrada(conn, LOJA_ID, d.item_id, qtd, Decimal(d.custo_unit), "entrada_inicial", sessao["usuario_id"], quando, d.motivo,
                              local_id=d.local_id, lote_codigo=d.lote_codigo, validade=d.validade, fornecedor_origem="inicial")
            movs = [mov]
        elif d.tipo == "transferencia":
            if d.destino_id is None or d.local_id is None or d.destino_id == d.local_id:
                raise HTTPException(status_code=400, detail="Informe origem e destino diferentes.")
            movs = svc.saida(conn, LOJA_ID, d.item_id, qtd, "transferencia_saida", sessao["usuario_id"], quando, d.motivo, local_id=d.local_id, lote_id=d.lote_id)
            for m in conn.execute("SELECT lote_id, -quantidade AS q FROM movimento_estoque WHERE id = ANY(%s)", (movs,)).fetchall():
                conn.execute("INSERT INTO movimento_estoque (loja_id, data, item_id, local_id, lote_id, tipo, quantidade, custo_unit, motivo, usuario_id, criado_em) "
                             "VALUES (%s,%s,%s,%s,%s,'transferencia_entrada',%s,NULL,%s,%s,%s)",
                             (LOJA_ID, quando.date(), d.item_id, d.destino_id, m["lote_id"], m["q"], d.motivo, sessao["usuario_id"], quando))
        else:
            movs = svc.saida(conn, LOJA_ID, d.item_id, qtd, d.tipo, sessao["usuario_id"], quando, d.motivo, local_id=d.local_id, lote_id=d.lote_id)
        auditar(conn, sessao, d.tipo, "movimento_estoque", movs[0], depois={"item_id": d.item_id, "quantidade": d.quantidade, "motivo": d.motivo})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"movimentos": movs, "saldo": svc.txt(svc.saldo_item(conn, d.item_id))}


def _permissoes(sessao):
    from api.security import PERMISSOES
    return PERMISSOES.get(sessao["perfil"], set())


# ---------------------------------------------------------------- alertas e pendências
@router.get("/alertas")
def alertas(sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    dias = int(vigentes(conn, LOJA_ID)["alerta_validade_dias"]["valor"] or 7)
    limite = (agora() + timedelta(days=dias)).date()
    hoje = agora().date()
    lotes = conn.execute("SELECT i.id AS item_id, i.nome AS item, l.codigo, l.validade, sum(m.quantidade) AS saldo FROM movimento_estoque m JOIN lote_estoque l ON l.id = m.lote_id "
                         "JOIN item i ON i.id = m.item_id WHERE m.loja_id = %s AND l.validade IS NOT NULL AND l.validade <= %s "
                         "GROUP BY i.id, i.nome, l.codigo, l.validade HAVING sum(m.quantidade) > 0 ORDER BY l.validade", (LOJA_ID, limite)).fetchall()
    abaixo = itens(None, None, True, None, sessao, conn)
    faltas = conn.execute("SELECT count(*) AS n FROM retrocesso r JOIN motivo_retrocesso m ON m.id = r.motivo_id WHERE m.avisa_estoque AND r.criado_em > %s",
                          (agora() - timedelta(hours=24),)).fetchone()["n"]
    pend = conn.execute("SELECT e.tipo, e.produto_id, p.nome AS produto, count(*) AS vezes, max(e.criado_em) AS ultima FROM pendencia_estoque e LEFT JOIN produto p ON p.id = e.produto_id "
                        "WHERE e.loja_id = %s GROUP BY e.tipo, e.produto_id, p.nome ORDER BY max(e.criado_em) DESC LIMIT 50", (LOJA_ID,)).fetchall()
    return {"repor": abaixo, "validade": [r | {"saldo": svc.txt(r["saldo"]), "vencido": r["validade"] < hoje} for r in lotes],
            "faltas_producao_24h": faltas, "pendencias": pend, "dias_alerta": dias}


# ---------------------------------------------------------------- inventário
def _inv(conn, iid: int, travar=False) -> dict:
    r = conn.execute("SELECT * FROM inventario WHERE id = %s AND loja_id = %s" + (" FOR UPDATE" if travar else ""), (iid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Inventário não encontrado.")
    return r


def _inv_out(conn, inv: dict) -> dict:
    mostra = inv["situacao"] != "aberto"
    linhas = conn.execute("SELECT l.item_id, i.nome AS item, i.unidade, l.contado, l.esperado, l.diferenca, l.motivo FROM inventario_linha l JOIN item i ON i.id = l.item_id "
                          "WHERE l.inventario_id = %s ORDER BY i.nome", (inv["id"],)).fetchall()
    return {**{k: inv[k] for k in ("id", "tipo", "situacao", "observacao", "aberto_em", "conferido_em", "fechado_em")},
            "linhas": [{"item_id": r["item_id"], "item": r["item"], "unidade": r["unidade"], "contado": svc.txt(r["contado"]),
                        "esperado": svc.txt(r["esperado"]) if mostra else None, "diferenca": svc.txt(r["diferenca"]) if mostra else None, "motivo": r["motivo"]} for r in linhas]}


@router.get("/inventarios")
def inventarios(sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    return conn.execute("SELECT id, tipo, situacao, aberto_em, fechado_em, (SELECT count(*) FROM inventario_linha l WHERE l.inventario_id = i.id) AS itens "
                        "FROM inventario i WHERE loja_id = %s ORDER BY id DESC LIMIT 50", (LOJA_ID,)).fetchall()


@router.post("/inventarios", status_code=201)
def abrir_inventario(d: InventarioIn, sessao=Depends(requer("estoque.mover")), conn=Depends(get_db)):
    """Diário: itens críticos. Mensal: todos (menos preparos, que a Produção conta). Avulso: os itens escolhidos."""
    conn.execute("SELECT pg_advisory_xact_lock(13, %s)", (LOJA_ID,))
    if conn.execute("SELECT 1 FROM inventario WHERE loja_id = %s AND situacao <> 'fechado'", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=409, detail="Já existe um inventário em andamento: feche-o antes de abrir outro.")
    if d.tipo == "avulso":
        if not d.item_ids:
            raise HTTPException(status_code=400, detail="Escolha os itens do inventário avulso.")
        ids = [r["id"] for r in conn.execute("SELECT id FROM item WHERE loja_id = %s AND ativo AND id = ANY(%s)", (LOJA_ID, d.item_ids)).fetchall()]
        if len(ids) != len(set(d.item_ids)):
            raise HTTPException(status_code=400, detail="Há item inexistente ou inativo na lista.")
    elif d.tipo == "diario":
        ids = [r["id"] for r in conn.execute("SELECT i.id FROM item i JOIN item_estoque e ON e.item_id = i.id WHERE i.loja_id = %s AND i.ativo AND e.critico", (LOJA_ID,)).fetchall()]
    else:
        ids = [r["id"] for r in conn.execute("SELECT id FROM item WHERE loja_id = %s AND ativo AND classe <> 'preparo'", (LOJA_ID,)).fetchall()]
    if not ids:
        raise HTTPException(status_code=400, detail="Nenhum item para contar: marque os itens críticos ou cadastre itens.")
    try:
        inv = conn.execute("INSERT INTO inventario (loja_id, tipo, observacao, aberto_por, aberto_em) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                           (LOJA_ID, d.tipo, d.observacao, sessao["usuario_id"], agora())).fetchone()
        for i in ids:
            conn.execute("INSERT INTO inventario_linha (inventario_id, item_id) VALUES (%s,%s)", (inv["id"], i))
        auditar(conn, sessao, "abrir", "inventario", inv["id"], depois={"tipo": d.tipo, "itens": len(ids)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _inv_out(conn, inv)


@router.get("/inventarios/{iid}")
def ver_inventario(iid: int, sessao=Depends(requer("estoque.ver")), conn=Depends(get_db)):
    return _inv_out(conn, _inv(conn, iid))


@router.put("/inventarios/{iid}/contagem")
def contar(iid: int, d: ContagemInventarioIn, sessao=Depends(requer("estoque.mover")), conn=Depends(get_db)):
    inv = _inv(conn, iid, travar=True)
    if inv["situacao"] != "aberto":
        raise HTTPException(status_code=409, detail="A contagem deste inventário já foi encerrada.")
    for x in d.linhas:  # o esperado fica gravado no instante da contagem: movimento posterior (perda, compra) não vira diferença
        esperado = svc.saldo_item(conn, x.item_id)
        n = conn.execute("UPDATE inventario_linha SET contado = %s, esperado = %s, diferenca = %s WHERE inventario_id = %s AND item_id = %s",
                         (Decimal(x.contado), esperado, Decimal(x.contado) - esperado, iid, x.item_id)).rowcount
        if not n:
            raise HTTPException(status_code=400, detail="Há item fora deste inventário.")
    auditar(conn, sessao, "contar", "inventario", iid, depois={"itens": len(d.linhas)})
    conn.commit()
    return _inv_out(conn, _inv(conn, iid))


@router.post("/inventarios/{iid}/conferir")
def conferir(iid: int, sessao=Depends(requer("estoque.mover")), conn=Depends(get_db)):
    """Revela o esperado e a diferença de cada item contado. Depois disso a contagem não muda."""
    inv = _inv(conn, iid, travar=True)
    if inv["situacao"] != "aberto":
        raise HTTPException(status_code=409, detail="Este inventário já foi conferido.")
    if not conn.execute("SELECT 1 FROM inventario_linha WHERE inventario_id = %s AND contado IS NOT NULL", (iid,)).fetchone():
        raise HTTPException(status_code=400, detail="Conte pelo menos um item antes de conferir.")
    conn.execute("UPDATE inventario SET situacao = 'conferido', conferido_em = %s WHERE id = %s", (agora(), iid))
    auditar(conn, sessao, "conferir", "inventario", iid)
    conn.commit()
    return _inv_out(conn, _inv(conn, iid))


@router.post("/inventarios/{iid}/fechar")
def fechar(iid: int, d: FecharInventarioIn, sessao=Depends(requer("estoque.gerir")), conn=Depends(get_db)):
    """Cada diferença vira um movimento de ajuste, com o motivo informado. Itens não contados ficam como estão."""
    inv = _inv(conn, iid, travar=True)
    if inv["situacao"] != "conferido":
        raise HTTPException(status_code=409, detail="Confira o inventário antes de fechar.")
    linhas = conn.execute("SELECT item_id, contado, diferenca FROM inventario_linha WHERE inventario_id = %s ORDER BY item_id", (iid,)).fetchall()
    nao_contados = [l for l in linhas if l["contado"] is None]
    if nao_contados and inv["tipo"] == "mensal" and not d.confirmar_nao_contados:
        raise HTTPException(status_code=409, detail=f"Há {len(nao_contados)} item(ns) sem contagem no inventário mensal: confirme para fechar assim mesmo.")
    motivos = {m.item_id: m.motivo for m in d.motivos}
    com_dif = [l for l in linhas if l["contado"] is not None and l["diferenca"] != 0]
    faltam = [l["item_id"] for l in com_dif if l["item_id"] not in motivos]
    if faltam or set(motivos) - {l["item_id"] for l in com_dif}:
        raise HTTPException(status_code=400, detail="Informe o motivo de cada diferença, e só das diferenças.")
    quando = agora()
    try:
        for l in com_dif:
            mot = motivos[l["item_id"]]
            conn.execute("UPDATE inventario_linha SET motivo = %s WHERE inventario_id = %s AND item_id = %s", (mot, iid, l["item_id"]))
            if l["diferenca"] > 0:
                svc.entrada(conn, LOJA_ID, l["item_id"], l["diferenca"], svc.custo_atual(conn, l["item_id"]), "ajuste_inventario", sessao["usuario_id"], quando, mot,
                            origem=("inventario", iid), lote_codigo=f"AJ{iid}", fornecedor_origem="inventario")
            else:
                svc.saida(conn, LOJA_ID, l["item_id"], -l["diferenca"], "ajuste_inventario", sessao["usuario_id"], quando, mot, origem=("inventario", iid), permitir_negativo=True)
        conn.execute("UPDATE inventario SET situacao = 'fechado', fechado_por = %s, fechado_em = %s WHERE id = %s", (sessao["usuario_id"], quando, iid))
        auditar(conn, sessao, "fechar", "inventario", iid, depois={"ajustes": len(com_dif), "nao_contados": len(nao_contados)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _inv_out(conn, _inv(conn, iid))
