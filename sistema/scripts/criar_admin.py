"""
Cria (ou redefine a senha de) um administrador e garante o registro da loja.
A senha NUNCA vai na linha de comando: vem da variável PIZZARIA_ADMIN_SENHA ou é pedida sem eco.

Uso:
    python scripts/criar_admin.py --usuario admin --nome "Administrador" [--loja-nome "Pizzaria X"]
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError  # noqa: E402

from api.config import LOJA_ID  # noqa: E402
from api.database import agora, auditar, get_connection  # noqa: E402
from api.schemas import UsuarioCreate  # noqa: E402
from api.security import hash_senha  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--usuario", required=True)
    ap.add_argument("--nome", default="Administrador")
    ap.add_argument("--loja-nome", default="Pizzaria")
    ap.add_argument("--promover", action="store_true", help="Permite redefinir a senha de um usuário que já existe")
    args = ap.parse_args()
    senha = os.getenv("PIZZARIA_ADMIN_SENHA") or getpass.getpass("Senha do administrador: ")
    try:
        dados = UsuarioCreate(nome=args.nome, usuario=args.usuario, senha=senha, perfil="administrador")
    except ValidationError as e:  # nunca imprimir o valor digitado
        for erro in e.errors(include_input=False, include_url=False):
            print(f"[erro] {'.'.join(str(x) for x in erro['loc'])}: {erro['msg']}", file=sys.stderr)
        sys.exit(1)
    conn = get_connection()
    try:
        conn.execute("INSERT INTO loja (id, nome) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (LOJA_ID, args.loja_nome))
        existe = conn.execute("SELECT id FROM usuario WHERE loja_id = %s AND usuario = %s", (LOJA_ID, dados.usuario)).fetchone()
        if existe and not args.promover:
            print(f"[erro] o usuário '{dados.usuario}' já existe; use --promover para redefinir a senha.", file=sys.stderr)
            sys.exit(1)
        if existe:
            conn.execute("UPDATE usuario SET senha_hash = %s, perfil = 'administrador', ativo = true, deve_trocar_senha = true "
                         "WHERE id = %s", (hash_senha(dados.senha), existe["id"]))
            conn.execute("DELETE FROM sessao WHERE usuario_id = %s", (existe["id"],))
            auditar(conn, None, "redefinir_senha_admin", "usuario", existe["id"])
            print(f"[ok] senha de '{dados.usuario}' redefinida (administrador, ativo; trocará a senha no próximo acesso).")
        else:
            novo = conn.execute("INSERT INTO usuario (loja_id, usuario, nome, senha_hash, perfil, deve_trocar_senha, criado_em) "
                                "VALUES (%s, %s, %s, %s, 'administrador', true, %s) RETURNING id",
                                (LOJA_ID, dados.usuario, dados.nome, hash_senha(dados.senha), agora())).fetchone()
            auditar(conn, None, "criar_admin", "usuario", novo["id"])
            print(f"[ok] administrador '{dados.usuario}' criado (trocará a senha no primeiro acesso).")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
