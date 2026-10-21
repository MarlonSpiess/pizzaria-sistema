import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, run, traduzir_erro
from api.schemas import RedefinirSenhaIn, UsuarioCreate, UsuarioUpdate
from api.security import hash_senha, invalidar_sessoes_usuario, requer

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

_COLS = "id, usuario, nome, perfil, ativo, deve_trocar_senha, criado_em"


def _so_administrador_mexe_em_administrador(sessao, perfil_alvo: str):
    if perfil_alvo == "administrador" and sessao["perfil"] != "administrador":
        raise HTTPException(status_code=403, detail="Só o administrador cria ou altera administradores.")


def _obter(conn, uid: int) -> dict:
    u = conn.execute(f"SELECT {_COLS} FROM usuario WHERE id = %s AND loja_id = %s", (uid, LOJA_ID)).fetchone()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return u


@router.get("")
def listar(sessao=Depends(requer("usuarios.gerir")), conn=Depends(get_db)):
    return run(conn, f"SELECT {_COLS} FROM usuario WHERE loja_id = %s ORDER BY nome", (LOJA_ID,), "all")


@router.post("", status_code=201)
def criar(dados: UsuarioCreate, sessao=Depends(requer("usuarios.gerir")), conn=Depends(get_db)):
    _so_administrador_mexe_em_administrador(sessao, dados.perfil)
    try:
        novo = conn.execute(
            f"INSERT INTO usuario (loja_id, usuario, nome, senha_hash, perfil, deve_trocar_senha, criado_em, criado_por) "
            f"VALUES (%s, %s, %s, %s, %s, true, %s, %s) RETURNING {_COLS}",
            (LOJA_ID, dados.usuario, dados.nome, hash_senha(dados.senha), dados.perfil, agora(),
             sessao["usuario_id"])).fetchone()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    auditar(conn, sessao, "criar", "usuario", novo["id"], depois={"usuario": novo["usuario"], "perfil": novo["perfil"]})
    conn.commit()
    return novo


@router.patch("/{uid}")
def alterar(uid: int, dados: UsuarioUpdate, sessao=Depends(requer("usuarios.gerir")), conn=Depends(get_db)):
    atual = _obter(conn, uid)
    campos = dados.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    _so_administrador_mexe_em_administrador(sessao, atual["perfil"])
    if "perfil" in campos:
        _so_administrador_mexe_em_administrador(sessao, campos["perfil"])
    if uid == sessao["usuario_id"] and (campos.get("ativo") is False or ("perfil" in campos and campos["perfil"] != atual["perfil"])):
        raise HTTPException(status_code=400, detail="Você não pode desativar nem trocar o perfil do seu próprio usuário.")
    if atual["perfil"] == "administrador" and (campos.get("ativo") is False or campos.get("perfil", "administrador") != "administrador"):
        restantes = conn.execute("SELECT count(*) AS n FROM usuario WHERE loja_id = %s AND perfil = 'administrador' "
                                 "AND ativo AND id != %s", (LOJA_ID, uid)).fetchone()["n"]
        if restantes == 0:
            conn.rollback()
            raise HTTPException(status_code=400, detail="A loja precisa de pelo menos um administrador ativo.")
    # Nomes de coluna vêm só das chaves do schema (nome, perfil, ativo), nunca do usuário.
    sets = ", ".join(f"{c} = %s" for c in campos)
    conn.execute(f"UPDATE usuario SET {sets} WHERE id = %s", (*campos.values(), uid))
    if campos.get("ativo") is False or ("perfil" in campos and campos["perfil"] != atual["perfil"]):
        invalidar_sessoes_usuario(conn, uid)
    novo = _obter(conn, uid)
    auditar(conn, sessao, "alterar", "usuario", uid,
            antes={k: atual[k] for k in campos}, depois={k: novo[k] for k in campos})
    conn.commit()
    return novo


@router.post("/{uid}/redefinir-senha")
def redefinir_senha(uid: int, dados: RedefinirSenhaIn, sessao=Depends(requer("usuarios.gerir")), conn=Depends(get_db)):
    atual = _obter(conn, uid)
    _so_administrador_mexe_em_administrador(sessao, atual["perfil"])
    conn.execute("UPDATE usuario SET senha_hash = %s, deve_trocar_senha = true WHERE id = %s",
                 (hash_senha(dados.senha_nova), uid))
    invalidar_sessoes_usuario(conn, uid)
    auditar(conn, sessao, "redefinir_senha", "usuario", uid)
    conn.commit()
    return {"ok": True}
