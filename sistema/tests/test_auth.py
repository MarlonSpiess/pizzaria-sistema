from tests.conftest import criar_usuario_direto, entrar, novo_login


def test_login_valido_e_me(client):
    login, senha = criar_usuario_direto("atendente")
    r = client.post("/api/auth/login", json={"usuario": login, "senha": senha})
    assert r.status_code == 200
    d = r.json()
    assert d["perfil"] == "atendente" and d["token"]
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + d["token"]})
    assert me.status_code == 200 and me.json()["usuario"] == login


def test_login_erro_generico_igual_para_todos_os_casos(client):
    login, senha = criar_usuario_direto("atendente")
    inativo, s2 = criar_usuario_direto("atendente", ativo=False)
    respostas = [
        client.post("/api/auth/login", json={"usuario": login, "senha": "errada-errada"}),
        client.post("/api/auth/login", json={"usuario": novo_login("nao"), "senha": "qualquer-coisa"}),
        client.post("/api/auth/login", json={"usuario": inativo, "senha": s2}),
    ]
    assert {r.status_code for r in respostas} == {401}
    assert len({r.text for r in respostas}) == 1


def test_bloqueio_apos_5_falhas_inclusive_usuario_inexistente(client):
    for alvo in (criar_usuario_direto("atendente")[0], novo_login("fantasma")):
        codigos = [client.post("/api/auth/login", json={"usuario": alvo, "senha": "errada-errada"}).status_code for _ in range(7)]
        assert codigos[:5] == [401] * 5 and codigos[5:] == [429, 429]


def test_bloqueio_vale_mesmo_com_senha_certa(client):
    login, senha = criar_usuario_direto("atendente")
    for _ in range(5):
        client.post("/api/auth/login", json={"usuario": login, "senha": "errada-errada"})
    assert client.post("/api/auth/login", json={"usuario": login, "senha": senha}).status_code == 429


def test_sem_token_e_token_invalido(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer abc"}).status_code == 401
    assert client.get("/api/usuarios").status_code == 401


def test_logout_encerra_sessao(client):
    _, h = entrar(client)
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_token_guardado_como_hash(client, conn_teste):
    login, senha = criar_usuario_direto("atendente")
    token = client.post("/api/auth/login", json={"usuario": login, "senha": senha}).json()["token"]
    tokens = [r[0] for r in conn_teste.execute("SELECT token FROM sessao").fetchall()]
    assert token not in tokens and len(tokens) >= 1


def test_usuario_desativado_perde_sessao_na_hora(client, admin):
    _, ha = admin
    login, senha = criar_usuario_direto("atendente")
    token = client.post("/api/auth/login", json={"usuario": login, "senha": senha}).json()["token"]
    h = {"Authorization": "Bearer " + token}
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=ha).json() if u["usuario"] == login)
    assert client.patch(f"/api/usuarios/{uid}", json={"ativo": False}, headers=ha).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_troca_obrigatoria_de_senha(client):
    login, senha = criar_usuario_direto("gerente", deve_trocar=True)
    d = client.post("/api/auth/login", json={"usuario": login, "senha": senha}).json()
    h = {"Authorization": "Bearer " + d["token"]}
    assert d["deve_trocar_senha"] is True
    assert client.get("/api/parametros", headers=h).status_code == 403  # bloqueado até trocar
    assert client.post("/api/auth/trocar-senha", json={"senha_atual": "errada", "senha_nova": "nova-senha-123"}, headers=h).status_code == 400
    assert client.post("/api/auth/trocar-senha", json={"senha_atual": senha, "senha_nova": senha}, headers=h).status_code == 400
    assert client.post("/api/auth/trocar-senha", json={"senha_atual": senha, "senha_nova": "curta"}, headers=h).status_code == 422
    assert client.post("/api/auth/trocar-senha", json={"senha_atual": senha, "senha_nova": "nova-senha-123"}, headers=h).status_code == 200
    assert client.get("/api/parametros", headers=h).status_code == 200
    assert client.post("/api/auth/login", json={"usuario": login, "senha": senha}).status_code == 401
    assert client.post("/api/auth/login", json={"usuario": login, "senha": "nova-senha-123"}).status_code == 200


def test_entrada_estrita_recusa_tipos_errados(client):
    assert client.post("/api/auth/login", json={"usuario": 123, "senha": "x"}).status_code == 422
    assert client.post("/api/auth/login", json={"usuario": "a", "senha": "x", "extra": 1}).status_code == 422
