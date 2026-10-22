"""Produção: fila de pizzas, montagem, forno, acabamento, massa, perdas e motivos. Cada função tem a sua permissão."""
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.routers.vendas import _pedido, mudar_situacao
from api.schemas import ContagemMassaIn, LoteMassaIn, MotivoIn, MotivoRef, MotivoUpdate, PerdaMassaIn
from api.security import PERMISSOES, requer
from api.services import producao as svc
from api.services.parametros import vigentes

router = APIRouter(prefix="/producao", tags=["producao"])
_COLS = ("p.id, p.pedido_id, ped.id_dia, ped.tipo AS tipo_pedido, ped.urgente, ped.situacao AS situacao_pedido, c.nome AS cliente, "
         "p.tipo, p.tamanho, p.sabores, p.adicionais, p.observacoes, p.situacao, p.ordem, p.responsavel_id, p.original_id")
_BASE = ("FROM pizza_producao p JOIN pedido ped ON ped.id = p.pedido_id LEFT JOIN cliente c ON c.id = ped.cliente_id "
         "WHERE p.loja_id = %s")
_ORDEM = "ORDER BY ped.urgente DESC, p.ordem, p.id"


def _out(r: dict) -> dict:
    r = dict(r)
    r["ordem"] = str(r["ordem"].normalize()) if r.get("ordem") is not None else None
    return r


