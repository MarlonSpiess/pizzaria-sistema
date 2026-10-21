"""Testes rodam SÓ contra um banco cujo nome termina em _teste, recriado a cada execução."""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

os.environ.setdefault("DB_PASS", os.getenv("TEST_DB_PASS", "teste"))
os.environ["DB_NAME"] = os.getenv("TEST_DB_NAME", "pizzaria_teste")
os.environ.setdefault("DB_HOST", os.getenv("TEST_DB_HOST", "localhost"))
os.environ.setdefault("DB_PORT", os.getenv("TEST_DB_PORT", "5432"))
os.environ.setdefault("DB_USER", os.getenv("TEST_DB_USER", "postgres"))
os.environ["LOGIN_MAX_FALHAS"] = "5"
os.environ["DOCS_ENABLED"] = "0"

if not os.environ["DB_NAME"].endswith("_teste"):
    raise SystemExit("Recusado: os testes só rodam em banco cujo nome termina em _teste.")

import psycopg  # noqa: E402
import psycopg.sql  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

BASE = dict(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]), user=os.environ["DB_USER"],
            password=os.environ["DB_PASS"])


@pytest.fixture(scope="session", autouse=True)
def banco():
    nome = os.environ["DB_NAME"]
    with psycopg.connect(dbname="postgres", autocommit=True, **BASE) as c:
        c.execute(psycopg.sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(psycopg.sql.Identifier(nome)))
        c.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(nome)))
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "aplicar_migrations_pg.py")], capture_output=True, text=True,
                       env=dict(os.environ))
    assert r.returncode == 0, r.stderr + r.stdout
    with psycopg.connect(dbname=nome, **BASE) as c:
        c.execute("INSERT INTO loja (id, nome) VALUES (1, 'Pizzaria Teste')")
    yield


@pytest.fixture(scope="session")
def client(banco):
    from api.main import app
    with TestClient(app) as c:
        yield c


_contador = [0]


def novo_login(prefixo="u"):
    _contador[0] += 1
    return f"{prefixo}{_contador[0]}"


def criar_usuario_direto(perfil="atendente", senha="senha-forte-1", deve_trocar=False, ativo=True):
    from api.security import hash_senha
    login = novo_login(perfil[:3])
    with psycopg.connect(dbname=os.environ["DB_NAME"], **BASE) as c:
        c.execute("INSERT INTO usuario (loja_id, usuario, nome, senha_hash, perfil, ativo, deve_trocar_senha, criado_em) "
                  "VALUES (1, %s, %s, %s, %s, %s, %s, now())", (login, f"Nome {login}", hash_senha(senha), perfil, ativo, deve_trocar))
    return login, senha


def entrar(client, perfil="atendente", **kw):
    login, senha = criar_usuario_direto(perfil, **kw)
    r = client.post("/api/auth/login", json={"usuario": login, "senha": senha})
    assert r.status_code == 200, r.text
    return login, {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def admin(client):
    return entrar(client, "administrador")


@pytest.fixture
def conn_teste():
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        yield c
