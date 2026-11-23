#!/usr/bin/env bash
# Recria o banco de DEMONSTRAÇÃO (nome terminado em _demo) e o popula com dados fictícios.
# Uso: SISTEMA=/caminho/para/sistema DB_PASS=... DEMO_SENHA=... ./preparar_demo.sh
# Só Linux. O servidor da demonstração é (re)subido na porta 8080; se outro servidor ocupar a porta, o script recusa.
set -euo pipefail
: "${SISTEMA:?Defina SISTEMA com a pasta sistema/ do repositório}"
: "${DB_PASS:?Defina DB_PASS}"
: "${DEMO_SENHA:?Defina DEMO_SENHA}"
export DB_NAME="${DB_NAME:-pizzaria_demo}" DB_USER="${DB_USER:-postgres}" DB_HOST="${DB_HOST:-localhost}" TZ=America/Sao_Paulo
# Só numa máquina de desenvolvimento com PostgreSQL próprio: nunca no PC da loja (a senha pedida é a do postgres local).
case "$DB_HOST" in localhost|127.0.0.1) ;; *) echo "Recusado: só PostgreSQL local" >&2; exit 1;; esac
[[ "$DB_NAME" =~ ^[a-z0-9_]+_demo$ ]] || { echo "Recusado: o banco precisa ser só letras minúsculas, números e _, terminando em _demo" >&2; exit 1; }
AQUI="$(cd "$(dirname "$0")" && pwd)"
pkill -f "uvicorn api.main:app --host 127.0.0.1 --port 8080" || true
sleep 1
# Nunca semear num servidor que já estava na porta (poderia ser o da loja, com o banco real).
if curl -s -o /dev/null http://127.0.0.1:8080/; then echo "Recusado: a porta 8080 já está em uso por outro servidor" >&2; exit 1; fi
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d postgres -qc "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE)" -c "CREATE DATABASE $DB_NAME"
cd "$SISTEMA"
python scripts/aplicar_migrations_pg.py > /dev/null
PIZZARIA_ADMIN_SENHA="$DEMO_SENHA" python scripts/criar_admin.py --usuario admin --nome "Ana Demonstração" --loja-nome "Pizzaria Demonstração"
nohup python -m uvicorn api.main:app --host 127.0.0.1 --port 8080 > /tmp/uvicorn_demo.log 2>&1 &
PID=$!
ok=0
for _ in $(seq 40); do curl -sf http://127.0.0.1:8080/ > /dev/null && { ok=1; break; }; sleep 0.5; done
kill -0 "$PID" 2>/dev/null && [ "$ok" = 1 ] || { echo "O servidor da demonstração não subiu (veja /tmp/uvicorn_demo.log)" >&2; exit 1; }
PYTHONPATH="$SISTEMA" python "$AQUI/semear_demo.py"
