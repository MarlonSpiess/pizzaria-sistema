"""Achados do QA cego da fatia 1A: concorrência, entrada hostil, limites e papel restrito do banco."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from tests.conftest import BASE, RAIZ, criar_usuario_direto, entrar, novo_login


def test_alteracao_de_usuario_espera_a_trava_dos_administradores(client, conn_teste):
    """A corrida (duas desativações simultâneas) é evitada por uma trava; aqui provamos que a trava existe e serializa:
    com a trava presa por outra conexão, o PATCH espera e só conclui quando ela é solta."""
    _, h = entrar(client, "administrador")
    alvo, _ = criar_usuario_direto("atendente")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=h).json() if u["usuario"] == alvo)
    conn_teste.execute("SELECT pg_advisory_lock(2, 1)")
    resultado = []
    t = threading.Thread(target=lambda: resultado.append(client.patch(f"/api/usuarios/{uid}", json={"nome": "Novo Nome"}, headers=h).status_code))
    t.start()
    t.join(1.5)
    assert t.is_alive() and resultado == []  # esperando a trava
    conn_teste.execute("SELECT pg_advisory_unlock(2, 1)")
    t.join(10)
    assert resultado == [200]


def test_desativar_ultimo_administrador_sem_corrida_e_recusado(client, conn_teste):
    conn_teste.execute("UPDATE usuario SET ativo = false WHERE perfil = 'administrador'")
    l1, h1 = entrar(client, "administrador")
    outro, _ = criar_usuario_direto("administrador")
    ids = {u["usuario"]: u["id"] for u in client.get("/api/usuarios", headers=h1).json()}
    assert client.patch(f"/api/usuarios/{ids[outro]}", json={"ativo": False}, headers=h1).status_code == 200
    # agora só resta o próprio: já coberto pela regra de não desativar a si mesmo
    assert client.patch(f"/api/usuarios/{ids[l1]}", json={"ativo": False}, headers=h1).status_code == 400


@pytest.mark.parametrize("corpo", [{"nome": None}, {"perfil": None}, {"ativo": None}, {"nome": "A\x00B"}, {"nome": "A\nB"},
                                   {"nome": "x‮ydob"}, {"nome": "x" * 121}])
def test_patch_hostil_nunca_da_500(client, admin, corpo):
    _, h = admin
    login, _ = criar_usuario_direto("atendente")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=h).json() if u["usuario"] == login)
    assert client.patch(f"/api/usuarios/{uid}", json=corpo, headers=h).status_code == 422


def test_senha_com_acentos_acima_de_72_bytes_e_recusada_com_422(client, admin):
    _, h = admin
    base = {"usuario": novo_login("ac"), "nome": "N", "perfil": "atendente"}
    assert client.post("/api/usuarios", json={**base, "senha": "ç" * 40}, headers=h).status_code == 422  # 80 bytes
    assert client.post("/api/usuarios", json={**base, "senha": "ç" * 30}, headers=h).status_code == 201  # 60 bytes


def test_senhas_fracas_recusadas(client, admin):
    _, h = admin
    login = novo_login("fr")
    for s in ("12345678", "PASSWORD", login * 2 if len(login * 2) >= 8 else login + "xxxxxxxx"):
        base = {"usuario": login if s.startswith(login) else novo_login("fr"), "nome": "N", "perfil": "atendente", "senha": s}
        if s.startswith(login):
            base["usuario"] = s
        assert client.post("/api/usuarios", json=base, headers=h).status_code == 422


def test_login_hostil_nao_da_500(client):
    assert client.post("/api/auth/login", json={"usuario": "a\x00b", "senha": "x"}).status_code == 422
    assert client.post("/api/auth/login", json={"usuario": "u" * 60000, "senha": "x"}).status_code == 422
    assert client.post("/api/auth/login", json={"usuario": "ok", "senha": "x" * 5000}).status_code == 422
    assert client.post("/api/auth/login", json={"usuario": "ok", "senha": "a\x00b"}).status_code == 422


def test_parametros_formato_estrito_e_sem_notacao_cientifica(client, admin):
    _, h = admin
    put = lambda c, v: client.put(f"/api/parametros/{c}", json={"valor": v}, headers=h)
    assert put("forno_tempo_min", "10").json()["valor"] == "10"
    assert put("forno_tempo_min", "2,5").json()["valor"] == "2.5"
    for ruim in ("1e1", "1_0", "١٢", "NaN", "Infinity", "-1", "1.1234567", "1 0", "0x10"):
        assert put("valor_entrega_padrao", ruim).status_code == 400, ruim
    assert put("loja_nome", "A\x00B").status_code == 422
    assert put("loja_nome", "Pizzaria <b>X</b>").status_code == 200  # texto livre, escapado na tela


def test_limpar_parametro_volta_ao_padrao_do_catalogo(client, admin):
    _, h = admin
    client.put("/api/parametros/forno_tempo_min", json={"valor": "3"}, headers=h)
    r = client.put("/api/parametros/forno_tempo_min", json={"valor": None}, headers=h).json()
    assert r["valor"] == "2" and r["definido"] is False
    r = client.put("/api/parametros/formas_pagamento_aceitas", json={"valor": None}, headers=h).json()
    assert r["valor"] == ["dinheiro", "pix", "credito", "debito"]


def test_corpo_grande_recusado_inclusive_em_partes(client):
    corpo = b'{"usuario":"a","senha":"' + b"x" * 1_500_000 + b'"}'
    assert client.post("/api/auth/login", content=corpo, headers={"Content-Type": "application/json"}).status_code == 413

    def pedacos():
        for _ in range(30):
            yield b"x" * 100_000
    r = client.post("/api/auth/login", content=pedacos(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_auditoria_deslocamento_enorme_nao_da_500(client, admin):
    assert client.get("/api/auditoria?deslocamento=99999999999999999999", headers=admin[1]).status_code == 422


def test_login_e_logout_ficam_na_auditoria(client, admin):
    login, h = admin
    client.post("/api/auth/logout", headers=h)
    _, h2 = entrar(client, "gerente")
    acoes = {(a["acao"], a["usuario"]) for a in client.get("/api/auditoria?entidade=sessao&limite=50", headers=h2).json()["data"]}
    assert ("login", login) in acoes and ("logout", login) in acoes


def test_backups_simultaneos_nao_colidem(client, tmp_path, monkeypatch):
    import api.services.backup as bk
    monkeypatch.setattr(bk, "BACKUP_DIR", str(tmp_path / "bk"))
    monkeypatch.setattr(bk, "BACKUP_DIRS_EXTRA", [])
    _, h = entrar(client, "gerente")
    with ThreadPoolExecutor(5) as ex:
        resp = list(ex.map(lambda _: client.post("/api/sistema/backup", headers=h), range(5)))
    codigos = sorted(r.status_code for r in resp)
    assert set(codigos) <= {200, 409} and 200 in codigos
    arquivos = list((tmp_path / "bk").glob("*.dump"))
    nomes_ok = [r.json()["arquivo"] for r in resp if r.status_code == 200]
    assert len(nomes_ok) == len(set(nomes_ok)) == len(arquivos)
    assert all(oct(a.stat().st_mode & 0o777) == "0o600" for a in arquivos)


def test_backup_falho_nao_deixa_arquivo_parcial(client, tmp_path, monkeypatch):
    import api.services.backup as bk
    monkeypatch.setattr(bk, "PG_DUMP", "/bin/false")
    monkeypatch.setattr(bk, "BACKUP_DIR", str(tmp_path / "bk"))
    _, h = entrar(client, "administrador")
    r = client.post("/api/sistema/backup", headers=h).json()
    assert r["sucesso"] is False and list((tmp_path / "bk").glob("*.dump")) == []
    assert str(tmp_path) not in str(r)


def test_pasta_de_backup_sem_permissao_nao_da_500(client, tmp_path, monkeypatch):
    import api.services.backup as bk
    arquivo = tmp_path / "arq"
    arquivo.write_text("x")
    monkeypatch.setattr(bk, "BACKUP_DIR", str(arquivo / "sub"))
    _, h = entrar(client, "administrador")
    r = client.post("/api/sistema/backup", headers=h)
    assert r.status_code == 200 and r.json()["sucesso"] is False and str(tmp_path) not in r.text


def test_papel_restrito_nao_altera_nem_desliga_a_auditoria(client, admin, conn_teste):
    papel = "pizzaria_app_teste"
    conn_teste.execute(f"DROP OWNED BY {papel}") if conn_teste.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (papel,)).fetchone() else None
    conn_teste.execute(f"DROP ROLE IF EXISTS {papel}")
    conn_teste.execute(f"CREATE ROLE {papel} LOGIN PASSWORD 'p'")
    sql = (RAIZ / "scripts" / "papel_app.sql").read_text(encoding="utf-8").replace(":app_role", papel)
    for comando in [c for c in sql.split(";\n") if c.strip() and not c.strip().startswith("--")]:
        conn_teste.execute("\n".join(l for l in comando.splitlines() if not l.startswith("--")))
    try:
        base = dict(BASE, user=papel, password="p")
        with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **base) as c:
            c.execute("SELECT count(*) FROM usuario")  # o app continua lendo e escrevendo o que precisa
            for ruim in ("UPDATE auditoria SET acao='x'", "DELETE FROM auditoria", "TRUNCATE auditoria",
                         "ALTER TABLE auditoria DISABLE TRIGGER ALL", "SET session_replication_role = replica"):
                with pytest.raises(psycopg.Error):
                    c.execute(ruim)
            c.execute("INSERT INTO auditoria (loja_id, quando, acao, entidade) VALUES (1, now(), 't', 't')")
    finally:
        conn_teste.execute(f"DROP OWNED BY {papel}")
        conn_teste.execute(f"DROP ROLE {papel}")
