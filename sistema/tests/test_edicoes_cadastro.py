"""Edições de cadastro que estavam sem teste (achado da medida de CRAP na revisão ub-mode)."""
from datetime import date, timedelta

from tests.conftest import criar_usuario_direto, entrar, novo_login
from tests.test_estoque_compras import _inicial
from tests.test_fichas import _item


def test_editar_local_de_estoque(client):
    h = entrar(client, "gerente")[1]
    assert client.patch("/api/estoque/locais/999999", json={"nome": "X"}, headers=h).status_code == 404
    loc = client.post("/api/estoque/locais", json={"nome": novo_login("Local")}, headers=h).json()
    assert client.patch(f"/api/estoque/locais/{loc['id']}", json={}, headers=h).status_code == 400
    novo = novo_login("Despensa")
    r = client.patch(f"/api/estoque/locais/{loc['id']}", json={"nome": novo}, headers=h)
    assert r.status_code == 200 and r.json()["nome"] == novo
    item = _item(client, h)
    _inicial(client, h, item["id"], "10", "1,00", local_id=loc["id"])
    r = client.patch(f"/api/estoque/locais/{loc['id']}", json={"ativo": False}, headers=h)
    assert r.status_code == 409 and "transfira" in r.json()["detail"]
    vazio = client.post("/api/estoque/locais", json={"nome": novo_login("Vazio")}, headers=h).json()
    r = client.patch(f"/api/estoque/locais/{vazio['id']}", json={"ativo": False}, headers=h)
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert client.patch(f"/api/estoque/locais/{vazio['id']}", json={"nome": "y"}, headers=entrar(client, "atendente")[1]).status_code == 403


def test_editar_maquininha(client):
    h = entrar(client, "gerente")[1]
    assert client.patch("/api/caixa/maquininhas/999999", json={"nome": "X"}, headers=h).status_code == 404
    a = client.post("/api/caixa/maquininhas", json={"nome": novo_login("Cielo")}, headers=h).json()
    b = client.post("/api/caixa/maquininhas", json={"nome": novo_login("Rede")}, headers=h).json()
    assert client.patch(f"/api/caixa/maquininhas/{a['id']}", json={}, headers=h).status_code == 400
    r = client.patch(f"/api/caixa/maquininhas/{a['id']}", json={"ativo": False}, headers=h)
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert client.patch(f"/api/caixa/maquininhas/{a['id']}", json={"nome": b["nome"]}, headers=h).status_code == 409  # nome repetido
    assert client.patch(f"/api/caixa/maquininhas/{a['id']}", json={"nome": "Z"}, headers=entrar(client, "atendente")[1]).status_code == 403


def test_editar_funcionario(client):
    h = entrar(client, "gerente")[1]
    client.post("/api/rh/iniciar-padrao", headers=h)
    funcs = {f["nome"]: f["id"] for f in client.get("/api/rh/funcoes", headers=h).json()}
    fid = client.post("/api/rh/funcionarios", json={"nome": novo_login("Func"), "funcao_id": funcs["Pizzaiolo"],
                                                    "admissao": str(date.today() - timedelta(days=30))}, headers=h).json()["id"]
    assert client.patch(f"/api/rh/funcionarios/{fid}", json={}, headers=h).status_code == 400
    assert client.patch("/api/rh/funcionarios/999999", json={"nome": "X"}, headers=h).status_code == 404
    assert client.patch(f"/api/rh/funcionarios/{fid}", json={"funcao_id": 999999}, headers=h).status_code == 404
    assert client.patch(f"/api/rh/funcionarios/{fid}", json={"usuario_id": 999999}, headers=h).status_code == 404
    login, _ = criar_usuario_direto("pizzaiolo")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=entrar(client, "administrador")[1]).json() if u["usuario"] == login)
    r = client.patch(f"/api/rh/funcionarios/{fid}", json={"nome": "Nome Novo", "funcao_id": funcs["Massa"], "usuario_id": uid}, headers=h)
    assert r.status_code == 200
    f = next(x for x in client.get("/api/rh/funcionarios", headers=h).json() if x["id"] == fid)
    assert f["nome"] == "Nome Novo"
    assert client.post(f"/api/rh/funcionarios/{fid}/desligar", json={"data": str(date.today()), "motivo": "pedido"}, headers=h).status_code == 200
    assert client.patch(f"/api/rh/funcionarios/{fid}", json={"nome": "Outro"}, headers=h).status_code in (404, 409)  # desligado não se edita
