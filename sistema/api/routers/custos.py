"""Custos: custo e margem por produto, sugestão de preço, CMV e resultado do mês."""
from datetime import date
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import FatorCorrecaoIn, FecharCmvIn
from api.security import PERMISSOES, requer
from api.services import custos as svc
from api.services.dinheiro import fmt

router = APIRouter(prefix="/custos", tags=["custos"])
ZERO = Decimal("0")
TAMANHOS = ("grande", "broto", "unico")


def _mes(m: Optional[str]) -> date:
    if m is None:
        return agora().date().replace(day=1)
    try:
        a, b = m.split("-")
        return date(int(a), int(b), 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Mês no formato AAAA-MM.") from None


def _margem(preco, custo, taxa_pct):
    if preco is None:
        return None, None
    m = preco - custo - preco * taxa_pct / 100
    return m, (m / preco * 100) if preco > 0 else None


@router.get("/produtos")
def produtos(sessao=Depends(requer("custos.ver")), conn=Depends(get_db)):
    """Custo dos insumos, preço atual e margem de contribuição de cada produto e tamanho (a Grande de dois sabores soma meia receita de cada)."""
    taxa = svc.taxa_cartao_media(conn, LOJA_ID)
    saida = []
    for p in conn.execute("SELECT p.id, p.nome, p.tipo, c.nome AS categoria FROM produto p LEFT JOIN categoria_pizza c ON c.id = p.categoria_id WHERE p.loja_id = %s AND p.ativo ORDER BY p.tipo, p.nome", (LOJA_ID,)).fetchall():
        tamanhos = [r["tamanho"] for r in conn.execute("SELECT DISTINCT tamanho FROM preco_produto WHERE produto_id = %s", (p["id"],)).fetchall()]
        for t in sorted(tamanhos, key=TAMANHOS.index):
            custo = svc.custo_unidade(conn, LOJA_ID, p["tipo"], t, p["id"])
            preco = svc.preco_vigente(conn, p["id"], t)
            m, mp = _margem(preco, custo["total"], taxa)
            saida.append({"produto_id": p["id"], "nome": p["nome"], "tipo": p["tipo"], "categoria": p["categoria"], "tamanho": t, "preco": fmt(preco), "custo": fmt(custo["total"]),
                          "margem": fmt(m) if not custo["sem_ficha"] else None, "margem_pct": fmt(mp) if mp is not None and not custo["sem_ficha"] else None,
                          "sem_ficha": custo["sem_ficha"], "itens_sem_custo": custo["sem_custo"]})
    return {"taxa_cartao_media_pct": fmt(taxa), "produtos": saida}


@router.get("/produtos/{pid}")
def produto(pid: int, tamanho: str, sabor2_id: Optional[int] = None, margem_desejada: Optional[str] = None, sessao=Depends(requer("custos.ver")), conn=Depends(get_db)):
    """Detalha o custo linha a linha. Com margem_desejada (%), sugere o preço; a decisão do preço é sempre de quem gerencia."""
    if tamanho not in TAMANHOS:
        raise HTTPException(status_code=400, detail="Tamanho inválido.")
    p = conn.execute("SELECT id, nome, tipo FROM produto WHERE id = %s AND loja_id = %s", (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    if sabor2_id and not (p["tipo"] == "pizza" and tamanho == "grande"):
        raise HTTPException(status_code=400, detail="Só a pizza Grande leva dois sabores.")
    if sabor2_id and not conn.execute("SELECT 1 FROM produto WHERE id = %s AND loja_id = %s AND tipo = 'pizza'", (sabor2_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Segundo sabor não encontrado.")
    taxa = svc.taxa_cartao_media(conn, LOJA_ID)
    c = svc.custo_unidade(conn, LOJA_ID, p["tipo"], tamanho, pid, sabor2_id)
    preco = svc.preco_vigente(conn, pid, tamanho)
    if sabor2_id:
        p2 = svc.preco_vigente(conn, sabor2_id, tamanho)
        preco = ((preco + p2) / 2).quantize(Decimal("0.01")) if preco is not None and p2 is not None else None
    m, mp = _margem(preco, c["total"], taxa)
    out = {"produto": p["nome"], "tamanho": tamanho, "sabor2_id": sabor2_id, "preco": fmt(preco), "custo": fmt(c["total"]), "margem": fmt(m), "margem_pct": fmt(mp), "taxa_cartao_media_pct": fmt(taxa),
           "sem_ficha": c["sem_ficha"], "itens_sem_custo": c["sem_custo"],
           "linhas": [{"item": x["item"], "unidade": x["unidade"], "quantidade": est_txt(x["quantidade"]), "custo_medio": est_txt(x["custo_medio"]), "fator": est_txt(x["fator"]), "valor": fmt(x["valor"])} for x in c["linhas"]]}
    if margem_desejada is not None:
        try:
            alvo = Decimal(margem_desejada.replace(",", "."))
        except Exception:
            raise HTTPException(status_code=400, detail="Margem desejada inválida.") from None
        den = 1 - alvo / 100 - taxa / 100
        if not 0 <= alvo < 100 or den <= 0:
            raise HTTPException(status_code=400, detail="Margem desejada impossível com a taxa de cartão atual.")
        out["preco_sugerido"] = fmt(c["total"] / den)
    return out


def est_txt(v):
    from api.services.estoque import txt
    return txt(v)


@router.get("/fatores")
def fatores(sessao=Depends(requer("custos.ver")), conn=Depends(get_db)):
    """Fator de correção dos insumos e preparos (1 quando não se sabe)."""
    return [r | {"fator_correcao": est_txt(r["fator_correcao"])} for r in conn.execute(
        "SELECT i.id AS item_id, i.nome, i.unidade, COALESCE(c.fator_correcao, 1) AS fator_correcao FROM item i LEFT JOIN item_custo c ON c.item_id = i.id "
        "WHERE i.loja_id = %s AND i.ativo AND i.classe IN ('insumo','preparo') ORDER BY i.nome", (LOJA_ID,)).fetchall()]


@router.put("/fatores/{item_id}")
def definir_fator(item_id: int, d: FatorCorrecaoIn, sessao=Depends(requer("custos.gerir")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM item WHERE id = %s AND loja_id = %s AND classe IN ('insumo','preparo')", (item_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    try:
        conn.execute("INSERT INTO item_custo (item_id, loja_id, fator_correcao, atualizado_em, atualizado_por) VALUES (%s,%s,%s,%s,%s) "
                     "ON CONFLICT (item_id) DO UPDATE SET fator_correcao = EXCLUDED.fator_correcao, atualizado_em = EXCLUDED.atualizado_em, atualizado_por = EXCLUDED.atualizado_por",
                     (item_id, LOJA_ID, Decimal(d.fator_correcao), agora(), sessao["usuario_id"]))
        auditar(conn, sessao, "fator", "item_custo", item_id, depois={"fator_correcao": d.fator_correcao})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"item_id": item_id, "fator_correcao": d.fator_correcao}


def _cmv_out(c: dict) -> dict:
    return {k: (fmt(v) if isinstance(v, Decimal) else v) for k, v in c.items()}


@router.get("/cmv")
def cmv(mes: Optional[str] = None, sessao=Depends(requer("custos.ver")), conn=Depends(get_db)):
    """CMV do mês: teórico (consumo das fichas) contra o real (estoque inicial + compras - estoque final). Mês fechado mostra o valor gravado."""
    m = _mes(mes)
    vivo = _cmv_out(svc.cmv_mes(conn, LOJA_ID, m))
    f = conn.execute("SELECT * FROM fechamento_cmv WHERE loja_id = %s AND mes = %s", (LOJA_ID, m)).fetchone()
    return {"fechado": bool(f), **(_cmv_out({k: f[k] for k in ("estoque_inicial", "compras", "estoque_final", "cmv_real", "cmv_teorico", "perdas", "consumo_interno", "vendas")} | {"mes": m,
            "diferenca": f["cmv_real"] - f["cmv_teorico"], "cmv_pct": (f["cmv_real"] / f["vendas"] * 100).quantize(Decimal("0.01")) if f["vendas"] > 0 else None}) if f else vivo)}


@router.post("/cmv/fechar", status_code=201)
def fechar_cmv(d: FecharCmvIn, sessao=Depends(requer("custos.gerir")), conn=Depends(get_db)):
    """Grava o CMV de um mês já terminado, depois do inventário completo. Não se refaz: o histórico não muda quando o custo médio mudar."""
    m = _mes(d.mes)
    if svc.limites_mes(m)[0] > agora().date():
        raise HTTPException(status_code=400, detail="O mês ainda não terminou.")
    conn.execute("SELECT pg_advisory_xact_lock(%s, 7002)", (LOJA_ID,))
    if conn.execute("SELECT 1 FROM fechamento_cmv WHERE loja_id = %s AND mes = %s", (LOJA_ID, m)).fetchone():
        raise HTTPException(status_code=409, detail="Este mês já foi fechado.")
    c = svc.cmv_mes(conn, LOJA_ID, m)
    if m.year < 2020 or not any(c[k] for k in ("estoque_inicial", "compras", "estoque_final", "vendas", "cmv_real")):
        raise HTTPException(status_code=400, detail="Mês sem movimento: não há CMV para fechar.")
    try:
        conn.execute("INSERT INTO fechamento_cmv (loja_id, mes, estoque_inicial, compras, estoque_final, cmv_real, cmv_teorico, perdas, consumo_interno, vendas, fechado_por, fechado_em) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (LOJA_ID, m, c["estoque_inicial"], c["compras"], c["estoque_final"], c["cmv_real"], c["cmv_teorico"], c["perdas"], c["consumo_interno"],
                                                                      c["vendas"], sessao["usuario_id"], agora()))
        auditar(conn, sessao, "fechar_cmv", "fechamento_cmv", None, depois={"mes": d.mes, "cmv_real": fmt(c["cmv_real"])})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _cmv_out(c)


@router.get("/resultado")
def resultado(mes: Optional[str] = None, sessao=Depends(requer("custos.ver")), conn=Depends(get_db)):
    """Receita, CMV, custos variáveis e fixos do mês, margem de contribuição e ponto de equilíbrio (competência pela data da venda e do título)."""
    r = svc.resultado_mes(conn, LOJA_ID, _mes(mes))
    r["fixos_detalhe"] = {k: fmt(v) for k, v in r["fixos_detalhe"].items()}
    if "rh.salarios" not in PERMISSOES.get(sessao["perfil"], set()):  # a folha aparece nas fixas, no resultado e no ponto de equilíbrio
        for k in ("custos_fixos", "resultado_operacional", "ponto_equilibrio"):
            r[k] = None
        r["fixos_detalhe"]["pessoal"] = None
    return _cmv_out(r)
