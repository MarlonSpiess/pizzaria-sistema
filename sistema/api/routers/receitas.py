"""Itens, fichas técnicas (versões só de inserção) e etapas de produção. Cadastro apenas: sem baixa de estoque nem custo."""
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import EtapaCreate, EtapasIn, EtapaUpdate, FichaIn, ItemCreate, ItemUpdate, TIPOS_PRODUTO
from api.security import requer
from api.services import parametros as svc_parametros
from api.services.dinheiro import fmt

router = APIRouter(tags=["receitas"])

_I = "id, nome, classe, unidade, ativo"
_E = "id, nome, funcao, ativo"


def _grava(conn, comando: str, params):
    try:
        return conn.execute(comando, params).fetchone()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e


# ---------------------------------------------------------------- itens
@router.get("/itens")
def listar_itens(classe: Optional[str] = None, ativo: Optional[bool] = None,
                 sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    sql, params = f"SELECT {_I} FROM item WHERE loja_id = %s", [LOJA_ID]
    if classe is not None:
        sql, params = sql + " AND classe = %s", params + [classe]
    if ativo is not None:
        sql, params = sql + " AND ativo = %s", params + [ativo]
    return conn.execute(sql + " ORDER BY classe, nome", params).fetchall()


@router.post("/itens", status_code=201)
def criar_item(d: ItemCreate, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    novo = _grava(conn, f"INSERT INTO item (loja_id, nome, classe, unidade, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s) "
                        f"RETURNING {_I}", (LOJA_ID, d.nome, d.classe, d.unidade, agora(), sessao["usuario_id"]))
    auditar(conn, sessao, "criar", "item", novo["id"], depois=novo)
    conn.commit()
    return novo


@router.patch("/itens/{iid}")
def alterar_item(iid: int, d: ItemUpdate, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    antes = conn.execute(f"SELECT {_I} FROM item WHERE id = %s AND loja_id = %s", (iid, LOJA_ID)).fetchone()
    if not antes:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    sets = ", ".join(f"{c} = %s" for c in campos)  # nomes de coluna vêm só do schema
    novo = _grava(conn, f"UPDATE item SET {sets} WHERE id = %s RETURNING {_I}", (*campos.values(), iid))
    auditar(conn, sessao, "alterar", "item", iid, antes={k: antes[k] for k in campos}, depois={k: novo[k] for k in campos})
    conn.commit()
    return novo


# ---------------------------------------------------------------- fichas técnicas
_TAMANHOS = ("grande", "broto")


def _dono(conn, tipo: str, dono_id: Optional[int], tamanho: Optional[str]):
    """Devolve (condição SQL, parâmetros, colunas a gravar, rótulo). 404/400 se o dono não existe ou não vale."""
    if tipo == "produto":
        if not conn.execute("SELECT 1 FROM produto WHERE id = %s AND loja_id = %s", (dono_id, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        return "produto_id = %s", [dono_id], {"produto_id": dono_id}, f"produto {dono_id}"
    if tipo == "adicional":
        if tamanho not in _TAMANHOS:
            raise HTTPException(status_code=400, detail="Tamanho deve ser grande ou broto.")
        if not conn.execute("SELECT 1 FROM adicional WHERE id = %s AND loja_id = %s", (dono_id, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Borda ou adicional não encontrado.")
        return "adicional_id = %s AND tamanho = %s", [dono_id, tamanho], {"adicional_id": dono_id, "tamanho": tamanho}, f"adicional {dono_id} {tamanho}"
    if tipo == "preparo":
        it = conn.execute("SELECT classe FROM item WHERE id = %s AND loja_id = %s", (dono_id, LOJA_ID)).fetchone()
        if not it:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        if it["classe"] != "preparo":
            raise HTTPException(status_code=400, detail="Só um item da classe preparo tem ficha própria.")
        return "item_id = %s", [dono_id], {"item_id": dono_id}, f"preparo {dono_id}"
    if tamanho not in _TAMANHOS:
        raise HTTPException(status_code=400, detail="Tamanho deve ser grande ou broto.")
    return ("tamanho = %s AND produto_id IS NULL AND adicional_id IS NULL AND item_id IS NULL", [tamanho],
            {"tamanho": tamanho}, f"base {tamanho}")


def _ficha_atual(conn, cond: str, params: list) -> dict:
    v = conn.execute(f"SELECT id, criado_em FROM ficha_versao WHERE loja_id = %s AND {cond} ORDER BY id DESC LIMIT 1",
                     (LOJA_ID, *params)).fetchone()
    if not v:
        return {"versao_id": None, "desde": None, "linhas": []}
    linhas = conn.execute("SELECT l.item_id, i.nome AS item, i.unidade, i.classe, l.quantidade, l.perda_pct, l.fase FROM ficha_linha l "
                          "JOIN item i ON i.id = l.item_id WHERE l.versao_id = %s ORDER BY i.nome", (v["id"],)).fetchall()
    for r in linhas:
        r["quantidade"], r["perda_pct"] = fmt(r["quantidade"]).rstrip("0").rstrip("."), fmt(r["perda_pct"])
    return {"versao_id": v["id"], "desde": v["criado_em"], "linhas": linhas}


def _tem_ciclo(conn, origem: int, itens: list[int]) -> bool:
    """O preparo `origem` não pode, direta ou indiretamente, entrar na própria ficha."""
    visto, pilha = set(), list(itens)
    while pilha:
        atual = pilha.pop()
        if atual == origem:
            return True
        if atual in visto:
            continue
        visto.add(atual)
        v = conn.execute("SELECT id FROM ficha_versao WHERE item_id = %s ORDER BY id DESC LIMIT 1", (atual,)).fetchone()
        if v:
            pilha += [r["item_id"] for r in conn.execute("SELECT item_id FROM ficha_linha WHERE versao_id = %s", (v["id"],)).fetchall()]
    return False


def _ler(conn, tipo, dono_id, tamanho):
    cond, params, _, _ = _dono(conn, tipo, dono_id, tamanho)
    return _ficha_atual(conn, cond, params)


def _salvar(conn, sessao, tipo, dono_id, tamanho, d: FichaIn):
    cond, params, colunas, rotulo = _dono(conn, tipo, dono_id, tamanho)
    ids = [x.item_id for x in d.linhas]
    if ids:
        ativos = {r["id"] for r in conn.execute("SELECT id FROM item WHERE loja_id = %s AND ativo = true AND id = ANY(%s)", (LOJA_ID, ids)).fetchall()}
        if set(ids) - ativos:
            raise HTTPException(status_code=400, detail="Há item inexistente ou inativo na ficha.")
    if tipo == "preparo" and _tem_ciclo(conn, dono_id, ids):
        raise HTTPException(status_code=400, detail="Um preparo não pode conter a si mesmo, direta ou indiretamente.")
    perda_padrao = svc_parametros.vigentes(conn, LOJA_ID)["perda_padrao_pct"]["valor"] or "10"
    nomes = ", ".join(colunas)
    marcas = ", ".join(["%s"] * len(colunas))
    v = _grava(conn, f"INSERT INTO ficha_versao (loja_id, {nomes}, criado_em, criado_por) VALUES (%s, {marcas}, %s, %s) RETURNING id",
               (LOJA_ID, *colunas.values(), agora(), sessao["usuario_id"]))
    for x in d.linhas:
        _grava(conn, "INSERT INTO ficha_linha (versao_id, item_id, quantidade, perda_pct, fase) VALUES (%s,%s,%s,%s,%s) RETURNING id",
               (v["id"], x.item_id, x.quantidade, x.perda_pct if x.perda_pct is not None else perda_padrao, x.fase))
    auditar(conn, sessao, "salvar_ficha", "ficha", rotulo, depois={"versao_id": v["id"], "linhas": len(d.linhas)})
    conn.commit()
    return _ficha_atual(conn, cond, params)


@router.get("/fichas/produto/{pid}")
def ficha_produto(pid: int, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    return _ler(conn, "produto", pid, None)


@router.put("/fichas/produto/{pid}")
def salvar_ficha_produto(pid: int, d: FichaIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    return _salvar(conn, sessao, "produto", pid, None, d)


@router.get("/fichas/adicional/{aid}/{tamanho}")
def ficha_adicional(aid: int, tamanho: str, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    return _ler(conn, "adicional", aid, tamanho)


@router.put("/fichas/adicional/{aid}/{tamanho}")
def salvar_ficha_adicional(aid: int, tamanho: str, d: FichaIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    return _salvar(conn, sessao, "adicional", aid, tamanho, d)


@router.get("/fichas/preparo/{iid}")
def ficha_preparo(iid: int, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    return _ler(conn, "preparo", iid, None)


@router.put("/fichas/preparo/{iid}")
def salvar_ficha_preparo(iid: int, d: FichaIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    return _salvar(conn, sessao, "preparo", iid, None, d)


@router.get("/fichas/base/{tamanho}")
def ficha_base(tamanho: str, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    return _ler(conn, "base", None, tamanho)


@router.put("/fichas/base/{tamanho}")
def salvar_ficha_base(tamanho: str, d: FichaIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    return _salvar(conn, sessao, "base", None, tamanho, d)


# ---------------------------------------------------------------- etapas
_ETAPAS_PADRAO = (("Preparo da massa", "massa"), ("Massa aberta", "massa"), ("Montagem", "pizzaiolo"),
                  ("Forno", "automatica"), ("Acabamento", "acabamento"))


@router.get("/etapas")
def listar_etapas(ativo: Optional[bool] = None, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    sql, params = f"SELECT {_E} FROM etapa WHERE loja_id = %s", [LOJA_ID]
    if ativo is not None:
        sql, params = sql + " AND ativo = %s", params + [ativo]
    return conn.execute(sql + " ORDER BY id", params).fetchall()


@router.post("/etapas", status_code=201)
def criar_etapa(d: EtapaCreate, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    nova = _grava(conn, f"INSERT INTO etapa (loja_id, nome, funcao, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s) RETURNING {_E}",
                  (LOJA_ID, d.nome, d.funcao, agora(), sessao["usuario_id"]))
    auditar(conn, sessao, "criar", "etapa", nova["id"], depois=nova)
    conn.commit()
    return nova


@router.patch("/etapas/{eid}")
def alterar_etapa(eid: int, d: EtapaUpdate, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    antes = conn.execute(f"SELECT {_E} FROM etapa WHERE id = %s AND loja_id = %s", (eid, LOJA_ID)).fetchone()
    if not antes:
        raise HTTPException(status_code=404, detail="Etapa não encontrada.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    novo = _grava(conn, f"UPDATE etapa SET {sets} WHERE id = %s RETURNING {_E}", (*campos.values(), eid))
    auditar(conn, sessao, "alterar", "etapa", eid, antes={k: antes[k] for k in campos}, depois={k: novo[k] for k in campos})
    conn.commit()
    return novo


@router.post("/etapas/iniciar-padrao", status_code=201)
def iniciar_etapas_padrao(sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    """Cria as cinco etapas de Marlon e o modelo de pizza e calzone, só quando a loja ainda não tem etapa."""
    if conn.execute("SELECT 1 FROM etapa WHERE loja_id = %s LIMIT 1", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=409, detail="A loja já tem etapas cadastradas.")
    ids = [_grava(conn, "INSERT INTO etapa (loja_id, nome, funcao, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                  (LOJA_ID, n, f, agora(), sessao["usuario_id"]))["id"] for n, f in _ETAPAS_PADRAO]
    for tipo in ("pizza", "calzone"):
        for ordem, eid in enumerate(ids, 1):
            conn.execute("INSERT INTO etapa_modelo (tipo, etapa_id, ordem) VALUES (%s,%s,%s)", (tipo, eid, ordem))
    auditar(conn, sessao, "criar", "etapa", "padrao", depois={"etapas": len(ids)})
    conn.commit()
    return conn.execute(f"SELECT {_E} FROM etapa WHERE loja_id = %s ORDER BY id", (LOJA_ID,)).fetchall()


def _passos(conn, tabela_sql: str, chave):
    rows = conn.execute(f"SELECT x.etapa_id, e.nome, e.funcao, x.ordem, x.tempo_min FROM {tabela_sql} x "
                        "JOIN etapa e ON e.id = x.etapa_id ORDER BY x.ordem", chave).fetchall()
    for r in rows:
        r["tempo_min"] = None if r["tempo_min"] is None else fmt(r["tempo_min"])
    return rows


def _validar_etapas(conn, d: EtapasIn):
    ids = [x.etapa_id for x in d.etapas]
    if ids:
        ok = {r["id"] for r in conn.execute("SELECT id FROM etapa WHERE loja_id = %s AND ativo = true AND id = ANY(%s)", (LOJA_ID, ids)).fetchall()}
        if set(ids) - ok:
            raise HTTPException(status_code=400, detail="Há etapa inexistente ou inativa na lista.")


@router.get("/modelo-etapas/{tipo}")
def ler_modelo(tipo: str, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    if tipo not in TIPOS_PRODUTO:
        raise HTTPException(status_code=404, detail="Tipo de produto inválido.")
    return {"etapas": _passos(conn, "(SELECT m.* FROM etapa_modelo m JOIN etapa e ON e.id = m.etapa_id WHERE m.tipo = %s AND e.loja_id = %s)", (tipo, LOJA_ID))}


@router.put("/modelo-etapas/{tipo}")
def salvar_modelo(tipo: str, d: EtapasIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    if tipo not in TIPOS_PRODUTO:
        raise HTTPException(status_code=404, detail="Tipo de produto inválido.")
    _validar_etapas(conn, d)
    conn.execute("DELETE FROM etapa_modelo WHERE tipo = %s AND etapa_id IN (SELECT id FROM etapa WHERE loja_id = %s)", (tipo, LOJA_ID))
    for ordem, x in enumerate(d.etapas, 1):
        _grava(conn, "INSERT INTO etapa_modelo (tipo, etapa_id, ordem, tempo_min) VALUES (%s,%s,%s,%s) RETURNING tipo", (tipo, x.etapa_id, ordem, x.tempo_min))
    auditar(conn, sessao, "salvar_modelo", "etapa_modelo", tipo, depois={"etapas": [x.etapa_id for x in d.etapas]})
    conn.commit()
    return ler_modelo(tipo, sessao, conn)


def _produto_tipo(conn, pid: int) -> str:
    p = conn.execute("SELECT tipo FROM produto WHERE id = %s AND loja_id = %s", (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return p["tipo"]


@router.get("/produtos/{pid}/etapas")
def etapas_do_produto(pid: int, sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    tipo = _produto_tipo(conn, pid)
    proprias = conn.execute("SELECT 1 FROM produto_etapa WHERE produto_id = %s LIMIT 1", (pid,)).fetchone()
    if proprias:
        return {"personalizado": True, "etapas": _passos(conn, "(SELECT * FROM produto_etapa WHERE produto_id = %s)", (pid,))}
    return {"personalizado": False, **ler_modelo(tipo, sessao, conn)}


@router.put("/produtos/{pid}/etapas")
def salvar_etapas_do_produto(pid: int, d: EtapasIn, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    _produto_tipo(conn, pid)
    if not d.etapas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma etapa, ou volte ao modelo do tipo.")
    _validar_etapas(conn, d)
    conn.execute("DELETE FROM produto_etapa WHERE produto_id = %s", (pid,))
    for ordem, x in enumerate(d.etapas, 1):
        _grava(conn, "INSERT INTO produto_etapa (produto_id, etapa_id, ordem, tempo_min) VALUES (%s,%s,%s,%s) RETURNING produto_id", (pid, x.etapa_id, ordem, x.tempo_min))
    auditar(conn, sessao, "salvar_etapas", "produto", pid, depois={"etapas": [x.etapa_id for x in d.etapas]})
    conn.commit()
    return etapas_do_produto(pid, sessao, conn)


@router.delete("/produtos/{pid}/etapas")
def voltar_ao_modelo(pid: int, sessao=Depends(requer("ficha.editar")), conn=Depends(get_db)):
    _produto_tipo(conn, pid)
    conn.execute("DELETE FROM produto_etapa WHERE produto_id = %s", (pid,))
    auditar(conn, sessao, "voltar_ao_modelo", "produto", pid)
    conn.commit()
    return etapas_do_produto(pid, sessao, conn)


# ---------------------------------------------------------------- qualidade dos dados
@router.get("/fichas/qualidade")
def qualidade(sessao=Depends(requer("ficha.ver")), conn=Depends(get_db)):
    """O que falta preencher. Produto sem ficha aparece aqui, nunca como custo zero."""
    sem_ficha = conn.execute(
        "SELECT p.id, p.tipo, p.nome FROM produto p WHERE p.loja_id = %s AND p.ativo = true AND NOT EXISTS "
        "(SELECT 1 FROM ficha_versao v JOIN ficha_linha l ON l.versao_id = v.id WHERE v.produto_id = p.id AND v.id = "
        "(SELECT max(id) FROM ficha_versao WHERE produto_id = p.id)) ORDER BY p.tipo, p.nome", (LOJA_ID,)).fetchall()
    preparos = conn.execute(
        "SELECT i.id, i.nome FROM item i WHERE i.loja_id = %s AND i.ativo = true AND i.classe = 'preparo' AND NOT EXISTS "
        "(SELECT 1 FROM ficha_versao v JOIN ficha_linha l ON l.versao_id = v.id WHERE v.item_id = i.id AND v.id = "
        "(SELECT max(id) FROM ficha_versao WHERE item_id = i.id)) ORDER BY i.nome", (LOJA_ID,)).fetchall()
    bases = [t for t in _TAMANHOS if not _ficha_atual(conn, "tamanho = %s AND produto_id IS NULL AND adicional_id IS NULL AND item_id IS NULL", [t])["linhas"]]
    sem_etapas = conn.execute(
        "SELECT p.id, p.tipo, p.nome FROM produto p WHERE p.loja_id = %s AND p.ativo = true AND p.tipo IN ('pizza','calzone') "
        "AND NOT EXISTS (SELECT 1 FROM produto_etapa pe WHERE pe.produto_id = p.id) "
        "AND NOT EXISTS (SELECT 1 FROM etapa_modelo m WHERE m.tipo = p.tipo) ORDER BY p.tipo, p.nome", (LOJA_ID,)).fetchall()
    return {"produtos_sem_ficha": sem_ficha, "preparos_sem_ficha": preparos, "bases_sem_ficha": bases, "produtos_sem_etapas": sem_etapas}
