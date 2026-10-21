import psycopg
import pytest

from tests.conftest import entrar


def _def(client, h, chave, valor):
    return client.put(f"/api/parametros/{chave}", json={"valor": valor}, headers=h)


def test_catalogo_e_padroes(client, admin):
    _, h = admin
    ps = {p["chave"]: p for p in client.get("/api/parametros", headers=h).json()}
    assert ps["formas_pagamento_aceitas"]["valor"] == ["dinheiro", "pix", "credito", "debito"]
    assert ps["limite_desconto_atendente_pct"]["valor"] is None  # fica vazio até Marlon definir
    assert ps["forno_pizzas_por_vez"]["valor"] is None


def test_definir_validar_e_historico(client, admin):
    _, h = admin
    assert _def(client, h, "limite_desconto_atendente_pct", "10").json()["valor"] == "10.00"
    assert _def(client, h, "limite_desconto_atendente_pct", "12,5").json()["valor"] == "12.50"
    assert _def(client, h, "limite_desconto_atendente_pct", "101").status_code == 400
    assert _def(client, h, "limite_desconto_atendente_pct", "-1").status_code == 400
    assert _def(client, h, "limite_desconto_atendente_pct", "abc").status_code == 400
    assert _def(client, h, "limite_desconto_atendente_pct", "NaN").status_code == 400
    assert _def(client, h, "valor_entrega_padrao", "7,5").json()["valor"] == "7.50"
    assert _def(client, h, "forno_pizzas_por_vez", "4").json()["valor"] == "4"
    assert _def(client, h, "forno_pizzas_por_vez", "4.5").status_code == 400
    assert _def(client, h, "regime_tributario", "simples_nacional").status_code == 200
    assert _def(client, h, "regime_tributario", "outro").status_code == 400
    assert _def(client, h, "inexistente", "1").status_code == 404
    hist = client.get("/api/parametros/limite_desconto_atendente_pct/historico", headers=h).json()
    assert [x["valor"] for x in hist[:2]] == ["12.50", "10.00"]
    assert hist[0]["alterado_por"]
    assert _def(client, h, "limite_desconto_atendente_pct", None).json()["valor"] is None  # limpar volta a "não definido"


def test_formas_de_pagamento(client, admin):
    _, h = admin
    assert _def(client, h, "formas_pagamento_aceitas", ["pix", "dinheiro"]).json()["valor"] == ["dinheiro", "pix"]
    assert _def(client, h, "formas_pagamento_aceitas", ["cheque"]).status_code == 400
    assert _def(client, h, "formas_pagamento_aceitas", ["pix", "pix"]).status_code == 400
    assert _def(client, h, "formas_pagamento_aceitas", "pix").status_code == 400
    _def(client, h, "formas_pagamento_aceitas", ["dinheiro", "pix", "credito", "debito"])


def test_alteracoes_geram_auditoria(client, admin):
    login, h = admin
    _def(client, h, "fundo_troco_padrao", "100")
    r = client.get("/api/auditoria?entidade=parametro&limite=5", headers=h).json()
    a = r["data"][0]
    assert a["usuario"] == login and a["acao"] == "definir" and a["entidade_id"] == "fundo_troco_padrao"
    assert a["depois"]["valor"] == "100.00"


def test_auditoria_so_aceita_insercao(conn_teste, client, admin):
    _def(client, admin[1], "tolerancia_diferenca_caixa", "2")
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE auditoria SET acao = 'x'")
    with pytest.raises(psycopg.Error):
        conn_teste.execute("DELETE FROM auditoria")
    with pytest.raises(psycopg.Error):
        conn_teste.execute("TRUNCATE auditoria")


def test_criar_usuario_gera_auditoria_sem_senha(client, admin):
    _, h = admin
    from tests.conftest import novo_login
    login = novo_login("aud")
    client.post("/api/usuarios", json={"usuario": login, "nome": "A", "perfil": "atendente", "senha": "provisoria-123"}, headers=h)
    r = client.get("/api/auditoria?entidade=usuario&limite=5", headers=h).json()["data"]
    achada = next(a for a in r if a["acao"] == "criar" and a["depois"]["usuario"] == login)
    assert "senha" not in str(achada)


def test_paginacao_da_auditoria_valida_limites(client, admin):
    _, h = admin
    assert client.get("/api/auditoria?limite=0", headers=h).status_code == 422
    assert client.get("/api/auditoria?limite=501", headers=h).status_code == 422
