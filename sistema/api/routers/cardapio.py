"""Cardápio: categorias, produtos (pizza, calzone, bebida, acompanhamento), bordas e adicionais, e simulação de preço."""
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (AdicionalCreate, AdicionalUpdate, CategoriaCreate, CategoriaUpdate, PizzaSimular, ProdutoCreate,
                         ProdutoUpdate, TIPOS_PRODUTO)
from api.security import requer
from api.services.dinheiro import fmt
from api.services.preco import calcular_pizza

router = APIRouter(tags=["cardapio"])

_P_ATUAL = "(SELECT valor FROM preco_produto WHERE produto_id = p.id AND tamanho = '{t}' ORDER BY id DESC LIMIT 1)"
_SQL_PRODUTO = (
    "SELECT p.id, p.tipo, p.nome, p.categoria_id, c.nome AS categoria, p.ingredientes, p.ativo, "
    f"{_P_ATUAL.format(t='grande')} AS preco_grande, {_P_ATUAL.format(t='broto')} AS preco_broto, "
    f"{_P_ATUAL.format(t='unico')} AS preco_unico FROM produto p LEFT JOIN categoria_pizza c ON c.id = p.categoria_id "
    "WHERE p.loja_id = %s")
_A_ATUAL = "(SELECT valor FROM preco_adicional WHERE adicional_id = a.id AND tamanho = '{t}' ORDER BY id DESC LIMIT 1)"
_SQL_ADICIONAL = ("SELECT a.id, a.tipo, a.nome, a.ativo, " + _A_ATUAL.format(t="grande") + " AS preco_grande, "
                  + _A_ATUAL.format(t="broto") + " AS preco_broto FROM adicional a WHERE a.loja_id = %s")


def _precos_em_texto(row: dict | None) -> dict | None:
    if row:
        for k in ("preco_grande", "preco_broto", "preco_unico", "preco_padrao_grande", "preco_padrao_broto"):
            if k in row:
                row[k] = fmt(row[k])
    return row


def _grava(conn, comando: str, params) -> dict:
    try:
        return conn.execute(comando, params).fetchone()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e