def _pizza(conn, pid: int, travar=False) -> dict:
    p = conn.execute(f"SELECT p.id, p.pedido_id, p.tipo, p.tamanho, p.sabores, p.adicionais, p.observacoes, p.situacao, p.ordem, p.responsavel_id, p.original_id "
                     f"FROM pizza_producao p WHERE p.id = %s AND p.loja_id = %s" + (" FOR UPDATE" if travar else ""), (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pizza não encontrada.")
    return p


def _pizza_travada(conn, pid: int):
    """Trava o pedido e depois a pizza, na mesma ordem do cancelamento, para as duas operações nunca esperarem uma pela outra."""
    r = conn.execute("SELECT pedido_id FROM pizza_producao WHERE id = %s AND loja_id = %s", (pid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Pizza não encontrada.")
    ped = _pedido(conn, r["pedido_id"], travar=True)
    return _pizza(conn, pid, travar=True), ped


def _exigir(p: dict, *situacoes: str) -> None:
    if p["situacao"] not in situacoes:
        raise HTTPException(status_code=409, detail=f"A pizza está '{p['situacao']}': esta ação não se aplica.")


def _gerencia(sessao) -> bool:
    return "producao.gerir" in PERMISSOES.get(sessao["perfil"], set())


def _motivo(conn, tabela: str, motivo_id: int) -> dict:
    m = conn.execute(f"SELECT id, nome, ativo{', avisa_estoque' if tabela == 'motivo_retrocesso' else ''} FROM {tabela} WHERE id = %s AND loja_id = %s",
                     (motivo_id, LOJA_ID)).fetchone()  # nome da tabela só vem do código
    if not m:
        raise HTTPException(status_code=404, detail="Motivo não encontrado.")
    if not m["ativo"]:
        raise HTTPException(status_code=400, detail="Este motivo está inativo.")
    return m


# ---------------------------------------------------------------- consulta
@router.get("/fila")
def fila(situacao: Optional[str] = None, sessao=Depends(requer("producao.ver")), conn=Depends(get_db)):
    """Pizzas ainda não finalizadas, na ordem de trabalho (urgentes primeiro), mais o estado do forno."""
    filtro = situacao or None
    if filtro and filtro not in ("na lista", "em montagem", "no forno", "saiu do forno", "acabada"):
        raise HTTPException(status_code=400, detail="Situação inválida.")
    sit = "(%s)" if filtro else "('na lista','em montagem','no forno','saiu do forno')"
    sql = f"SELECT {_COLS} {_BASE} AND ped.situacao <> 'cancelado' AND p.situacao IN {sit if filtro else sit} {_ORDEM}"
    params = [LOJA_ID] + ([filtro] if filtro else [])
    pizzas = [_out(r) | {"minha": r["responsavel_id"] == sessao["usuario_id"]} for r in conn.execute(sql, params).fetchall()]
    par = vigentes(conn, LOJA_ID)
    no_forno = sum(1 for p in pizzas if p["situacao"] == "no forno") if not filtro else conn.execute(
        "SELECT count(*) AS n FROM pizza_producao WHERE loja_id = %s AND situacao = 'no forno'", (LOJA_ID,)).fetchone()["n"]
    cap = par["forno_pizzas_por_vez"]["valor"]
    return {"pizzas": pizzas, "forno": {"quantidade": no_forno, "capacidade": None if cap is None else int(cap),
                                          "tempo_min": par["forno_tempo_min"]["valor"],
                                          "acima_capacidade": cap is not None and no_forno > int(cap)}}


@router.get("/pedidos")
def pedidos_abertos(sessao=Depends(requer("producao.ver")), conn=Depends(get_db)):
    """Todos os pedidos em aberto com o andamento das pizzas (só consulta; o pedido só vira acabado à mão)."""
    rows = conn.execute(
        "SELECT ped.id, ped.id_dia, ped.tipo, ped.urgente, ped.situacao, c.nome AS cliente, ped.entrega_calculada, "
        "count(p.id) FILTER (WHERE p.situacao <> 'cancelada' AND NOT (p.situacao = 'perdida' AND rf.refeita IS TRUE)) AS pizzas, "
        "count(p.id) FILTER (WHERE p.situacao = 'acabada') AS acabadas "
        "FROM pedido ped LEFT JOIN cliente c ON c.id = ped.cliente_id LEFT JOIN pizza_producao p ON p.pedido_id = ped.id "
        "LEFT JOIN LATERAL (SELECT true AS refeita FROM pizza_producao r WHERE r.original_id = p.id LIMIT 1) rf ON true "
        "WHERE ped.loja_id = %s AND ped.situacao IN ('recebido','em producao','acabado') GROUP BY ped.id, c.nome ORDER BY ped.urgente DESC, ped.id",
        (LOJA_ID,)).fetchall()
    return rows


# ---------------------------------------------------------------- montagem (pizzaiolo)
@router.post("/pizzas/proxima")
def pegar_proxima(sessao=Depends(requer("producao.montagem")), conn=Depends(get_db)):
    """O pizzaiolo recebe sempre a próxima pizza. Se já tem uma em montagem, devolve a mesma."""
    conn.execute("SELECT pg_advisory_xact_lock(6, %s)", (sessao["usuario_id"],))
    atual = conn.execute(f"SELECT {_COLS} {_BASE} AND p.situacao = 'em montagem' AND p.responsavel_id = %s", (LOJA_ID, sessao["usuario_id"])).fetchone()
    if atual:
        conn.rollback()
        return _out(atual)
    alvo = conn.execute(f"SELECT p.id {_BASE} AND p.situacao = 'na lista' AND ped.situacao <> 'cancelado' {_ORDEM} LIMIT 1 FOR UPDATE OF p, ped SKIP LOCKED",
                        (LOJA_ID,)).fetchone()
    if not alvo:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Não há pizza na lista.")
    quando = agora()
    svc.mover(conn, alvo["id"], "em montagem", sessao["usuario_id"], quando, responsavel=sessao["usuario_id"])
    ped = conn.execute("SELECT pedido_id FROM pizza_producao WHERE id = %s", (alvo["id"],)).fetchone()
    p = _pedido(conn, ped["pedido_id"], travar=True)
    if p["situacao"] == "recebido":
        mudar_situacao(conn, sessao, p, "em producao")
    out = conn.execute(f"SELECT {_COLS} {_BASE} AND p.id = %s", (LOJA_ID, alvo["id"])).fetchone()
    conn.commit()
    return _out(out)


def _minha(p: dict, sessao) -> None:
    if p["responsavel_id"] != sessao["usuario_id"] and not _gerencia(sessao):
        raise HTTPException(status_code=403, detail="Esta pizza está com outro pizzaiolo.")


@router.post("/pizzas/{pid}/produzida")
def produzida(pid: int, sessao=Depends(requer("producao.montagem")), conn=Depends(get_db)):
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem")
    _minha(p, sessao)
    svc.mover(conn, pid, "no forno", sessao["usuario_id"], agora())
    conn.commit()
    return {"id": pid, "situacao": "no forno"}


@router.post("/pizzas/{pid}/retroceder")
def retroceder(pid: int, d: MotivoRef, sessao=Depends(requer("producao.montagem")), conn=Depends(get_db)):
    """Volta a pizza atual uma posição na fila, com motivo obrigatório da tabela."""
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem")
    _minha(p, sessao)
    m = _motivo(conn, "motivo_retrocesso", d.motivo_id)
    quando = agora()
    conn.execute("SELECT pg_advisory_xact_lock(5, %s)", (LOJA_ID,))  # mesma trava da criação: ordens nunca se repetem
    def _proximas():  # dentro do mesmo grupo de urgência da pizza
        return conn.execute(f"SELECT p.ordem {_BASE} AND p.situacao = 'na lista' AND p.id <> %s AND ped.urgente = %s AND ped.situacao <> 'cancelado' "
                            "ORDER BY p.ordem, p.id LIMIT 2", (LOJA_ID, pid, ped["urgente"])).fetchall()
    prox = _proximas()
    if len(prox) == 2 and prox[1]["ordem"] - prox[0]["ordem"] < Decimal("0.001"):  # espaço esgotado: renumera a fila e recalcula
        conn.execute("UPDATE pizza_producao SET ordem = n.n FROM (SELECT id, row_number() OVER (ORDER BY ordem, id) AS n FROM pizza_producao "
                     "WHERE loja_id = %s AND situacao = 'na lista') n WHERE pizza_producao.id = n.id", (LOJA_ID,))
        prox = _proximas()
    if len(prox) == 2:
        nova = (prox[0]["ordem"] + prox[1]["ordem"]) / 2
    elif len(prox) == 1:
        nova = prox[0]["ordem"] + 1
    else:
        nova = p["ordem"]
    try:
        conn.execute("UPDATE pizza_producao SET ordem = %s WHERE id = %s", (nova, pid))
        svc.mover(conn, pid, "na lista", sessao["usuario_id"], quando, responsavel=None)
        conn.execute("INSERT INTO retrocesso (pizza_id, motivo_id, usuario_id, criado_em) VALUES (%s,%s,%s,%s)", (pid, m["id"], sessao["usuario_id"], quando))
        auditar(conn, sessao, "retroceder", "pizza_producao", pid, depois={"motivo": m["nome"], "avisa_estoque": m.get("avisa_estoque")})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"id": pid, "situacao": "na lista", "avisa_estoque": bool(m.get("avisa_estoque"))}


# ---------------------------------------------------------------- forno e acabamento
@router.post("/pizzas/{pid}/saiu-do-forno")
def saiu_do_forno(pid: int, sessao=Depends(requer("producao.forno")), conn=Depends(get_db)):
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "no forno")
    svc.mover(conn, pid, "saiu do forno", sessao["usuario_id"], agora())
    conn.commit()
    return {"id": pid, "situacao": "saiu do forno"}


@router.post("/pizzas/{pid}/acabada")
def acabada(pid: int, sessao=Depends(requer("producao.acabamento")), conn=Depends(get_db)):
    """Marca a pizza como acabada e devolve os dados da etiqueta (cliente, Id do pedido e sabor)."""
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "saiu do forno")
    quando = agora()
    svc.mover(conn, pid, "acabada", sessao["usuario_id"], quando)
    conn.execute("INSERT INTO etiqueta_impressa (pizza_id, usuario_id, criado_em) VALUES (%s,%s,%s)", (pid, sessao["usuario_id"], quando))
    et = conn.execute("SELECT ped.id_dia, c.nome AS cliente FROM pedido ped LEFT JOIN cliente c ON c.id = ped.cliente_id WHERE ped.id = %s", (p["pedido_id"],)).fetchone()
    conn.commit()
    return {"id": pid, "situacao": "acabada", "etiqueta": {"cliente": et["cliente"] or "Balcão", "id_dia": et["id_dia"], "sabores": p["sabores"], "tamanho": p["tamanho"]}}


@router.post("/pedidos/{ped_id}/acabado")
def pedido_acabado(ped_id: int, sessao=Depends(requer("producao.acabamento")), conn=Depends(get_db)):
    """O pedido é marcado como acabado sempre à mão, e só com todas as pizzas acabadas (ou refeitas)."""
    p = _pedido(conn, ped_id, travar=True)
    if p["situacao"] not in ("recebido", "em producao"):
        raise HTTPException(status_code=409, detail=f"Pedido {p['situacao']}: não pode ser marcado como acabado.")
    conn.execute("SELECT 1 FROM pizza_producao WHERE pedido_id = %s FOR UPDATE", (ped_id,)).fetchall()
    pend = svc.pizzas_pendentes(conn, ped_id)
    if pend:
        raise HTTPException(status_code=409, detail=f"Faltam {pend} pizza(s) para acabar.")
    if p["situacao"] == "recebido":
        p = mudar_situacao(conn, sessao, p, "em producao")
    p = mudar_situacao(conn, sessao, p, "acabado")
    conn.commit()
    return {"id": ped_id, "situacao": p["situacao"]}


# ---------------------------------------------------------------- perdas e refação
@router.post("/pizzas/{pid}/perder")
def perder(pid: int, d: MotivoRef, sessao=Depends(requer("producao.perda")), conn=Depends(get_db)):
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem", "no forno", "saiu do forno", "acabada")
    if ped["situacao"] in ("cancelado", "despachado ou retirado"):
        raise HTTPException(status_code=409, detail=f"Pedido {ped['situacao']}: não há mais o que perder aqui.")
    if p["situacao"] == "em montagem" and p["responsavel_id"] != sessao["usuario_id"] and not _gerencia(sessao) \
            and "producao.acabamento" not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=403, detail="Esta pizza está com outro pizzaiolo.")
    m = _motivo(conn, "motivo_perda", d.motivo_id)
    quando = agora()
    svc.mover(conn, pid, "perdida", sessao["usuario_id"], quando)
    svc.registrar_perda_pizza(conn, LOJA_ID, p, m["id"], sessao["usuario_id"], quando)
    auditar(conn, sessao, "perder", "pizza_producao", pid, depois={"motivo": m["nome"]})
    conn.commit()
    return {"id": pid, "situacao": "perdida"}


