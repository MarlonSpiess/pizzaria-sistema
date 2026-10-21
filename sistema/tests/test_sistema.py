import os
import subprocess
import sys
from pathlib import Path

import psycopg

from tests.conftest import BASE, RAIZ, entrar


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_cabecalhos_de_seguranca_e_frontend(client):
    r = client.get("/")
    assert r.status_code == 200 and "app.js" in r.text
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "script-src 'self'" in r.headers["content-security-policy"] and "unsafe-inline" not in r.headers["content-security-policy"]
    assert client.get("/static/app.js").status_code == 200


def test_rota_de_api_inexistente_nao_cai_no_frontend(client):
    r = client.get("/api/nao-existe")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


def test_docs_desligados(client):
    assert client.get("/docs").status_code == 404 and client.get("/openapi.json").status_code == 404


def test_html_estatico_sem_script_inline(client):
    html = client.get("/").text
    assert "<script>" not in html and "onclick=" not in html


def test_frontend_nao_usa_innerhtml():
    js = (RAIZ / "frontend" / "static" / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "document.write" not in js and "eval(" not in js


def test_backup_e_restauracao(client, tmp_path, monkeypatch):
    import api.config as cfg
    import api.services.backup as bk
    destino, extra1, extra2 = tmp_path / "bk", tmp_path / "drive", tmp_path / "pc"
    monkeypatch.setattr(bk, "BACKUP_DIR", str(destino))
    monkeypatch.setattr(bk, "BACKUP_DIRS_EXTRA", [str(extra1), str(extra2)])
    _, h = entrar(client, "gerente")
    antes = client.get("/api/sistema/backup", headers=h).json()
    r = client.post("/api/sistema/backup", headers=h).json()
    assert r["sucesso"] and r["copias_ok"] == 2 and r["copias_falha"] == 0
    assert (destino / r["arquivo"]).stat().st_size > 0
    assert (extra1 / r["arquivo"]).exists() and (extra2 / r["arquivo"]).exists()
    depois = client.get("/api/sistema/backup", headers=h).json()
    assert depois["atrasado"] is False and depois["ultimo_sucesso"]["arquivo"] == r["arquivo"]
    # restauração em banco novo: confere que o backup serve
    env = dict(os.environ)
    r2 = subprocess.run([sys.executable, str(RAIZ / "scripts" / "restaurar_em_teste.py"), str(extra1 / r["arquivo"]), "pizzaria_restauracao_teste"],
                        capture_output=True, text=True, env=env)
    try:
        assert r2.returncode == 0, r2.stderr + r2.stdout
        with psycopg.connect(dbname="pizzaria_restauracao_teste", **BASE) as c:
            assert c.execute("SELECT count(*) FROM usuario").fetchone()[0] >= 1
    finally:
        with psycopg.connect(dbname="postgres", autocommit=True, **BASE) as c:
            c.execute("DROP DATABASE IF EXISTS pizzaria_restauracao_teste WITH (FORCE)")


def test_backup_com_copia_extra_falhando_avisa(client, tmp_path, monkeypatch):
    import api.services.backup as bk
    arquivo_no_lugar_de_pasta = tmp_path / "arquivo"
    arquivo_no_lugar_de_pasta.write_text("x")
    monkeypatch.setattr(bk, "BACKUP_DIR", str(tmp_path / "bk"))
    monkeypatch.setattr(bk, "BACKUP_DIRS_EXTRA", [str(arquivo_no_lugar_de_pasta / "sub")])
    _, h = entrar(client, "administrador")
    r = client.post("/api/sistema/backup", headers=h).json()
    assert r["sucesso"] and r["copias_falha"] == 1 and "falhou" in r["detalhe"]


def test_backup_sem_pg_dump_registra_falha(client, tmp_path, monkeypatch):
    import api.services.backup as bk
    monkeypatch.setattr(bk, "PG_DUMP", "/nao/existe/pg_dump")
    monkeypatch.setattr(bk, "BACKUP_DIR", str(tmp_path / "bk"))
    _, h = entrar(client, "administrador")
    r = client.post("/api/sistema/backup", headers=h).json()
    assert r["sucesso"] is False and "pg_dump" in r["detalhe"]


def test_migration_editada_depois_de_aplicada_e_recusada(tmp_path):
    pasta = tmp_path / "m"
    pasta.mkdir()
    (pasta / "001_a.sql").write_text("SELECT 1;")
    env = dict(os.environ, MIGRATIONS_DIR=str(pasta), DB_NAME="pizzaria_migr_teste")
    with psycopg.connect(dbname="postgres", autocommit=True, **BASE) as c:
        c.execute("DROP DATABASE IF EXISTS pizzaria_migr_teste WITH (FORCE)")
        c.execute("CREATE DATABASE pizzaria_migr_teste")
    try:
        script = str(RAIZ / "scripts" / "aplicar_migrations_pg.py")
        assert subprocess.run([sys.executable, script], env=env, capture_output=True).returncode == 0
        (pasta / "001_a.sql").write_text("SELECT 2;")
        r = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True)
        assert r.returncode != 0 and "checksum" in r.stderr
    finally:
        with psycopg.connect(dbname="postgres", autocommit=True, **BASE) as c:
            c.execute("DROP DATABASE IF EXISTS pizzaria_migr_teste WITH (FORCE)")
