"""Produção: fila de pizzas, montagem, forno, acabamento, massa, perdas e motivos. Cada função tem a sua permissão."""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import psycopg
import psycopg.errors
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.routers.vendas import _pedido, mudar_situacao
from api.schemas import ContagemMassaIn, LoteMassaIn, MontagemErradaIn, MotivoIn, MotivoRef, MotivoUpdate, PerdaMassaIn
from api.security import permissoes_de, requer, requer_alguma, tem_permissao
from api.services import estoque, producao as svc
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
    p = conn.execute("SELECT p.id, p.pedido_id, p.tipo, p.tamanho, p.sabores, p.adicionais, p.observacoes, p.situacao, p.ordem, p.responsavel_id, p.original_id "
                     "FROM pizza_producao p WHERE p.id = %s AND p.loja_id = %s" + (" FOR UPDATE" if travar else ""), (pid, LOJA_ID)).fetchone()
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
    return tem_permissao(sessao, "producao.gerir")


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
def fila(situacao: Optional[str] = None,
         sessao=Depends(requer_alguma("producao.montagem", "producao.forno", "producao.acabamento", "producao.gerir")),
         conn=Depends(get_db)):
    """Pizzas ainda não finalizadas, na ordem de trabalho (urgentes primeiro), mais o estado do forno.
    Acesso rígido por função: cada perfil recebe só as situações da sua tela; o nome do cliente só vai a quem precisa."""
    todas = ("na lista", "em montagem", "no forno", "saiu do forno", "acabada")
    filtro = situacao or None
    if filtro and filtro not in todas:
        raise HTTPException(status_code=400, detail="Situação inválida.")
    perms = permissoes_de(sessao)
    if "producao.gerir" in perms:
        permitidas, ve_cliente, ve_forno = set(todas), True, True
    else:
        permitidas = set()
        if "producao.montagem" in perms:
            permitidas |= {"na lista", "em montagem"}
        if "producao.forno" in perms or "producao.acabamento" in perms:  # na prática as duas são do acabamento
            permitidas |= {"no forno", "saiu do forno", "acabada"}
        ve_cliente = "producao.acabamento" in perms
        ve_forno = "producao.forno" in perms or "producao.acabamento" in perms
    if filtro and filtro not in permitidas:
        raise HTTPException(status_code=403, detail="Perfil insuficiente para esta operação")
    abertas = {"na lista", "em montagem", "no forno", "saiu do forno"}
    quais = sorted([filtro] if filtro else abertas & permitidas)
    sql = f"SELECT {_COLS} {_BASE} AND ped.situacao <> 'cancelado' AND p.situacao = ANY(%s) {_ORDEM}"
    pizzas = [_out(r) | {"minha": r["responsavel_id"] == sessao["usuario_id"]} for r in conn.execute(sql, [LOJA_ID, quais]).fetchall()]
    if not ve_cliente:  # a montagem não precisa de nome de cliente nem de dados do pedido ou de outras pessoas
        for p in pizzas:
            for campo in ("cliente", "tipo_pedido", "situacao_pedido", "responsavel_id", "original_id"):
                p.pop(campo, None)
    if not ve_forno:
        return {"pizzas": pizzas, "forno": None}
    par = vigentes(conn, LOJA_ID)
    no_forno = conn.execute("SELECT count(*) AS n FROM pizza_producao WHERE loja_id = %s AND situacao = 'no forno'", (LOJA_ID,)).fetchone()["n"]
    cap = par["forno_pizzas_por_vez"]["valor"]
    return {"pizzas": pizzas, "forno": {"quantidade": no_forno, "capacidade": None if cap is None else int(cap),
                                          "tempo_min": par["forno_tempo_min"]["valor"],
                                          "acima_capacidade": cap is not None and no_forno > int(cap)}}


