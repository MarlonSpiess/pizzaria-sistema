"""Clientes e entregadores. Nada é apagado: só inativado."""
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import _telefone, ClienteCreate, ClienteUpdate, EntregadorCreate, EntregadorUpdate
from api.security import requer

router = APIRouter(tags=["pessoas"])
_C = "id, nome, telefone, endereco, ativo"
_E = "id, nome, telefone, ativo"


def _grava(conn, comando, params):
    try:
        return conn.execute(comando, params).fetchone()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@router.get("/clientes")
def listar_clientes(q: Optional[str] = Query(default=None, max_length=60), limite: int = Query(default=50, ge=1, le=200),
                    sessao=Depends(requer("clientes.ver")), conn=Depends(get_db)):
    sql, params = f"SELECT {_C} FROM cliente WHERE loja_id = %s", [LOJA_ID]
    q = q.replace("\x00", "") if q else q
    if q and q.strip():
        digitos = "".join(c for c in q if c in "0123456789")
        sql += " AND (lower(nome) LIKE lower(%s) ESCAPE '\\'" + (" OR telefone LIKE %s)" if digitos else ")")
        params += [_like(q.strip())] + ([_like(digitos)] if digitos else [])
    return conn.execute(sql + " ORDER BY nome LIMIT %s", (*params, limite)).fetchall()


@router.get("/clientes/por-telefone/{telefone}")
def cliente_por_telefone(telefone: str, sessao=Depends(requer("clientes.ver")), conn=Depends(get_db)):
    try:
        digitos = _telefone(telefone)
    except ValueError:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    c = conn.execute(f"SELECT {_C} FROM cliente WHERE loja_id = %s AND telefone = %s", (LOJA_ID, digitos)).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return c


@router.post("/clientes", status_code=201)
def criar_cliente(d: ClienteCreate, sessao=Depends(requer("clientes.editar")), conn=Depends(get_db)):
    novo = _grava(conn, f"INSERT INTO cliente (loja_id, nome, telefone, endereco, criado_em, criado_por) "
                        f"VALUES (%s,%s,%s,%s,%s,%s) RETURNING {_C}", (LOJA_ID, d.nome, d.telefone, d.endereco, agora(), sessao["usuario_id"]))
    auditar(conn, sessao, "criar", "cliente", novo["id"], depois={"nome": novo["nome"]})  # sem telefone nem endereço na auditoria
    conn.commit()
    return novo


@router.patch("/clientes/{cid}")
def alterar_cliente(cid: int, d: ClienteUpdate, sessao=Depends(requer("clientes.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute("SELECT 1 FROM cliente WHERE id = %s AND loja_id = %s", (cid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    sets = ", ".join(f"{c} = %s" for c in campos)  # nomes de coluna vêm só do schema
    novo = _grava(conn, f"UPDATE cliente SET {sets} WHERE id = %s RETURNING {_C}", (*campos.values(), cid))
    auditar(conn, sessao, "alterar", "cliente", cid, depois={"campos": sorted(campos), "nome": novo["nome"]})
    conn.commit()
    return novo


@router.get("/entregadores")
def listar_entregadores(ativo: Optional[bool] = None, sessao=Depends(requer("entregadores.ver")), conn=Depends(get_db)):
    sql, params = f"SELECT {_E} FROM entregador WHERE loja_id = %s", [LOJA_ID]
    if ativo is not None:
        sql, params = sql + " AND ativo = %s", params + [ativo]
    return conn.execute(sql + " ORDER BY nome", params).fetchall()


@router.post("/entregadores", status_code=201)
def criar_entregador(d: EntregadorCreate, sessao=Depends(requer("entregadores.editar")), conn=Depends(get_db)):
    novo = _grava(conn, f"INSERT INTO entregador (loja_id, nome, telefone, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s) RETURNING {_E}",
                  (LOJA_ID, d.nome, d.telefone, agora(), sessao["usuario_id"]))
    auditar(conn, sessao, "criar", "entregador", novo["id"], depois={"nome": novo["nome"]})
    conn.commit()
    return novo


@router.patch("/entregadores/{eid}")
def alterar_entregador(eid: int, d: EntregadorUpdate, sessao=Depends(requer("entregadores.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute("SELECT 1 FROM entregador WHERE id = %s AND loja_id = %s", (eid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Entregador não encontrado.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    novo = _grava(conn, f"UPDATE entregador SET {sets} WHERE id = %s RETURNING {_E}", (*campos.values(), eid))
    auditar(conn, sessao, "alterar", "entregador", eid, depois={"campos": sorted(campos), "nome": novo["nome"]})
    conn.commit()
    return novo
