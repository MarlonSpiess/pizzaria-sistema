"""Canais de venda: só gerência acessa; fila, recusa e mapa de produtos."""
from tests.conftest import entrar
from tests.test_vendas import cardapio  # noqa: F401  (fixture)


def _canal(client, h, codigo="anotaai"):
    return next(c for c in client.get("/api/canais", headers=h).json() if c["codigo"] == codigo)


def test_so_gerencia_acessa_canais(client):
    for perfil, esperado in (("atendente", 403), ("massa", 403), ("pizzaiolo", 403), ("acabamento", 403), ("gerente", 200), ("subgerente", 200)):
        _, h = entrar(client, perfil)
        assert client.get("/api/canais", headers=h).status_code == esperado, perfil


def test_ativar_fila_recusa_e_mapa(client, cardapio, conn_teste):  # noqa: F811
    _, h = entrar(client, "gerente")
    c = _canal(client, h)
    assert c["ativo"] is False and {x["codigo"] for x in client.get("/api/canais", headers=h).json()} >= {"anotaai", "ifood"}
    assert client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=h).status_code == 403  # gerência não configura
    _, adm = entrar(client, "administrador")
    assert client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=adm).json()["ativo"] is True
    conn_teste.execute("INSERT INTO entrada_canal (loja_id, canal_id, id_externo, recebido_em) VALUES (1, %s, 'AB123', now())", (c["id"],))
    fila = client.get(f"/api/canais/{c['id']}/fila", headers=h).json()
    assert fila[0]["id_externo"] == "AB123" and fila[0]["situacao"] == "pendente"
    assert client.post(f"/api/canais/fila/{fila[0]['id']}/recusar", json={"motivo": ""}, headers=h).status_code == 422
    assert client.post(f"/api/canais/fila/{fila[0]['id']}/recusar", json={"motivo": "Sem sabor"}, headers=h).status_code == 200
    assert client.post(f"/api/canais/fila/{fila[0]['id']}/recusar", json={"motivo": "Sem sabor"}, headers=h).status_code == 409
    pid = cardapio["trad"]["id"]
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": pid, "id_externo": "X1"}, headers=adm).status_code == 200
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": pid, "id_externo": "X2"}, headers=adm).status_code == 200
    assert next(m for m in client.get(f"/api/canais/{c['id']}/produtos", headers=h).json() if m["produto_id"] == pid)["id_externo"] == "X2"
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": 99999999, "id_externo": "Z"}, headers=adm).status_code == 404


def test_escritas_negadas_a_quem_nao_e_gerencia(client, cardapio):  # noqa: F811
    _, g = entrar(client, "gerente")
    c = _canal(client, g)
    pid = cardapio["trad"]["id"]
    for perfil in ("atendente", "massa", "pizzaiolo", "acabamento"):
        _, h = entrar(client, perfil)
        assert client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=h).status_code == 403, perfil
        assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": pid, "id_externo": "Q"}, headers=h).status_code == 403, perfil
        assert client.post("/api/canais/fila/1/recusar", json={"motivo": "x"}, headers=h).status_code == 403, perfil
        assert client.get(f"/api/canais/{c['id']}/fila", headers=h).status_code == 403, perfil
    for perfil in ("administrador", "proprietario"):
        _, h = entrar(client, perfil)
        assert client.get("/api/canais", headers=h).status_code == 200, perfil
    assert client.get("/api/canais/99999999/fila", headers=g).status_code == 404


def test_id_externo_repetido_no_canal_da_409(client, cardapio):  # noqa: F811
    _, g = entrar(client, "gerente")
    _, adm = entrar(client, "administrador")
    c = _canal(client, g)
    a, b = cardapio["trad"]["id"], cardapio["esp"]["id"]
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": a, "id_externo": "DUP"}, headers=adm).status_code == 200
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": b, "id_externo": "DUP"}, headers=adm).status_code == 409