@router.post("/pizzas/{pid}/refazer", status_code=201)
def refazer(pid: int, d: MotivoRef, sessao=Depends(requer("producao.refazer")), conn=Depends(get_db)):
    """Nova pizza ligada à original, na frente da fila; a original vira perda, com o motivo."""
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem", "no forno", "saiu do forno", "acabada", "perdida")
    if conn.execute("SELECT 1 FROM pizza_producao WHERE original_id = %s", (pid,)).fetchone():
        raise HTTPException(status_code=409, detail="Esta pizza já foi refeita.")
    if ped["situacao"] not in ("recebido", "em producao"):
        raise HTTPException(status_code=409, detail=f"Pedido {ped['situacao']}: refação só enquanto o pedido está em produção. Para reclamação depois, faça um novo pedido.")
    m = _motivo(conn, "motivo_perda", d.motivo_id)
    quando = agora()
    if p["situacao"] != "perdida":
        svc.mover(conn, pid, "perdida", sessao["usuario_id"], quando)
        svc.registrar_perda_pizza(conn, LOJA_ID, p, m["id"], sessao["usuario_id"], quando)
    conn.execute("SELECT pg_advisory_xact_lock(5, %s)", (LOJA_ID,))
    frente = conn.execute("SELECT COALESCE(min(ordem), 1) - 1 AS o FROM pizza_producao WHERE loja_id = %s AND situacao = 'na lista'", (LOJA_ID,)).fetchone()["o"]
    novo = conn.execute(
        "INSERT INTO pizza_producao (loja_id, pedido_id, item_id, tipo, tamanho, sabores, adicionais, observacoes, ordem, original_id, criado_em) "
        "SELECT loja_id, pedido_id, item_id, tipo, tamanho, sabores, adicionais, observacoes, %s, id, %s FROM pizza_producao WHERE id = %s RETURNING id",
        (frente, quando, pid)).fetchone()
    svc.evento(conn, novo["id"], "na lista", sessao["usuario_id"], quando)
    auditar(conn, sessao, "refazer", "pizza_producao", pid, depois={"nova": novo["id"], "motivo": m["nome"]})
    conn.commit()
    return {"id": novo["id"], "original_id": pid, "situacao": "na lista"}


