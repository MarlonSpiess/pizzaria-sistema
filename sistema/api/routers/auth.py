from fastapi import APIRouter, Depends, HTTPException, Request

from api.database import agora, auditar, get_db
from api.schemas import LoginIn, TrocarSenhaIn
from api.security import (SENHA_DUMMY_HASH, criar_sessao, exigir_login_liberado, get_current_session, hash_senha,
                          invalidar_sessao, invalidar_sessoes_usuario, ip_cliente, limpar_falhas_login,
                          registrar_falha_login, verificar_senha)

router = APIRouter(prefix="/auth", tags=["auth"])

_CRED_INVALIDAS = "Usuário ou senha inválidos."


@router.post("/login")
def login(dados: LoginIn, request: Request, conn=Depends(get_db)):
    ip = ip_cliente(request)
    exigir_login_liberado(conn, ip, dados.usuario)
    u = conn.execute("SELECT id, usuario, nome, perfil, senha_hash, ativo, deve_trocar_senha FROM usuario WHERE usuario = %s",
                     (dados.usuario,)).fetchone()
    # Sempre roda o bcrypt (hash dummy se o usuário não existe) e responde igual para todo tipo de falha.
    ok = verificar_senha(dados.senha, u["senha_hash"] if u else SENHA_DUMMY_HASH)
    if not u or not ok or not u["ativo"]:
        registrar_falha_login(conn, ip, dados.usuario)
        raise HTTPException(status_code=401, detail=_CRED_INVALIDAS)
    limpar_falhas_login(conn, ip, dados.usuario)
    token = criar_sessao(conn, u["id"])
    return {"token": token, "usuario": u["usuario"], "nome": u["nome"], "perfil": u["perfil"],
            "deve_trocar_senha": u["deve_trocar_senha"]}


@router.post("/logout")
def logout(sessao=Depends(get_current_session), conn=Depends(get_db)):
    invalidar_sessao(conn, sessao["token"])
    return {"ok": True}


@router.get("/me")
def me(sessao=Depends(get_current_session)):
    return {"usuario": sessao["usuario"], "nome": sessao["nome"], "perfil": sessao["perfil"],
            "deve_trocar_senha": sessao["deve_trocar_senha"]}


@router.post("/trocar-senha")
def trocar_senha(dados: TrocarSenhaIn, request: Request, sessao=Depends(get_current_session), conn=Depends(get_db)):
    ip = ip_cliente(request)
    exigir_login_liberado(conn, ip, sessao["usuario"])  # mesmo bloqueio do login
    atual = conn.execute("SELECT senha_hash FROM usuario WHERE id = %s", (sessao["usuario_id"],)).fetchone()
    if not verificar_senha(dados.senha_atual, atual["senha_hash"]):
        registrar_falha_login(conn, ip, sessao["usuario"])
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")
    if dados.senha_nova == dados.senha_atual:
        conn.rollback()
        raise HTTPException(status_code=400, detail="A senha nova deve ser diferente da atual.")
    conn.execute("UPDATE usuario SET senha_hash = %s, deve_trocar_senha = false WHERE id = %s",
                 (hash_senha(dados.senha_nova), sessao["usuario_id"]))
    invalidar_sessoes_usuario(conn, sessao["usuario_id"], exceto_token=sessao["token"])
    auditar(conn, sessao, "trocar_senha", "usuario", sessao["usuario_id"])
    conn.commit()
    limpar_falhas_login(conn, ip, sessao["usuario"])
    return {"ok": True}
