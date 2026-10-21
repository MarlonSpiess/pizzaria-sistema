"""
Faz o backup do banco agora (pg_dump), copia para as pastas extras (BACKUP_DIRS_EXTRA) e registra o resultado.
Uso: python scripts/backup.py
Saída com código 0 se o dump foi feito; 2 se houve falha de dump; 3 se o dump foi feito mas alguma cópia falhou.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.database import get_connection  # noqa: E402
from api.services.backup import fazer_backup  # noqa: E402


def main():
    conn = get_connection()
    try:
        r = fazer_backup(conn, "script")
    finally:
        conn.close()
    if not r["sucesso"]:
        print(f"[erro] {r['detalhe']}", file=sys.stderr)
        sys.exit(2)
    print(f"[ok] {r['arquivo']} ({r['tamanho_bytes']} bytes), cópias extras: {r['copias_ok']} ok, {r['copias_falha']} com falha.")
    if r["copias_falha"]:
        print(f"[aviso] {r['detalhe']}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