# ---------------------------------------------------------------- categorias
@router.get("/categorias")
def listar_categorias(sessao=Depends(requer("cardapio.ver")), conn=Depends(get_db)):
    rows = conn.execute("SELECT id, nome, preco_padrao_grande, preco_padrao_broto, ativo FROM categoria_pizza "
                        "WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()
    return [_precos_em_texto(r) for r in rows]


@router.post("/categorias", status_code=201)
def criar_categoria(d: CategoriaCreate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    nova = _grava(conn, "INSERT INTO categoria_pizza (loja_id, nome, preco_padrao_grande, preco_padrao_broto, criado_em, criado_por) "
                        "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id, nome, preco_padrao_grande, preco_padrao_broto, ativo",
                  (LOJA_ID, d.nome, d.preco_padrao_grande, d.preco_padrao_broto, agora(), sessao["usuario_id"]))
    nova = _precos_em_texto(nova)
    auditar(conn, sessao, "criar", "categoria_pizza", nova["id"], depois=nova)
    conn.commit()
    return nova


@router.patch("/categorias/{cid}")
def alterar_categoria(cid: int, d: CategoriaUpdate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    antes = conn.execute("SELECT id, nome, preco_padrao_grande, preco_padrao_broto, ativo FROM categoria_pizza "
                         "WHERE id = %s AND loja_id = %s", (cid, LOJA_ID)).fetchone()
    if not antes:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    sets = ", ".join(f"{c} = %s" for c in campos)  # nomes de coluna vêm só do schema
    novo = _grava(conn, f"UPDATE categoria_pizza SET {sets} WHERE id = %s RETURNING id, nome, preco_padrao_grande, "
                        "preco_padrao_broto, ativo", (*campos.values(), cid))
    antes, novo = _precos_em_texto(antes), _precos_em_texto(novo)
    auditar(conn, sessao, "alterar", "categoria_pizza", cid, antes={k: antes[k] for k in campos}, depois={k: novo[k] for k in campos})
    conn.commit()
    return novo


# ---------------------------------------------------------------- produtos
@router.get("/produtos")
def listar_produtos(tipo: Optional[str] = Query(default=None), ativo: Optional[bool] = None,
                    sessao=Depends(requer("cardapio.ver")), conn=Depends(get_db)):
    sql, params = _SQL_PRODUTO, [LOJA_ID]
    if tipo is not None:
        if tipo not in TIPOS_PRODUTO:
            raise HTTPException(status_code=422, detail="Tipo de produto inválido.")
        sql, params = sql + " AND p.tipo = %s", params + [tipo]
    if ativo is not None:
        sql, params = sql + " AND p.ativo = %s", params + [ativo]
    return [_precos_em_texto(r) for r in conn.execute(sql + " ORDER BY p.tipo, c.nome NULLS LAST, p.nome", params).fetchall()]


def _produto(conn, pid: int) -> dict:
    p = conn.execute(_SQL_PRODUTO + " AND p.id = %s", (LOJA_ID, pid)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return p


def _categoria_ativa(conn, cid: int):
    c = conn.execute("SELECT ativo FROM categoria_pizza WHERE id = %s AND loja_id = %s", (cid, LOJA_ID)).fetchone()
    if not c:
        raise HTTPException(status_code=400, detail="Categoria não encontrada.")
    if not c["ativo"]:
        raise HTTPException(status_code=400, detail="Categoria inativa.")


def _novo_preco(conn, sessao, produto_id: int, tamanho: str, valor: str):
    conn.execute("INSERT INTO preco_produto (produto_id, tamanho, valor, vigente_desde, criado_por) VALUES (%s,%s,%s,%s,%s)",
                 (produto_id, tamanho, valor, agora(), sessao["usuario_id"]))


@router.post("/produtos", status_code=201)
def criar_produto(d: ProdutoCreate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    if d.categoria_id is not None:
        _categoria_ativa(conn, d.categoria_id)
    novo = _grava(conn, "INSERT INTO produto (loja_id, tipo, nome, categoria_id, ingredientes, criado_em, criado_por) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.tipo, d.nome, d.categoria_id, d.ingredientes,
                                                                        agora(), sessao["usuario_id"]))
    for tam, valor in (("grande", d.preco_grande), ("broto", d.preco_broto), ("unico", d.preco_unico)):
        if valor is not None:
            _novo_preco(conn, sessao, novo["id"], tam, valor)
    criado = _precos_em_texto(_produto(conn, novo["id"]))
    auditar(conn, sessao, "criar", "produto", novo["id"], depois=criado)
    conn.commit()
    return criado


@router.patch("/produtos/{pid}")
def alterar_produto(pid: int, d: ProdutoUpdate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    atual = _produto(conn, pid)
    if atual["tipo"] == "pizza" and "preco_unico" in campos or atual["tipo"] != "pizza" and (
            "preco_grande" in campos or "preco_broto" in campos or "categoria_id" in campos):
        raise HTTPException(status_code=400, detail="Campo não se aplica a este tipo de produto.")
    if "categoria_id" in campos:
        _categoria_ativa(conn, campos["categoria_id"])
    cols = {k: v for k, v in campos.items() if k in ("nome", "categoria_id", "ingredientes", "ativo")}
    if cols:
        sets = ", ".join(f"{c} = %s" for c in cols)  # nomes de coluna vêm só do schema
        _grava(conn, f"UPDATE produto SET {sets} WHERE id = %s RETURNING id", (*cols.values(), pid))
    for tam, chave in (("grande", "preco_grande"), ("broto", "preco_broto"), ("unico", "preco_unico")):
        if chave in campos and campos[chave] != fmt(atual[chave]):
            _novo_preco(conn, sessao, pid, tam, campos[chave])
    novo = _precos_em_texto(_produto(conn, pid))
    atual = _precos_em_texto(atual)
    chaves = list(campos) + (["categoria"] if "categoria_id" in campos else [])
    auditar(conn, sessao, "alterar", "produto", pid, antes={"nome": atual["nome"], **{k: atual.get(k) for k in chaves}},
            depois={"nome": novo["nome"], **{k: novo.get(k) for k in chaves}})
    conn.commit()
    return novo


@router.get("/produtos/{pid}/historico-precos")
def historico_precos(pid: int, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    _produto(conn, pid)
    rows = conn.execute("SELECT h.tamanho, h.valor, h.vigente_desde, u.usuario AS alterado_por FROM preco_produto h "
                        "LEFT JOIN usuario u ON u.id = h.criado_por WHERE h.produto_id = %s ORDER BY h.id DESC LIMIT 200",
                        (pid,)).fetchall()
    for r in rows:
        r["valor"] = fmt(r["valor"])
    return rows


# ---------------------------------------------------------------- bordas e adicionais
def _adicional(conn, aid: int) -> dict:
    a = conn.execute(_SQL_ADICIONAL + " AND a.id = %s", (LOJA_ID, aid)).fetchone()
    if not a:
        raise HTTPException(status_code=404, detail="Borda ou adicional não encontrado.")
    return a


@router.get("/adicionais")
def listar_adicionais(ativo: Optional[bool] = None, sessao=Depends(requer("cardapio.ver")), conn=Depends(get_db)):
    sql, params = _SQL_ADICIONAL, [LOJA_ID]
    if ativo is not None:
        sql, params = sql + " AND a.ativo = %s", params + [ativo]
    return [_precos_em_texto(r) for r in conn.execute(sql + " ORDER BY a.tipo, a.nome", params).fetchall()]


@router.post("/adicionais", status_code=201)
def criar_adicional(d: AdicionalCreate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    novo = _grava(conn, "INSERT INTO adicional (loja_id, tipo, nome, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                  (LOJA_ID, d.tipo, d.nome, agora(), sessao["usuario_id"]))
    for tam, valor in (("grande", d.preco_grande), ("broto", d.preco_broto)):
        conn.execute("INSERT INTO preco_adicional (adicional_id, tamanho, valor, vigente_desde, criado_por) VALUES (%s,%s,%s,%s,%s)",
                     (novo["id"], tam, valor, agora(), sessao["usuario_id"]))
    criado = _precos_em_texto(_adicional(conn, novo["id"]))
    auditar(conn, sessao, "criar", "adicional", novo["id"], depois=criado)
    conn.commit()
    return criado


@router.patch("/adicionais/{aid}")
def alterar_adicional(aid: int, d: AdicionalUpdate, sessao=Depends(requer("cardapio.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    atual = _adicional(conn, aid)
    cols = {k: v for k, v in campos.items() if k in ("nome", "ativo")}
    if cols:
        sets = ", ".join(f"{c} = %s" for c in cols)
        _grava(conn, f"UPDATE adicional SET {sets} WHERE id = %s RETURNING id", (*cols.values(), aid))
    for tam, chave in (("grande", "preco_grande"), ("broto", "preco_broto")):
        if chave in campos and campos[chave] != fmt(atual[chave]):
            conn.execute("INSERT INTO preco_adicional (adicional_id, tamanho, valor, vigente_desde, criado_por) VALUES (%s,%s,%s,%s,%s)",
                         (aid, tam, campos[chave], agora(), sessao["usuario_id"]))
    novo, atual = _precos_em_texto(_adicional(conn, aid)), _precos_em_texto(atual)
    auditar(conn, sessao, "alterar", "adicional", aid, antes={"nome": atual["nome"], **{k: atual[k] for k in campos}},
            depois={"nome": novo["nome"], **{k: novo[k] for k in campos}})
    conn.commit()
    return novo


# ---------------------------------------------------------------- simulação de preço
@router.post("/precos/pizza")
def simular_pizza(d: PizzaSimular, sessao=Depends(requer("cardapio.ver")), conn=Depends(get_db)):
    return calcular_pizza(conn, LOJA_ID, d.tamanho, d.sabor1_id, d.sabor2_id, d.adicional_ids)
