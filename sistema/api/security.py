"""
Autenticação por sessão em PostgreSQL, bcrypt e permissões por perfil (nega o que não está liberado).
Sessões e bloqueio de login ficam em tabelas, não na memória do processo. O token é guardado como SHA-256.
"""
import hashlib
import secrets
from typing import Optional

import bcrypt
from fastapi import Depends, Header, HTTPException, Request

from api.config import CLIENT_IP_HEADER, LOGIN_JANELA_MIN, LOGIN_MAX_FALHAS, SESSION_TTL_HOURS
from api.database import get_db

PERFIS = ("administrador", "proprietario", "gerente", "subgerente", "atendente", "massa", "pizzaiolo", "acabamento")

# Permissões por perfil. Perfil ausente ou permissão ausente = negado.
# administrador e proprietário têm tudo; as demais permissões entram nas fatias seguintes.
_TODAS = {"usuarios.gerir", "parametros.ver", "parametros.editar", "auditoria.ver", "sistema.backup.ver", "sistema.backup.rodar",
          "cardapio.ver", "cardapio.editar", "clientes.ver", "clientes.editar", "entregadores.ver", "entregadores.editar",
          "ficha.ver", "ficha.editar", "vendas.ver", "vendas.criar", "vendas.gerir",
          "producao.ver", "producao.massa", "producao.montagem", "producao.forno", "producao.acabamento", "producao.perda",
          "producao.refazer", "producao.gerir"}
_GERENCIA = {"parametros.ver", "auditoria.ver", "sistema.backup.ver", "sistema.backup.rodar", "cardapio.ver", "cardapio.editar",
             "clientes.ver", "clientes.editar", "entregadores.ver", "entregadores.editar", "ficha.ver", "ficha.editar",
             "vendas.ver", "vendas.criar", "vendas.gerir",
             "producao.ver", "producao.massa", "producao.montagem", "producao.forno", "producao.acabamento", "producao.perda",
             "producao.refazer", "producao.gerir"}
PERMISSOES = {
    "administrador": _TODAS,
    "proprietario": _TODAS,
    "gerente": _GERENCIA,
    # Subgerente: permissões do gerente, exceto aprovar diferença de caixa (decisão de 19/10/2026; entra na fatia 1E).
    "subgerente": _GERENCIA,
    # Atendente consulta o cardápio e os entregadores e cadastra cliente na primeira compra.
    "atendente": {"cardapio.ver", "clientes.ver", "clientes.editar", "entregadores.ver",
                  "vendas.ver", "vendas.criar", "producao.ver"},
    # Funções de produção: cada tablet só enxerga e faz o que é da sua função (login pessoal).
    "massa": {"producao.ver", "producao.massa", "producao.perda"},
    "pizzaiolo": {"producao.ver", "producao.montagem", "producao.forno", "producao.perda"},
    "acabamento": {"producao.ver", "producao.forno", "producao.acabamento", "producao.perda", "producao.refazer"},
}


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# Hash de custo real: o caminho de usuário inexistente gasta o mesmo tempo de bcrypt que o de sucesso.
SENHA_DUMMY_HASH = hash_senha(secrets.token_urlsafe(32))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ip_cliente(request: Request) -> str:
    if CLIENT_IP_HEADER:
        # Último valor: o que o proxy confiável acrescentou. O primeiro pode ser forjado pelo cliente.
        valor = request.headers.get(CLIENT_IP_HEADER, "").split(",")[-1].strip()
        if valor:
            return valor
    return request.client.host if request.client else "?"


def _chave_login(ip: str, usuario: str) -> str:
    return f"{ip}|{usuario.strip().lower()}".replace("\x00", "\\0")


_MSG_429 = "Muitas tentativas de login. Aguarde alguns minutos e tente novamente."


def exigir_login_liberado(conn, ip: str, usuario: str) -> None:
    chave = _chave_login(ip, usuario)
    # Lock de transação por chave: tentativa concorrente na mesma chave recebe 429 em vez de furar o limite.
    ok = conn.execute("SELECT pg_try_advisory_xact_lock(1, hashtext(%s)) AS ok", (chave,)).fetchone()["ok"]
    if not ok:
        conn.rollback()
        raise HTTPException(status_code=429, detail=_MSG_429)
    n = conn.execute("SELECT count(*) AS n FROM login_falha WHERE chave = %s "
                     "AND tentativa_em > now() - (%s * interval '1 minute')", (chave, LOGIN_JANELA_MIN)).fetchone()["n"]
    if n >= LOGIN_MAX_FALHAS:
        conn.rollback()
        raise HTTPException(status_code=429, detail=_MSG_429)


def registrar_falha_login(conn, ip: str, usuario: str) -> None:
    conn.execute("DELETE FROM login_falha WHERE tentativa_em < now() - interval '1 day'")
    conn.execute("INSERT INTO login_falha (chave) VALUES (%s)", (_chave_login(ip, usuario),))
    conn.commit()


def limpar_falhas_login(conn, ip: str, usuario: str) -> None:
    conn.execute("DELETE FROM login_falha WHERE chave = %s", (_chave_login(ip, usuario),))
    conn.commit()


def criar_sessao(conn, usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("DELETE FROM sessao WHERE expira_em < now()")
    conn.execute("INSERT INTO sessao (token, usuario_id, expira_em) VALUES (%s, %s, now() + (%s * interval '1 hour'))",
                 (_hash_token(token), usuario_id, SESSION_TTL_HOURS))
    conn.commit()
    return token


def invalidar_sessao(conn, token: str) -> None:
    conn.execute("DELETE FROM sessao WHERE token = %s", (_hash_token(token),))
    conn.commit()


def invalidar_sessoes_usuario(conn, usuario_id: int, exceto_token: Optional[str] = None) -> None:
    """Não comita: quem chama comita junto com a alteração que motivou o encerramento."""
    if exceto_token:
        conn.execute("DELETE FROM sessao WHERE usuario_id = %s AND token != %s", (usuario_id, _hash_token(exceto_token)))
    else:
        conn.execute("DELETE FROM sessao WHERE usuario_id = %s", (usuario_id,))


def _extrair_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação ausente ou inválido")
    return authorization.split(" ", 1)[1].strip()


def get_current_session(authorization: Optional[str] = Header(default=None), conn=Depends(get_db)) -> dict:
    """Sessão válida + usuário revalidado no mesmo SELECT: usuário desativado perde a sessão na hora
    e o perfil devolvido é sempre o atual do cadastro."""
    token = _extrair_token(authorization)
    row = conn.execute(
        """SELECT s.usuario_id, u.usuario, u.nome, u.perfil, u.ativo, u.deve_trocar_senha, (s.expira_em > now()) AS valida
           FROM sessao s JOIN usuario u ON u.id = s.usuario_id WHERE s.token = %s""",
        (_hash_token(token),)).fetchone()
    if not row or not row["ativo"] or not row["valida"]:
        if row:
            invalidar_sessao(conn, token)
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    row["token"] = token
    return row


def requer(permissao: str):
    """Dependency: exige a permissão no perfil ATUAL; bloqueia quem ainda deve trocar a senha."""
    def _guard(sessao: dict = Depends(get_current_session)) -> dict:
        if sessao["deve_trocar_senha"]:
            raise HTTPException(status_code=403, detail="Troque a senha antes de continuar.")
        if permissao not in PERMISSOES.get(sessao["perfil"], set()):
            raise HTTPException(status_code=403, detail="Perfil insuficiente para esta operação")
        return sessao
    return _guard