# ---------------------------------------------------------------- massa
@router.get("/massa")
def massa(sessao=Depends(requer("producao.ver")), conn=Depends(get_db)):
    return svc.saldo_massa(conn, LOJA_ID)


@router.post("/massa/lote", status_code=201)
def lote(d: LoteMassaIn, sessao=Depends(requer("producao.massa")), conn=Depends(get_db)):
    quando = agora()
    conn.execute("INSERT INTO lote_massa (loja_id, tamanho, quantidade, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s)",
                 (LOJA_ID, d.tamanho, d.quantidade, sessao["usuario_id"], quando))
    auditar(conn, sessao, "lote_massa", "lote_massa", None, depois={"tamanho": d.tamanho, "quantidade": d.quantidade})
    conn.commit()
    return svc.saldo_massa(conn, LOJA_ID)


@router.post("/massa/contagem", status_code=201)
def contagem(d: ContagemMassaIn, sessao=Depends(requer("producao.massa")), conn=Depends(get_db)):
    conn.execute("INSERT INTO contagem_massa (loja_id, tamanho, quantidade, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s)",
                 (LOJA_ID, d.tamanho, d.quantidade, sessao["usuario_id"], agora()))
    auditar(conn, sessao, "contagem_massa", "contagem_massa", None, depois={"tamanho": d.tamanho, "quantidade": d.quantidade})
    conn.commit()
    return svc.saldo_massa(conn, LOJA_ID)


