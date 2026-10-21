"""
Teste de restauração: restaura um arquivo de backup em um banco NOVO (nunca no banco em uso) para conferir
que o backup serve. Uso: python scripts/restaurar_em_teste.py backups/pizzaria_..._.dump pizzaria_restauracao_teste
O banco de destino é criado; se já existir, o script para.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402
import psycopg.sql  # noqa: E402

from api.config import DB_CONFIG, PG_DUMP  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    arquivo, destino = sys.argv[1], sys.argv[2]
    if destino == DB_CONFIG["dbname"]:
        print("[erro] o destino não pode ser o banco em uso.", file=sys.stderr)
        sys.exit(1)
    base = dict(host=DB_CONFIG["host"], port=DB_CONFIG["port"], user=DB_CONFIG["user"], password=DB_CONFIG["password"])
    with psycopg.connect(dbname="postgres", autocommit=True, **base) as c:
        if c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (destino,)).fetchone():
            print(f"[erro] o banco '{destino}' já existe; escolha outro nome.", file=sys.stderr)
            sys.exit(1)
        c.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(destino)))
    pg_restore = str(Path(PG_DUMP).with_name("pg_restore" + Path(PG_DUMP).suffix)) if os.sep in PG_DUMP else "pg_restore"
    r = subprocess.run([pg_restore, "-h", str(base["host"]), "-p", str(base["port"]), "-U", base["user"], "-d", destino,
                        "--no-owner", arquivo], env=dict(os.environ, PGPASSWORD=base["password"]), capture_output=True, text=True)
    if r.returncode != 0:
        print("[erro] pg_restore: " + (r.stderr.strip().splitlines() or ["sem detalhe"])[-1], file=sys.stderr)
        sys.exit(2)
    with psycopg.connect(dbname=destino, **base) as c:
        n = c.execute("SELECT count(*) FROM usuario").fetchone()[0]
    print(f"[ok] restaurado em '{destino}': {n} usuário(s).")


if __name__ == "__main__":
    main()
