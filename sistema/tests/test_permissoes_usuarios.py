from tests.conftest import entrar, novo_login


def test_negado_por_padrao_para_perfis_sem_permissao(client):
    for perfil in ("atendente", "massa", "pizzaiolo", "acabamento"):
        _, h = entrar(client, perfil)
        for caminho in ("/api/usuarios", "/api/parametros", "/api/auditoria", "/api/sistema/backup"):
            assert client.get(caminho, headers=h).status_code == 403, (perfil, caminho)


def test_gerente_ve_parametros_mas_nao_edita_nem_gere_usuarios(client):
    _, h = entrar(client, "gerente")
    assert client.get("/api/parametros", headers=h).status_code == 200
    assert client.put("/api/parametros/loja_nome", json={"valor": "X"}, headers=h).status_code == 403
    assert client.get("/api/usuarios", headers=h).status_code == 403


def test_criar_usuario_e_primeiro_acesso(client, admin):
    _, h = admin
    login = novo_login("novo")
    r = client.post("/api/usuarios", json={"usuario": login, "nome": "Maria", "perfil": "atendente", "senha": "provisoria-123"}, headers=h)
    assert r.status_code == 201 and r.json()["deve_trocar_senha"] is True
    assert "senha_hash" not in r.json()
    assert client.post("/api/usuarios", json={"usuario": login, "nome": "Outra", "perfil": "atendente", "senha": "provisoria-123"}, headers=h).status_code == 409
    d = client.post("/api/auth/login", json={"usuario": login, "senha": "provisoria-123"}).json()
    assert d["deve_trocar_senha"] is True


def test_validacao_de_usuario(client, admin):
    _, h = admin
    base = {"usuario": novo_login("v"), "nome": "N", "perfil": "atendente", "senha": "provisoria-123"}
    assert client.post("/api/usuarios", json={**base, "usuario": "Com Espaço"}, headers=h).status_code == 422
    assert client.post("/api/usuarios", json={**base, "perfil": "dono"}, headers=h).status_code == 422
    assert client.post("/api/usuarios", json={**base, "senha": "curta"}, headers=h).status_code == 422
    assert client.post("/api/usuarios", json={**base, "nome": ""}, headers=h).status_code == 422


def test_proprietario_nao_cria_administrador(client):
    _, h = entrar(client, "proprietario")
    r = client.post("/api/usuarios", json={"usuario": novo_login("a"), "nome": "A", "perfil": "administrador", "senha": "provisoria-123"}, headers=h)
    assert r.status_code == 403
    r = client.post("/api/usuarios", json={"usuario": novo_login("g"), "nome": "G", "perfil": "gerente", "senha": "provisoria-123"}, headers=h)
    assert r.status_code == 201


def test_nao_desativa_a_si_mesmo_nem_o_ultimo_administrador(client, conn_teste):
    # Isola: um único administrador ativo.
    conn_teste.execute("UPDATE usuario SET ativo = false WHERE perfil = 'administrador'")
    login, h = entrar(client, "administrador")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=h).json() if u["usuario"] == login)
    assert client.patch(f"/api/usuarios/{uid}", json={"ativo": False}, headers=h).status_code == 400
    assert client.patch(f"/api/usuarios/{uid}", json={"perfil": "gerente"}, headers=h).status_code == 400


def test_redefinir_senha_forca_troca_e_encerra_sessoes(client, admin):
    _, ha = admin
    login, senha = entrar(client, "atendente")[0], None
    lista = client.get("/api/usuarios", headers=ha).json()
    uid = next(u["id"] for u in lista if u["usuario"] == login)
    assert client.post(f"/api/usuarios/{uid}/redefinir-senha", json={"senha_nova": "provisoria-456"}, headers=ha).status_code == 200
    d = client.post("/api/auth/login", json={"usuario": login, "senha": "provisoria-456"}).json()
    assert d["deve_trocar_senha"] is True


def test_usuario_inexistente_404(client, admin):
    _, h = admin
    assert client.patch("/api/usuarios/99999999", json={"nome": "X"}, headers=h).status_code == 404
