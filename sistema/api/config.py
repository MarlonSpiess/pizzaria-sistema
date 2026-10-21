"""Configuração via variáveis de ambiente. Nenhum segredo no código."""
import os


def _obter_db_pass() -> str:
    senha = os.getenv("DB_PASS")
    if not senha:
        raise RuntimeError("Variável de ambiente DB_PASS não definida. Não há senha padrão no código; "
                           "defina DB_PASS (set_env.bat, copiado de set_env.bat.example) antes de iniciar.")
    return senha


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "pizzaria"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": _obter_db_pass(),
}

# Uma loja por banco; o identificador entra em todo registro.
LOJA_ID = int(os.getenv("LOJA_ID", "1"))
TZ_BRASIL = "America/Sao_Paulo"

SESSION_TTL_HOURS = float(os.getenv("SESSION_TTL_HOURS", "12"))
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_MIN = float(os.getenv("LOGIN_JANELA_MIN", "15"))
SENHA_MIN = 8

# Cabeçalho com o IP real do cliente, só atrás de proxy confiável. Vazio = IP do socket.
CLIENT_IP_HEADER = os.getenv("CLIENT_IP_HEADER", "").strip().lower()
DOCS_ENABLED = os.getenv("DOCS_ENABLED", "0") == "1"

POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
POOL_TIMEOUT_S = float(os.getenv("DB_POOL_TIMEOUT", "5"))
STATEMENT_TIMEOUT_S = int(os.getenv("DB_STATEMENT_TIMEOUT", "30"))
LOCK_TIMEOUT_S = int(os.getenv("DB_LOCK_TIMEOUT", "10"))

# Backup (scripts/backup.py)
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
# Cópias extras, separadas por ";" (ex.: pasta sincronizada do Google Drive e pasta do computador de Marlon).
BACKUP_DIRS_EXTRA = [d for d in os.getenv("BACKUP_DIRS_EXTRA", "").split(";") if d.strip()]
BACKUP_RETENCAO = int(os.getenv("BACKUP_RETENCAO", "30"))
BACKUP_ATRASO_HORAS = float(os.getenv("BACKUP_ATRASO_HORAS", "24"))
PG_DUMP = os.getenv("PG_DUMP_PATH", "pg_dump")
