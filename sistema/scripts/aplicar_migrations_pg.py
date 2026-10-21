"""
scripts/aplicar_migrations_pg.py
Aplica os arquivos migrations_pg/NNN_*.sql em ordem, uma única vez cada,
registrando o que já foi aplicado em `schema_version` (com checksum).
pg_try_advisory_lock serializa execuções concorrentes; cada migration roda em
uma transação (falha = rollback total).

Regras para escrever migration:
- Nunca conter BEGIN/COMMIT/ROLLBACK nem comandos que não rodam em transação
  (CREATE INDEX CONCURRENTLY, VACUUM): o script rejeita.
- Nunca editar uma migration já aplicada (checksum): criar uma nova.
- Idempotente (IF NOT EXISTS) e curta.

Uso:
    python scripts/aplicar_migrations_pg.py
    python scripts/aplicar_migrations_pg.py --dry-run     (somente leitura)
Variável opcional MIGRATIONS_DIR aponta para outra pasta (usada nos testes).
"""
import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402

from api.config import DB_CONFIG  # noqa: E402

MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR") or Path(__file__).resolve().parent.parent / "migrations_pg")
LOCK_ID = 727101
LOCK_ESPERA_S = 60
_NOME_MIGRATION = re.compile(r"^(\d+)_.+\.sql$")
# Remove comentários, literais entre aspas e corpos $$...$$ (funções plpgsql têm BEGIN/END legítimos)
# antes de procurar comandos de controle de transação.
_IGNORAVEL = re.compile(r"--[^\n]*|/\*.*?\*/|\$([A-Za-z_]*)\$.*?\$\1\$|'(?:[^']|'')*'|\"[^\"]*\"", re.DOTALL)
_PROIBIDO = re.compile(r"(^|;)\s*(BEGIN|COMMIT|END|ROLLBACK|ABORT|START\s+TRANSACTION|VACUUM)\b|CONCURRENTLY",
                       re.IGNORECASE | re.MULTILINE)
# Erros permanentes: repetir a conexão não ajuda.
_SQLSTATE_SEM_RETRY = {"28P01", "28000", "3D000"}


def erro(msg: str):
    print(f"[erro] {msg}", file=sys.stderr)
    sys.exit(1)


def listar_migrations() -> list[tuple[int, Path]]:
    achadas = []
    for caminho in MIGRATIONS_DIR.glob("*.sql"):
        m = _NOME_MIGRATION.match(caminho.name)
        if m:
            achadas.append((int(m.group(1)), caminho))
    achadas.sort(key=lambda item: item[0])
    numeros = [n for n, _ in achadas]
    duplicados = {n for n in numeros if numeros.count(n) > 1}
    if duplicados:
        erro(f"numeração duplicada em migrations: {sorted(duplicados)}")
    return achadas


def ler_sql(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8-sig")


def conectar():
    # MIGRATE_DB_USER/MIGRATE_DB_PASS: papel dono do schema (DDL). O app roda com um papel restrito (DB_USER/DB_PASS).
    return psycopg.connect(
        host=DB_CONFIG["host"], port=DB_CONFIG["port"], dbname=DB_CONFIG["dbname"],
        user=os.getenv("MIGRATE_DB_USER") or DB_CONFIG["user"],
        password=os.getenv("MIGRATE_DB_PASS") or DB_CONFIG["password"], connect_timeout=5,
    )


def conectar_com_retry(tentativas: int = 3):
    for n in range(1, tentativas + 1):
        try:
            return conectar()
        except psycopg.OperationalError as e:
            if n == tentativas or getattr(e, "sqlstate", None) in _SQLSTATE_SEM_RETRY:
                raise
            time.sleep(2 * n)


def checksum(caminho: Path) -> str:
    """SHA-256 do conteúdo com fim de linha normalizado (CRLF/LF não muda o hash)."""
    texto = caminho.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(texto).hexdigest()


def preparar_controle(conn):
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "versao INT PRIMARY KEY, aplicada_em TIMESTAMPTZ DEFAULT now(), checksum TEXT)"
        )
    conn.commit()


