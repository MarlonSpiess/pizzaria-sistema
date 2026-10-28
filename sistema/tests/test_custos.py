from datetime import date
from decimal import Decimal

import pytest

from tests.conftest import entrar
from tests.test_estoque_compras import _inicial  # noqa: F401
from tests.test_fichas import _ficha, _item
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

D = Decimal


@pytest.fixture
def hs(client):
    return {p: entrar(client, p)[1] for p in ("administrador", "gerente", "subgerente", "atendente")}


def test_permissoes(client, hs):
    assert client.get("/api/custos/produtos", headers=hs["atendente"]).status_code == 403
    assert client.get("/api/custos/resultado", headers=hs["atendente"]).status_code == 403
    assert client.get("/api/custos/produtos", headers=hs["subgerente"]).status_code == 200


def test_custo_do_produto_pela_ficha_com_fator_de_correcao(client, cardapio, hs):
    h = hs["gerente"]
    queijo = _item(client, h, "insumo", "g")
    _inicial(client, h, queijo["id"], "10000", "0,05")
    sabor = cardapio["trad"]
    assert _ficha(client, h, f"produto/{sabor['id']}", [{"item_id": queijo["id"], "quantidade": "100", "perda_pct": "10"}]).status_code == 200
    r = client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=grande", headers=h).json()
    assert r["custo"] == "11.00" and not r["sem_ficha"]  # 2 meias x 100 g x 1,10 x R$ 0,05
    assert r["preco"] == "35.00" and abs(D(r["margem"]) - (D("24.00") - D("35.00") * D(r["taxa_cartao_media_pct"]) / 100)) < D("0.01")
    assert r["linhas"][0]["valor"] == "11.00"
    broto = client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=broto", headers=h).json()
    assert broto["custo"] == "5.50"
    # fator de correção 1,2 no queijo: o custo sobe 20%
    assert client.put(f"/api/custos/fatores/{queijo['id']}", json={"fator_correcao": "1,2"}, headers=h).status_code == 200
    assert client.put(f"/api/custos/fatores/{queijo['id']}", json={"fator_correcao": "0,5"}, headers=h).status_code == 422
    assert client.put(f"/api/custos/fatores/{queijo['id']}", json={"fator_correcao": "1,2"}, headers=hs["atendente"]).status_code == 403
    assert client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=grande", headers=h).json()["custo"] == "13.20"
    assert any(f["item_id"] == queijo["id"] and f["fator_correcao"] == "1.2" for f in client.get("/api/custos/fatores", headers=h).json())
    # preço sugerido por margem: custo / (1 - margem - taxa)
    s = client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=grande&margem_desejada=60", headers=h).json()
    taxa = D(s["taxa_cartao_media_pct"]) / 100
    assert abs(D(s["preco_sugerido"]) - D("13.20") / (1 - D("0.6") - taxa)) < D("0.01")
    assert client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=grande&margem_desejada=100", headers=h).status_code == 400
    assert client.get(f"/api/custos/produtos/{sabor['id']}?tamanho=gigante", headers=h).status_code == 400


def test_grande_com_dois_sabores_soma_meia_receita_de_cada(client, cardapio, hs):
    h = hs["gerente"]
    a, b = _item(client, h, "insumo", "g"), _item(client, h, "insumo", "g")
    _inicial(client, h, a["id"], "1000", "0,10")
    _inicial(client, h, b["id"], "1000", "0,20")
    s1, s2 = cardapio["trad"], cardapio["esp"]
    assert _ficha(client, h, f"produto/{s1['id']}", [{"item_id": a["id"], "quantidade": "100", "perda_pct": "0"}]).status_code == 200
    assert _ficha(client, h, f"produto/{s2['id']}", [{"item_id": b["id"], "quantidade": "100", "perda_pct": "0"}]).status_code == 200
    r = client.get(f"/api/custos/produtos/{s1['id']}?tamanho=grande&sabor2_id={s2['id']}", headers=h).json()
    assert r["custo"] == "30.00" and r["preco"] == "42.50"  # 100 x 0,10 + 100 x 0,20; média de 35 e 50
    assert client.get(f"/api/custos/produtos/{s1['id']}?tamanho=broto&sabor2_id={s2['id']}", headers=h).status_code == 400


def test_produto_sem_ficha_nao_mostra_margem(client, cardapio, hs):
    r = client.get("/api/custos/produtos", headers=hs["gerente"]).json()
    sem = next(p for p in r["produtos"] if p["produto_id"] == cardapio["borda"]["id"] or p["sem_ficha"])
    assert sem["sem_ficha"] and sem["margem"] is None


def test_cmv_e_resultado_do_mes(client, cardapio, hs):
    h = hs["administrador"]
    hoje = date.today()
    mes = hoje.strftime("%Y-%m")
    c = client.get(f"/api/custos/cmv?mes={mes}", headers=h).json()
    assert c["fechado"] is False
    assert D(c["cmv_real"]) == D(c["estoque_inicial"]) + D(c["compras"]) - D(c["estoque_final"])
    r = client.get(f"/api/custos/resultado?mes={mes}", headers=h).json()
    assert D(r["receita"]) == D(r["receita_bruta"]) - D(r["descontos"])
    assert D(r["margem_contribuicao"]) == D(r["receita"]) - D(r["cmv"]) - D(r["custos_variaveis"])
    assert D(r["resultado_operacional"]) == D(r["margem_contribuicao"]) - D(r["custos_fixos"])
    assert client.get("/api/custos/resultado?mes=2026-13", headers=h).status_code == 400
    # o mês corrente não fecha; mês passado fecha uma vez e o valor gravado não muda
    assert client.post("/api/custos/cmv/fechar", json={"mes": mes}, headers=h).status_code == 400
    assert client.post("/api/custos/cmv/fechar", json={"mes": "2019-01"}, headers=hs["atendente"]).status_code == 403
    # mês sem movimento (ou antes de 2020) não fecha: o fechamento é definitivo
    assert client.post("/api/custos/cmv/fechar", json={"mes": "2019-01"}, headers=h).status_code == 400
    assert client.post("/api/custos/cmv/fechar", json={"mes": "2024-01"}, headers=h).status_code == 400