@router.post("/massa/perda", status_code=201)
def perda_massa(d: PerdaMassaIn, sessao=Depends(requer("producao.perda_massa")), conn=Depends(get_db)):
    m = _motivo(conn, "motivo_perda", d.motivo_id)
    conn.execute("INSERT INTO perda (loja_id, tipo, tamanho, quantidade, motivo_id, usuario_id, criado_em) VALUES (%s,'massa',%s,%s,%s,%s,%s)",
                 (LOJA_ID, d.tamanho, d.quantidade, m["id"], sessao["usuario_id"], agora()))
    auditar(conn, sessao, "perda_massa", "perda", None, depois={"tamanho": d.tamanho, "quantidade": d.quantidade, "motivo": m["nome"]})
    conn.commit()
    return svc.saldo_massa(conn, LOJA_ID)


# ---------------------------------------------------------------- motivos (listas em tabela)
@router.get("/motivos")
def motivos(sessao=Depends(requer("producao.ver")), conn=Depends(get_db)):
    return {"retrocesso": conn.execute("SELECT id, nome, avisa_estoque, ativo FROM motivo_retrocesso WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall(),
            "perda": conn.execute("SELECT id, nome, ativo FROM motivo_perda WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall()}


@router.post("/motivos/iniciar-padrao", status_code=201)
def iniciar_padrao(sessao=Depends(requer("producao.gerir")), conn=Depends(get_db)):
    """Cria as listas iniciais combinadas (retrocesso e perda). Só roda se as duas estiverem vazias; depois é cadastro livre."""
    conn.execute("SELECT pg_advisory_xact_lock(7, %s)", (LOJA_ID,))
    if (conn.execute("SELECT count(*) AS n FROM motivo_retrocesso WHERE loja_id = %s", (LOJA_ID,)).fetchone()["n"]
            or conn.execute("SELECT count(*) AS n FROM motivo_perda WHERE loja_id = %s AND lower(nome) <> lower(%s)", (LOJA_ID, svc.MOTIVO_CANCELAMENTO)).fetchone()["n"]):
        raise HTTPException(status_code=409, detail="Já existem motivos cadastrados.")
    for nome, avisa in svc.MOTIVOS_RETROCESSO_PADRAO:
        conn.execute("INSERT INTO motivo_retrocesso (loja_id, nome, avisa_estoque) VALUES (%s,%s,%s)", (LOJA_ID, nome, avisa))
    for nome in svc.MOTIVOS_PERDA_PADRAO:
        conn.execute("INSERT INTO motivo_perda (loja_id, nome) VALUES (%s,%s) ON CONFLICT DO NOTHING", (LOJA_ID, nome))
    auditar(conn, sessao, "iniciar_padrao", "motivo", None)
    conn.commit()
    return motivos(sessao, conn)


def _tabela(tipo: str) -> str:
    if tipo not in ("retrocesso", "perda"):
        raise HTTPException(status_code=404, detail="Lista de motivos desconhecida.")
    return "motivo_" + tipo


@router.post("/motivos/{tipo}", status_code=201)
def criar_motivo(tipo: str, d: MotivoIn, sessao=Depends(requer("producao.gerir")), conn=Depends(get_db)):
    t = _tabela(tipo)
    try:
        if t == "motivo_retrocesso":
            r = conn.execute("INSERT INTO motivo_retrocesso (loja_id, nome, avisa_estoque) VALUES (%s,%s,%s) RETURNING id, nome, avisa_estoque, ativo", (LOJA_ID, d.nome, d.avisa_estoque)).fetchone()
        else:
            r = conn.execute("INSERT INTO motivo_perda (loja_id, nome) VALUES (%s,%s) RETURNING id, nome, ativo", (LOJA_ID, d.nome)).fetchone()
        auditar(conn, sessao, "criar", t, r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.patch("/motivos/{tipo}/{mid}")
def alterar_motivo(tipo: str, mid: int, d: MotivoUpdate, sessao=Depends(requer("producao.gerir")), conn=Depends(get_db)):
    t = _tabela(tipo)
    campos = d.model_dump(exclude_unset=True)
    if t == "motivo_perda":
        campos.pop("avisa_estoque", None)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute(f"SELECT 1 FROM {t} WHERE id = %s AND loja_id = %s", (mid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Motivo não encontrado.")
    sets = ", ".join(f"{c} = %s" for c in campos)  # nomes de coluna vêm só do schema
    try:
        r = conn.execute(f"UPDATE {t} SET {sets} WHERE id = %s RETURNING *", (*campos.values(), mid)).fetchone()
        auditar(conn, sessao, "alterar", t, mid, depois={"campos": sorted(campos)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r