@router.get("/perdidas")
def perdidas_sem_refacao(sessao=Depends(requer_alguma("producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Pizzas perdidas ainda sem refação, de pedidos em produção: sem refazer, o pedido não consegue ficar acabado."""
    sql = (f"SELECT {_COLS} {_BASE} AND p.situacao = 'perdida' AND ped.situacao IN ('recebido','em producao') "
           "AND NOT EXISTS (SELECT 1 FROM pizza_producao r WHERE r.original_id = p.id) ORDER BY ped.urgente DESC, p.id")
    return [_out(r) for r in conn.execute(sql, [LOJA_ID]).fetchall()]


@router.get("/pedidos")
def pedidos_abertos(sessao=Depends(requer_alguma("producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Todos os pedidos em aberto com o andamento das pizzas (só consulta; o pedido só vira acabado à mão)."""
    rows = conn.execute(
        "SELECT ped.id, ped.id_dia, ped.tipo, ped.urgente, ped.situacao, c.nome AS cliente, ped.entrega_calculada, "
        "count(p.id) FILTER (WHERE p.situacao <> 'cancelada' AND NOT (p.situacao IN ('perdida','avulsa') AND rf.refeita IS TRUE)) AS pizzas, "
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
    # a pizza que este pizzaiolo devolveu há pouco ("sem ingredientes") só volta a ele se não houver outra
    alvo = conn.execute(f"SELECT p.id {_BASE} AND p.situacao = 'na lista' AND ped.situacao <> 'cancelado' "
                        "ORDER BY EXISTS (SELECT 1 FROM retrocesso r WHERE r.pizza_id = p.id AND r.usuario_id = %s AND r.criado_em > %s), ped.urgente DESC, p.ordem, p.id "
                        "LIMIT 1 FOR UPDATE OF p, ped SKIP LOCKED", (LOJA_ID, sessao["usuario_id"], agora() - timedelta(minutes=10))).fetchone()
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
            and not tem_permissao(sessao, "producao.acabamento"):
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


@router.post("/pizzas/{pid}/montagem-errada", status_code=201)
def montagem_errada(pid: int, d: MontagemErradaIn, sessao=Depends(requer_alguma("producao.montagem", "producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Montagem errada no sabor ou no formato/esteira. A pizza errada vira AVULSA (sai do pedido e pode ser vendida à parte; o consumo
    da montagem fica como custo) e a pizza certa recomeça: na montagem, com o mesmo pizzaiolo, se ele está com ela; no topo da lista
    se foi o acabamento (ou a gerência) que achou o erro, com a pizza no forno ou fora dele. Massa, montagem e acabamento recebem o aviso."""
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem", "no forno", "saiu do forno")
    perms = permissoes_de(sessao)
    if p["situacao"] == "em montagem":
        _minha(p, sessao)
    elif "producao.acabamento" not in perms and not _gerencia(sessao):
        raise HTTPException(status_code=403, detail="Depois da montagem, só o acabamento ou a gerência apontam o erro.")
    if ped["situacao"] not in ("recebido", "em producao"):
        raise HTTPException(status_code=409, detail=f"Pedido {ped['situacao']}: não há mais o que refazer aqui.")
    if conn.execute("SELECT 1 FROM pizza_producao WHERE original_id = %s", (pid,)).fetchone():
        raise HTTPException(status_code=409, detail="Esta pizza já foi refeita.")
    quando = agora()
    estava_na_montagem = p["situacao"] == "em montagem"
    svc.mover(conn, pid, "avulsa", sessao["usuario_id"], quando)
    # o consumo de estoque da avulsa só é baixado quando ela tiver destino: vendida (ficha inteira, saída de venda) ou descartada (perda)
    conn.execute("SELECT pg_advisory_xact_lock(5, %s)", (LOJA_ID,))
    frente = conn.execute("SELECT COALESCE(min(ordem), 1) - 1 AS o FROM pizza_producao WHERE loja_id = %s AND situacao = 'na lista'", (LOJA_ID,)).fetchone()["o"]
    novo = conn.execute(
        "INSERT INTO pizza_producao (loja_id, pedido_id, item_id, tipo, tamanho, sabores, adicionais, observacoes, ordem, original_id, situacao, responsavel_id, criado_em) "
        "SELECT loja_id, pedido_id, item_id, tipo, tamanho, sabores, adicionais, observacoes, %s, id, %s, %s, %s FROM pizza_producao WHERE id = %s RETURNING id",
        (frente, "em montagem" if estava_na_montagem else "na lista", p["responsavel_id"] if estava_na_montagem else None, quando, pid)).fetchone()
    svc.evento(conn, novo["id"], "na lista", sessao["usuario_id"], quando)  # o histórico mostra o caminho completo
    if estava_na_montagem:
        svc.evento(conn, novo["id"], "em montagem", sessao["usuario_id"], quando)
    tipo_aviso = "sabor_errado" if d.tipo == "sabor" else "formato"
    conn.execute("INSERT INTO aviso_producao (loja_id, tipo, pizza_id, nova_pizza_id, criado_por, criado_em, observacao) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                 (LOJA_ID, tipo_aviso, pid, novo["id"], sessao["usuario_id"], quando, d.observacao))
    auditar(conn, sessao, "montagem_errada", "pizza_producao", pid, depois={"nova": novo["id"], "tipo": d.tipo, "de": p["situacao"]})
    conn.commit()
    return {"id": novo["id"], "original_id": pid, "situacao": "em montagem" if estava_na_montagem else "na lista", "original": "avulsa"}


@router.post("/pizzas/{pid}/sem-ingredientes")
def sem_ingredientes(pid: int, sessao=Depends(requer("producao.montagem")), conn=Depends(get_db)):
    """Faltou ingrediente: a pizza volta para o FIM da lista e a gerência é avisada para tomar providência."""
    p, ped = _pizza_travada(conn, pid)
    _exigir(p, "em montagem")
    _minha(p, sessao)
    m = conn.execute("SELECT id, nome FROM motivo_retrocesso WHERE loja_id = %s AND ativo AND avisa_estoque ORDER BY (lower(nome) = 'falta de insumo') DESC, id LIMIT 1", (LOJA_ID,)).fetchone()
    if not m:
        raise HTTPException(status_code=400, detail="Cadastre em Motivos um motivo de retrocesso que avisa o estoque (ex.: Falta de insumo).")
    quando = agora()
    conn.execute("SELECT pg_advisory_xact_lock(5, %s)", (LOJA_ID,))
    fim = conn.execute("SELECT COALESCE(max(ordem), 0) + 1 AS o FROM pizza_producao WHERE loja_id = %s", (LOJA_ID,)).fetchone()["o"]
    try:
        conn.execute("UPDATE pizza_producao SET ordem = %s WHERE id = %s", (fim, pid))
        svc.mover(conn, pid, "na lista", sessao["usuario_id"], quando, responsavel=None)
        conn.execute("INSERT INTO retrocesso (pizza_id, motivo_id, usuario_id, criado_em) VALUES (%s,%s,%s,%s)", (pid, m["id"], sessao["usuario_id"], quando))
        conn.execute("INSERT INTO aviso_producao (loja_id, tipo, pizza_id, criado_por, criado_em) SELECT %s,'sem_ingredientes',%s,%s,%s "
                     "WHERE NOT EXISTS (SELECT 1 FROM aviso_producao WHERE pizza_id = %s AND tipo = 'sem_ingredientes' AND resolvido_em IS NULL)", (LOJA_ID, pid, sessao["usuario_id"], quando, pid))
        auditar(conn, sessao, "sem_ingredientes", "pizza_producao", pid, depois={"motivo": m["nome"]})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"id": pid, "situacao": "na lista", "avisa_estoque": True}


@router.get("/avulsas")
def avulsas(sessao=Depends(requer_alguma("producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Pizzas avulsas (montagem errada) ainda sem destino. Sem valores: quem vende é o balcão (Vendas), como pedido; aqui só se descarta."""
    return conn.execute(
        "SELECT p.id, ped.id_dia, p.tipo, p.tamanho, p.sabores, p.adicionais, p.observacoes, p.criado_em, "
        "(SELECT a.observacao FROM aviso_producao a WHERE a.pizza_id = p.id AND a.tipo IN ('sabor_errado','formato') ORDER BY a.id DESC LIMIT 1) AS observacao_acabamento "
        "FROM pizza_producao p JOIN pedido ped ON ped.id = p.pedido_id "
        "WHERE p.loja_id = %s AND p.situacao = 'avulsa' AND NOT EXISTS (SELECT 1 FROM pizza_avulsa_destino d WHERE d.pizza_id = p.id) ORDER BY p.id", (LOJA_ID,)).fetchall()


def _avulsa(conn, pid: int) -> dict:
    p = _pizza(conn, pid, travar=True)
    _exigir(p, "avulsa")
    if conn.execute("SELECT 1 FROM pizza_avulsa_destino WHERE pizza_id = %s", (pid,)).fetchone():
        raise HTTPException(status_code=409, detail="Esta pizza avulsa já tem destino.")
    return p


@router.post("/avulsas/{pid}/descartar")
def avulsa_descartada(pid: int, d: MotivoRef, sessao=Depends(requer_alguma("producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Sem venda: a avulsa vira perda, com motivo."""
    p = _avulsa(conn, pid)
    m = _motivo(conn, "motivo_perda", d.motivo_id)
    quando = agora()
    svc.registrar_perda_pizza(conn, LOJA_ID, p, m["id"], sessao["usuario_id"], quando)
    foi_ao_forno = conn.execute("SELECT 1 FROM evento_producao WHERE pizza_id = %s AND situacao = 'no forno' LIMIT 1", (pid,)).fetchone() is not None
    estoque.baixar_pizza(conn, LOJA_ID, pid, "perdida", sessao["usuario_id"], quando, "Pizza avulsa descartada", ficha_inteira=foi_ao_forno)  # já assada: perde a ficha inteira
    try:
        conn.execute("INSERT INTO pizza_avulsa_destino (pizza_id, destino, motivo_id, usuario_id, criado_em) VALUES (%s,'perda',%s,%s,%s)", (pid, m["id"], sessao["usuario_id"], quando))
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Esta pizza avulsa já tem destino.")
    auditar(conn, sessao, "avulsa_descartada", "pizza_producao", pid, depois={"motivo": m["nome"]})
    conn.commit()
    return {"id": pid, "destino": "perda"}


_ROTULO_AVISO = {"sabor_errado": "Montagem errada no sabor", "formato": "Problema no formato/esteira", "sem_ingredientes": "Sem ingredientes"}


@router.get("/avisos")
def avisos(sessao=Depends(requer_alguma("producao.massa", "producao.montagem", "producao.forno", "producao.acabamento", "producao.gerir")), conn=Depends(get_db)):
    """Avisos abertos das últimas 6 horas, para todos os setores da Produção. Só o acabamento e a gerência veem o cliente."""
    perms = permissoes_de(sessao)
    ve_cliente = "producao.acabamento" in perms or "producao.gerir" in perms
    desde = agora() - timedelta(hours=6) if "producao.gerir" not in perms else agora() - timedelta(days=3)  # a gerência vê o que ninguém resolveu
    rows = conn.execute(
        "SELECT a.id, a.tipo, a.criado_em, p.id AS pizza_id, ped.id_dia, p.tipo AS tipo_pizza, p.tamanho, p.sabores, c.nome AS cliente, u.nome AS por "
        "FROM aviso_producao a JOIN pizza_producao p ON p.id = a.pizza_id JOIN pedido ped ON ped.id = p.pedido_id "
        "LEFT JOIN cliente c ON c.id = ped.cliente_id LEFT JOIN usuario u ON u.id = a.criado_por "
        "WHERE a.loja_id = %s AND a.resolvido_em IS NULL AND a.criado_em > %s AND ped.situacao <> 'cancelado' ORDER BY a.id DESC LIMIT 30", (LOJA_ID, desde)).fetchall()
    for x in rows:
        x["rotulo"] = _ROTULO_AVISO[x["tipo"]]
        if not ve_cliente:
            x.pop("cliente", None)
    return rows


@router.post("/avisos/{aid}/resolver")
def resolver_aviso(aid: int, sessao=Depends(requer_alguma("producao.gerir", "producao.acabamento")), conn=Depends(get_db)):
    r = conn.execute("UPDATE aviso_producao SET resolvido_em = %s, resolvido_por = %s WHERE id = %s AND loja_id = %s AND resolvido_em IS NULL RETURNING id",
                     (agora(), sessao["usuario_id"], aid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Aviso não encontrado ou já resolvido.")
    auditar(conn, sessao, "resolver", "aviso_producao", aid)
    conn.commit()
    return {"id": aid, "resolvido": True}


# ---------------------------------------------------------------- massa
@router.get("/massa")
def massa(sessao=Depends(requer_alguma("producao.massa", "producao.gerir")), conn=Depends(get_db)):
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
def motivos(sessao=Depends(requer_alguma("producao.montagem", "producao.perda", "producao.perda_massa", "producao.refazer", "producao.gerir")), conn=Depends(get_db)):
    perms = permissoes_de(sessao)
    ve_retro = bool(perms & {"producao.montagem", "producao.gerir"})  # cada função recebe só a lista de motivos que usa
    ve_perda = bool(perms & {"producao.perda", "producao.perda_massa", "producao.refazer", "producao.gerir"})
    return {"retrocesso": conn.execute("SELECT id, nome, avisa_estoque, ativo FROM motivo_retrocesso WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall() if ve_retro else [],
            "perda": conn.execute("SELECT id, nome, ativo FROM motivo_perda WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall() if ve_perda else []}


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
