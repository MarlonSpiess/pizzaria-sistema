"""Fechamento de caixa: abertura, sangria e suprimento, contagem cega, fechamento com aprovação, entregas e acerto dos entregadores."""
from datetime import date
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, hoje, traduzir_erro
from api.schemas import (AcertoIn, CaixaAbrir, ContagemIn, EntregaIn, FecharIn, MaquininhaIn, MaquininhaUpdate, MotivoMovimentoIn,
                         MotivoMovimentoUpdate, MovimentoIn, RegraRecebimentoIn)
from api.security import PERMISSOES, requer
from api.services import caixa as svc
from api.services.dinheiro import fmt, parse_reais
from api.services.parametros import vigentes
from api.services.vendas import autorizar

router = APIRouter(prefix="/caixa", tags=["caixa"])
APROVADORES = ("gerente", "proprietario", "administrador")  # subgerente não aprova diferença de caixa
MOTIVOS_PADRAO = (("Despesa pequena", "sangria", True), ("Depósito", "sangria", False), ("Reforço de troco", "suprimento", False))


def _aprova(sessao) -> bool:
    return "caixa.aprovar" in PERMISSOES.get(sessao["perfil"], set())


def _dinheiro_param(par: dict, chave: str) -> Decimal:
    v = par[chave]["valor"]
    return Decimal(v) if v is not None else svc.ZERO


def _linha_caixa(c: dict | None) -> dict | None:
    if not c:
        return None
    c = dict(c)
    c["fundo_troco"] = fmt(c["fundo_troco"])
    return c


def _dinheiros(linhas, *campos):
    saida = []
    for r in linhas:
        r = dict(r)
        for c in campos:
            if r.get(c) is not None:
                r[c] = fmt(r[c])
        saida.append(r)
    return saida


def _pendentes_acerto(conn, fx) -> list[dict]:
    """Entregas do caixa ainda sem acerto (pedidos cancelados não contam)."""
    return conn.execute(
        "SELECT e.pedido_id, ped.id_dia, ped.situacao, e.entregador_id, ent.nome AS entregador, e.valor_entrega "
        "FROM entrega e JOIN pedido ped ON ped.id = e.pedido_id JOIN entregador ent ON ent.id = e.entregador_id "
        "WHERE e.loja_id = %s AND e.data >= %s AND e.data < %s AND e.acerto_id IS NULL AND ped.situacao <> 'cancelado' ORDER BY e.data, ped.id_dia",
        (LOJA_ID, fx[0], fx[1])).fetchall()


def _status(conn, c: dict | None, sessao) -> dict:
    par = vigentes(conn, LOJA_ID)
    fx = svc.faixa(conn, LOJA_ID, c) if c else (hoje(), svc.FIM)
    contado = bool(c and c["situacao"] != "aberto")
    r = svc.relatorio(conn, LOJA_ID, fx, _linha_caixa(c), contado)
    # contagem cega: antes de contar, nada que permita somar o esperado
    r["recebido_por_forma"] = {f: fmt(v) for f, v in r["recebido_por_forma"].items()} if contado else None
    r["acertos"] = _dinheiros(r["acertos"], "dinheiro_recebido", "valor_entregas", "diaria", "total_devido", "saldo_gaveta") if contado else None
    for k in ("vendas", "descontos", "acrescimos"):
        r[k] = fmt(r[k]) if contado else None
    r["pedidos"] = r["pedidos"] if contado else None
    r["movimentos"] = _dinheiros(r["movimentos"], "valor")
    r["estornos"] = _dinheiros(r["estornos"], "valor") if contado else [e | {"valor": None} for e in r["estornos"]]
    r["pedidos_sem_cf"] = _dinheiros(r["pedidos_sem_cf"], "total") if contado else [{"id": x["id"], "id_dia": x["id_dia"]} for x in r["pedidos_sem_cf"]]
    r["cancelamentos"] = {"n": r["cancelamentos"]["n"], "valor": fmt(r["cancelamentos"]["valor"])} if contado else {"n": r["cancelamentos"]["n"], "valor": None}
    if "contagens" in r:
        r["contagens"] = _dinheiros(r["contagens"], "contado", "esperado", "diferenca")
    r["formas"] = sorted(set(par["formas_pagamento_aceitas"]["valor"]) | (svc.formas_com_movimento(conn, LOJA_ID, fx) if c else {"dinheiro"}), key=svc.FORMAS.index)
    r["tolerancia"] = fmt(svc.tolerancia(par))
    r["entregas_pendentes"] = _dinheiros(_pendentes_acerto(conn, fx), "valor_entrega") if c else []
    r["pode_aprovar"] = _aprova(sessao)
    r["fundo_padrao"] = par["fundo_troco_padrao"]["valor"]
    return r