def adquirir_lock(conn):
    limite = time.time() + LOCK_ESPERA_S
    while True:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            if cur.fetchone()[0]:
                return
        if time.time() > limite:
            erro(f"outra instância do migrator segura o lock há mais de {LOCK_ESPERA_S}s.")
        print("[aguardando] outra instância aplicando migrations...")
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria aplicado, sem escrever no banco")
    args = parser.parse_args()

    migrations = listar_migrations()
    if not migrations:
        print(f"Nenhuma migration encontrada em {MIGRATIONS_DIR}.")
        sys.exit(0)
    for _, caminho in migrations:
        sql = ler_sql(caminho)
        if not sql.strip():
            erro(f"{caminho.name} está vazia.")
        if _PROIBIDO.search(_IGNORAVEL.sub(" ", sql)):
            erro(f"{caminho.name} contém BEGIN/COMMIT/ROLLBACK/ABORT/START TRANSACTION/VACUUM/CONCURRENTLY (proibido: quebra a atomicidade).")

    try:
        conn = conectar_com_retry()
    except psycopg.OperationalError as e:
        erro(f"não foi possível conectar ao banco '{DB_CONFIG['dbname']}': {str(e).strip().splitlines()[-1]}")

    try:
        if not args.dry_run:
            adquirir_lock(conn)
            preparar_controle(conn)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('schema_version')")
                existe = cur.fetchone()[0] is not None
                aplicadas = {}
                if existe:
                    cur.execute("SELECT versao, checksum FROM schema_version")
                    aplicadas = {v: c for v, c in cur.fetchall()}
            conn.commit()

            arquivos = {v: p for v, p in migrations}
            ausentes = sorted(set(aplicadas) - set(arquivos))
            if ausentes:
                erro(f"migrations já aplicadas sem arquivo no disco: {ausentes}.")
            for versao, esperado in aplicadas.items():
                if esperado != checksum(arquivos[versao]):
                    erro(f"{arquivos[versao].name} foi alterada depois de aplicada (checksum diferente). "
                         "Crie uma nova migration em vez de editar a antiga.")

            pendentes = [(v, p) for v, p in migrations if v not in aplicadas]
            ultima = max(aplicadas, default=0)
            fora_de_ordem = [p.name for v, p in pendentes if v < ultima]
            if fora_de_ordem:
                erro(f"migration com número menor que a última aplicada ({ultima}): {fora_de_ordem}.")
            if not pendentes:
                print(f"[ok] banco já em dia (versão {ultima}).")
                return
            for versao, caminho in pendentes:
                if args.dry_run:
                    print(f"[dry-run] aplicaria {caminho.name}")
                    continue
                print(f"[aplicando] {caminho.name} ...")
                try:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute("SET LOCAL lock_timeout = '5s'")
                            cur.execute(ler_sql(caminho))
                            cur.execute("INSERT INTO schema_version (versao, checksum) VALUES (%s, %s)",
                                        (versao, checksum(caminho)))
                except psycopg.Error as e:
                    erro(f"falha em {caminho.name} (rollback total): {str(e).strip().splitlines()[0]}")
                print(f"[ok] {caminho.name} aplicada.")
        finally:
            if not args.dry_run:
                try:
                    conn.rollback()
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
                except psycopg.Error:
                    pass  # conexão já caída: o lock de sessão some junto
    except psycopg.errors.InsufficientPrivilege as e:
        erro("o papel do banco não tem permissão para criar/alterar tabelas. Rode o migrator com o dono do schema "
             f"(MIGRATE_DB_USER/MIGRATE_DB_PASS): {str(e).strip().splitlines()[0]}")
    except psycopg.Error as e:
        erro(f"erro de banco: {str(e).strip().splitlines()[0]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