def _em_uso(conn):
    """Caixa a mostrar agora: o último, exceto se fechou em dia anterior (então a loja ainda não abriu o de hoje)."""
    c = svc.ultimo_caixa(conn, LOJA_ID)
    return None if (c and c["situacao"] == "fechado" and c["data"] < hoje()) else c


# ---------------------------------------------------------------- consulta
@router.get("/hoje")
def hoje_status(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    return _status(conn, _em_uso(conn), sessao)


@router.get("/pendentes")
def anteriores_abertos(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    """Caixas de dias anteriores que ficaram sem fechar."""
    return _dinheiros(conn.execute("SELECT id, data, situacao, fundo_troco FROM caixa_dia WHERE loja_id = %s AND data < %s AND situacao <> 'fechado' "
                                   "ORDER BY data", (LOJA_ID, hoje())).fetchall(), "fundo_troco")


# ---------------------------------------------------------------- motivos, maquininhas e regras (cadastros)
def _motivos(conn):
    return conn.execute("SELECT id, nome, tipo, vira_despesa, ativo FROM motivo_movimento WHERE loja_id = %s ORDER BY tipo, id", (LOJA_ID,)).fetchall()


@router.get("/motivos")
def motivos(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    return _motivos(conn)


@router.post("/motivos/iniciar-padrao", status_code=201)
def iniciar_motivos(sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    conn.execute("SELECT pg_advisory_xact_lock(9, %s)", (LOJA_ID,))
    if conn.execute("SELECT count(*) AS n FROM motivo_movimento WHERE loja_id = %s", (LOJA_ID,)).fetchone()["n"]:
        raise HTTPException(status_code=409, detail="Já existem motivos cadastrados.")
    for nome, tipo, despesa in MOTIVOS_PADRAO:
        conn.execute("INSERT INTO motivo_movimento (loja_id, nome, tipo, vira_despesa) VALUES (%s,%s,%s,%s)", (LOJA_ID, nome, tipo, despesa))
    auditar(conn, sessao, "iniciar_padrao", "motivo_movimento", None)
    conn.commit()
    return _motivos(conn)


@router.post("/motivos", status_code=201)
def criar_motivo(d: MotivoMovimentoIn, sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    if d.tipo == "suprimento" and d.vira_despesa:
        raise HTTPException(status_code=400, detail="Só a sangria pode virar despesa.")
    try:
        r = conn.execute("INSERT INTO motivo_movimento (loja_id, nome, tipo, vira_despesa) VALUES (%s,%s,%s,%s) RETURNING id, nome, tipo, vira_despesa, ativo",
                         (LOJA_ID, d.nome, d.tipo, d.vira_despesa)).fetchone()
        auditar(conn, sessao, "criar", "motivo_movimento", r["id"], depois={"nome": d.nome, "tipo": d.tipo})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.patch("/motivos/{mid}")
def alterar_motivo(mid: int, d: MotivoMovimentoUpdate, sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    m = conn.execute("SELECT tipo FROM motivo_movimento WHERE id = %s AND loja_id = %s", (mid, LOJA_ID)).fetchone()
    if not m:
        raise HTTPException(status_code=404, detail="Motivo não encontrado.")
    if campos.get("vira_despesa") and m["tipo"] == "suprimento":
        raise HTTPException(status_code=400, detail="Só a sangria pode virar despesa.")
    sets = ", ".join(f"{c} = %s" for c in campos)  # nomes de coluna vêm só do schema
    try:
        r = conn.execute(f"UPDATE motivo_movimento SET {sets} WHERE id = %s RETURNING id, nome, tipo, vira_despesa, ativo", (*campos.values(), mid)).fetchone()
        auditar(conn, sessao, "alterar", "motivo_movimento", mid, depois=campos)
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.get("/maquininhas")
def maquininhas(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    return conn.execute("SELECT id, nome, ativo FROM maquininha WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall()


@router.post("/maquininhas", status_code=201)
def criar_maquininha(d: MaquininhaIn, sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO maquininha (loja_id, nome) VALUES (%s,%s) RETURNING id, nome, ativo", (LOJA_ID, d.nome)).fetchone()
        auditar(conn, sessao, "criar", "maquininha", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.patch("/maquininhas/{mid}")
def alterar_maquininha(mid: int, d: MaquininhaUpdate, sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute("SELECT 1 FROM maquininha WHERE id = %s AND loja_id = %s", (mid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Maquininha não encontrada.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    try:
        r = conn.execute(f"UPDATE maquininha SET {sets} WHERE id = %s RETURNING id, nome, ativo", (*campos.values(), mid)).fetchone()
        auditar(conn, sessao, "alterar", "maquininha", mid, depois=campos)
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.get("/regras-recebimento")
def regras(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    """Regra vigente (a mais recente) de cada forma e maquininha, e o histórico completo."""
    todas = conn.execute("SELECT id, forma, maquininha_id, taxa_pct, prazo_dias, vigente_desde FROM regra_recebimento WHERE loja_id = %s ORDER BY id DESC",
                         (LOJA_ID,)).fetchall()
    vistas, vigentes_ = set(), []
    for r in todas:
        k = (r["forma"], r["maquininha_id"])
        if k not in vistas:
            vistas.add(k)
            vigentes_.append(r)
    return {"vigentes": [r | {"taxa_pct": str(r["taxa_pct"])} for r in vigentes_], "historico": [r | {"taxa_pct": str(r["taxa_pct"])} for r in todas]}


@router.post("/regras-recebimento", status_code=201)
def criar_regra(d: RegraRecebimentoIn, sessao=Depends(requer("caixa.gerir")), conn=Depends(get_db)):
    if d.maquininha_id is not None:
        if d.forma not in ("credito", "debito"):
            raise HTTPException(status_code=400, detail="Maquininha só vale para crédito e débito.")
        if not conn.execute("SELECT 1 FROM maquininha WHERE id = %s AND loja_id = %s", (d.maquininha_id, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Maquininha não encontrada.")
    quando = agora()
    r = conn.execute("INSERT INTO regra_recebimento (loja_id, forma, maquininha_id, taxa_pct, prazo_dias, vigente_desde, criado_por) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, forma, maquininha_id, taxa_pct, prazo_dias, vigente_desde",
                     (LOJA_ID, d.forma, d.maquininha_id, d.taxa_pct, d.prazo_dias, quando, sessao["usuario_id"])).fetchone()
    auditar(conn, sessao, "criar", "regra_recebimento", r["id"], depois={"forma": d.forma, "taxa_pct": str(d.taxa_pct), "prazo_dias": d.prazo_dias})
    conn.commit()
    return r | {"taxa_pct": str(r["taxa_pct"])}


# ---------------------------------------------------------------- abertura, movimentos, contagem, fechamento
@router.post("/abrir", status_code=201)
def abrir(d: CaixaAbrir, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    par = vigentes(conn, LOJA_ID)
    padrao = par["fundo_troco_padrao"]["valor"]
    if d.fundo_troco is not None:
        fundo = parse_reais(d.fundo_troco)
        if (padrao is None or fundo != Decimal(padrao)) and "caixa.gerir" not in PERMISSOES.get(sessao["perfil"], set()):
            raise HTTPException(status_code=403, detail="Fundo de troco diferente do padrão: só a gerência define.")
    else:
        fundo = Decimal(padrao) if padrao is not None else svc.ZERO
    quando = agora()
    conn.execute("SELECT pg_advisory_xact_lock(14, %s)", (LOJA_ID,))
    ult = svc.ultimo_caixa(conn, LOJA_ID)
    if ult and ult["situacao"] != "fechado":
        raise HTTPException(status_code=409, detail=f"O caixa de {ult['data'].strftime('%d/%m')} ainda não foi fechado: conte e feche antes de abrir outro.")
    try:
        r = conn.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (%s,%s,%s,%s,%s) "
                         "ON CONFLICT (loja_id, data) DO NOTHING RETURNING id", (LOJA_ID, quando.date(), fundo, sessao["usuario_id"], quando)).fetchone()
        if not r:
            raise HTTPException(status_code=409, detail="O caixa de hoje já foi aberto e fechado.")
        auditar(conn, sessao, "abrir", "caixa_dia", r["id"], depois={"fundo_troco": fmt(fundo)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _status(conn, svc.ultimo_caixa(conn, LOJA_ID), sessao)


def _sangria_sem_autorizacao(conn, fx) -> Decimal:
    return conn.execute("SELECT COALESCE(sum(valor), 0) AS s FROM movimento_caixa WHERE loja_id = %s AND data >= %s AND data < %s AND tipo = 'sangria' AND autorizado_por IS NULL",
                        (LOJA_ID, fx[0], fx[1])).fetchone()["s"]


@router.post("/movimentos", status_code=201)
def movimentar(d: MovimentoIn, request: Request, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    valor = parse_reais(d.valor)
    quando = agora()
    c = svc.exigir_aberto(conn, LOJA_ID)
    m = conn.execute("SELECT id, nome, tipo, vira_despesa, ativo FROM motivo_movimento WHERE id = %s AND loja_id = %s", (d.motivo_id, LOJA_ID)).fetchone()
    if not m or m["tipo"] != d.tipo:
        raise HTTPException(status_code=404, detail="Motivo não encontrado para este tipo de lançamento.")
    if not m["ativo"]:
        raise HTTPException(status_code=400, detail="Este motivo está inativo.")
    if m["vira_despesa"] and not d.comprovante:
        raise HTTPException(status_code=400, detail="Despesa paga do caixa exige o comprovante (número ou descrição).")
    autorizador = None
    if d.tipo == "sangria" and not _aprova(sessao):
        # Limite não definido vale 0 (como nos descontos) e conta o acumulado do dia, para não fatiar a retirada.
        lim = vigentes(conn, LOJA_ID)["sangria_limite_gerente"]["valor"]
        lim = Decimal(lim) if lim is not None else svc.ZERO
        if _sangria_sem_autorizacao(conn, svc.faixa(conn, LOJA_ID, c)) + valor > lim:
            if not d.autorizacao:
                raise HTTPException(status_code=403, detail=f"A soma das sangrias passa de R$ {fmt(lim)}: peça a autorização de um gerente.")
            autorizador = autorizar(conn, request, d.autorizacao, sessao["usuario_id"], perfis=APROVADORES)
            svc.exigir_aberto(conn, LOJA_ID)
    try:
        r = conn.execute("INSERT INTO movimento_caixa (loja_id, data, tipo, valor, motivo_id, motivo_nome, vira_despesa, observacao, comprovante, usuario_id, autorizado_por, criado_em) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (LOJA_ID, quando.date(), d.tipo, valor, d.motivo_id, m["nome"], m["vira_despesa"],
                                                                                      d.observacao, d.comprovante, sessao["usuario_id"], autorizador, quando)).fetchone()
        auditar(conn, sessao, d.tipo, "movimento_caixa", r["id"], depois={"valor": fmt(valor), "motivo_id": d.motivo_id, "autorizado_por": autorizador})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"id": r["id"], "tipo": d.tipo, "valor": fmt(valor)}


@router.post("/contagem")
def contar(d: ContagemIn, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    """Contagem cega: só depois de informada a contagem completa o sistema revela o esperado e as diferenças."""
    quando = agora()
    c = svc.exigir_aberto(conn, LOJA_ID, "update")
    fx = svc.faixa(conn, LOJA_ID, c)
    formas = set(vigentes(conn, LOJA_ID)["formas_pagamento_aceitas"]["valor"]) | svc.formas_com_movimento(conn, LOJA_ID, fx)
    enviadas = [x.forma for x in d.contagens]
    if len(set(enviadas)) != len(enviadas) or set(enviadas) != formas:
        raise HTTPException(status_code=400, detail="Informe o valor contado de cada forma de pagamento, uma vez só: " + ", ".join(sorted(formas, key=svc.FORMAS.index)) + ".")
    pend = _pendentes_acerto(conn, fx)
    if pend:
        raise HTTPException(status_code=409, detail=f"Acerte antes os entregadores: há {len(pend)} entrega(s) sem acerto.")
    esperado = svc.esperado(conn, LOJA_ID, fx, c["fundo_troco"])
    try:
        for x in d.contagens:
            contado = parse_reais(x.valor)
            conn.execute("INSERT INTO contagem_caixa (caixa_id, forma, contado, esperado, diferenca, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                         (c["id"], x.forma, contado, esperado[x.forma], contado - esperado[x.forma], sessao["usuario_id"], quando))
        conn.execute("UPDATE caixa_dia SET situacao = 'contado', contado_por = %s, contado_em = %s WHERE id = %s", (sessao["usuario_id"], quando, c["id"]))
        auditar(conn, sessao, "contar", "caixa_dia", c["id"])
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _status(conn, svc.ultimo_caixa(conn, LOJA_ID), sessao)


@router.post("/fechar")
def fechar(d: FecharIn, request: Request, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    quando = agora()
    c = svc.ultimo_caixa(conn, LOJA_ID, "update")
    if not c or c["situacao"] != "contado":
        raise HTTPException(status_code=409, detail="Conte o caixa antes de fechar." if c and c["situacao"] == "aberto" else "O caixa não está pronto para fechar.")
    tol = svc.tolerancia(vigentes(conn, LOJA_ID))
    difs = conn.execute("SELECT diferenca FROM contagem_caixa WHERE caixa_id = %s", (c["id"],)).fetchall()
    acima = any(abs(x["diferenca"]) > tol for x in difs)
    aprovador = None
    if acima:
        if not d.justificativa:
            raise HTTPException(status_code=400, detail="Há diferença acima da tolerância: escreva a justificativa.")
        if _aprova(sessao) and sessao["usuario_id"] != c["contado_por"]:
            aprovador = sessao["usuario_id"]  # quem contou não aprova a própria contagem
        elif d.autorizacao:
            aprovador = autorizar(conn, request, d.autorizacao, sessao["usuario_id"], perfis=APROVADORES)
            if aprovador == c["contado_por"]:
                raise HTTPException(status_code=403, detail="Quem fez a contagem não pode aprovar a diferença: use outro gerente.")
            c = svc.ultimo_caixa(conn, LOJA_ID, "update")
            if c["situacao"] != "contado":
                raise HTTPException(status_code=409, detail="O caixa já foi fechado.")
        else:
            raise HTTPException(status_code=403, detail="Diferença acima da tolerância: um gerente que não fez a contagem precisa aprovar o fechamento.")
    try:
        conn.execute("UPDATE caixa_dia SET situacao = 'fechado', fechado_por = %s, fechado_em = %s, aprovado_por = %s, justificativa = %s WHERE id = %s",
                     (sessao["usuario_id"], quando, aprovador, d.justificativa, c["id"]))
        auditar(conn, sessao, "fechar", "caixa_dia", c["id"], depois={"aprovado_por": aprovador, "justificativa": d.justificativa})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _status(conn, svc.ultimo_caixa(conn, LOJA_ID), sessao)


# ---------------------------------------------------------------- entregas e acerto dos entregadores
@router.get("/entregas")
def entregas(sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    """Pedidos de entrega do caixa em uso, com o entregador atribuído (se houver) e se já foram acertados."""
    c = _em_uso(conn)
    fx = svc.faixa(conn, LOJA_ID, c) if c else (hoje(), svc.FIM)
    return _dinheiros(conn.execute(
        "SELECT ped.id AS pedido_id, ped.id_dia, ped.situacao, ped.total, e.entregador_id, ent.nome AS entregador, e.valor_entrega, e.acerto_id "
        "FROM pedido ped LEFT JOIN entrega e ON e.pedido_id = ped.id LEFT JOIN entregador ent ON ent.id = e.entregador_id "
        "WHERE ped.loja_id = %s AND ped.data >= %s AND ped.data < %s AND ped.tipo = 'entrega' AND ped.situacao <> 'cancelado' ORDER BY ped.data, ped.id_dia", (LOJA_ID, fx[0], fx[1])).fetchall(),
        "total", "valor_entrega")


@router.post("/entregas/{pedido_id}", status_code=201)
def atribuir_entrega(pedido_id: int, d: EntregaIn, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    quando = agora()
    c = svc.exigir_aberto(conn, LOJA_ID)
    p = conn.execute("SELECT id, data, tipo, situacao FROM pedido WHERE id = %s AND loja_id = %s FOR SHARE", (pedido_id, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if p["tipo"] != "entrega" or p["situacao"] == "cancelado":
        raise HTTPException(status_code=409, detail="Só pedido de entrega ativo recebe entregador.")
    if p["data"] < c["data"]:
        raise HTTPException(status_code=409, detail="Este pedido é de um caixa anterior, já encerrado.")
    ent = conn.execute("SELECT ativo FROM entregador WHERE id = %s AND loja_id = %s", (d.entregador_id, LOJA_ID)).fetchone()
    if not ent or not ent["ativo"]:
        raise HTTPException(status_code=404, detail="Entregador não encontrado ou inativo.")
    padrao = _dinheiro_param(vigentes(conn, LOJA_ID), "valor_entrega_padrao")
    valor = parse_reais(d.valor_entrega) if d.valor_entrega is not None else padrao
    if valor != padrao and "caixa.gerir" not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=403, detail="Valor de entrega diferente do padrão: só a gerência define.")
    try:
        conn.execute("INSERT INTO entrega (pedido_id, loja_id, data, entregador_id, valor_entrega, atribuido_por, atribuido_em) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                     (pedido_id, LOJA_ID, p["data"], d.entregador_id, valor, sessao["usuario_id"], quando))
        auditar(conn, sessao, "atribuir", "entrega", pedido_id, depois={"entregador_id": d.entregador_id, "valor": fmt(valor)})
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Este pedido já tem entregador.")
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"pedido_id": pedido_id, "entregador_id": d.entregador_id, "valor_entrega": fmt(valor)}


@router.post("/acertos", status_code=201)
def acertar(d: AcertoIn, sessao=Depends(requer("caixa.operar")), conn=Depends(get_db)):
    """Acerto do fim do turno: o entregador devolve o dinheiro que recebeu e recebe o valor das entregas mais a diária (uma vez por dia)."""
    quando = agora()
    c = svc.exigir_aberto(conn, LOJA_ID)
    fx = svc.faixa(conn, LOJA_ID, c)
    if not conn.execute("SELECT 1 FROM entregador WHERE id = %s AND loja_id = %s", (d.entregador_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Entregador não encontrado.")
    conn.execute("SELECT pg_advisory_xact_lock(10, %s)", (d.entregador_id,))
    ents = conn.execute("SELECT e.pedido_id, e.valor_entrega FROM entrega e JOIN pedido ped ON ped.id = e.pedido_id "
                        "WHERE e.loja_id = %s AND e.data >= %s AND e.data < %s AND e.entregador_id = %s AND e.acerto_id IS NULL AND ped.situacao = 'despachado ou retirado' "
                        "FOR UPDATE OF e", (LOJA_ID, fx[0], fx[1], d.entregador_id)).fetchall()
    if not ents:
        raise HTTPException(status_code=409, detail="Este entregador não tem entregas concluídas para acertar (marque os pedidos como entregues no balcão).")
    ids = [e["pedido_id"] for e in ents]
    recebido = conn.execute("SELECT COALESCE(sum(valor - troco), 0) AS s FROM pagamento WHERE forma = 'dinheiro' AND pedido_id = ANY(%s)", (ids,)).fetchone()["s"]
    valor_entregas = sum((e["valor_entrega"] for e in ents), svc.ZERO)
    ja = conn.execute("SELECT 1 FROM acerto_entregador WHERE loja_id = %s AND data = %s AND entregador_id = %s", (LOJA_ID, quando.date(), d.entregador_id)).fetchone()
    if ja:
        diaria = svc.ZERO  # a diária vale uma vez por entregador por dia
    else:
        padrao = _dinheiro_param(vigentes(conn, LOJA_ID), "diaria_entregador_padrao")
        diaria = parse_reais(d.diaria) if d.diaria is not None else padrao
        if diaria != padrao and "caixa.gerir" not in PERMISSOES.get(sessao["perfil"], set()):
            raise HTTPException(status_code=403, detail="Diária diferente do padrão: só a gerência define.")
    devido = valor_entregas + diaria
    try:
        a = conn.execute("INSERT INTO acerto_entregador (loja_id, data, entregador_id, pedidos, dinheiro_recebido, valor_entregas, diaria, total_devido, saldo_gaveta, "
                         "usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, quando.date(), d.entregador_id, len(ids), recebido, valor_entregas, diaria, devido, recebido - devido,
                          sessao["usuario_id"], quando)).fetchone()
        conn.execute("UPDATE entrega SET acerto_id = %s WHERE pedido_id = ANY(%s)", (a["id"], ids))
        auditar(conn, sessao, "acertar", "acerto_entregador", a["id"], depois={"pedidos": len(ids), "total_devido": fmt(devido), "saldo_gaveta": fmt(recebido - devido)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"id": a["id"], "pedidos": len(ids), "dinheiro_recebido": fmt(recebido), "valor_entregas": fmt(valor_entregas), "diaria": fmt(diaria),
            "total_devido": fmt(devido), "saldo_gaveta": fmt(recebido - devido), "diaria_ja_paga_hoje": bool(ja)}


# ---------------------------------------------------------------- relatório de uma data (por último: o caminho aceita qualquer data)
@router.get("/{data}/relatorio")
def relatorio(data: date, sessao=Depends(requer("caixa.ver")), conn=Depends(get_db)):
    return _status(conn, svc.caixa_do_dia(conn, LOJA_ID, data), sessao)
