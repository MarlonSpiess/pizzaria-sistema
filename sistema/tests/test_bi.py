from decimal import Decimal

import pytest

from tests.conftest import entrar
from tests.test_estoque_compras import _inicial  # noqa: F401
from tests.test_fichas import _ficha, _item
from tests.test_producao import _g, _pagar
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

D = Decimal


@pytest.fixture
def hs(client):
    return {p: entrar(client, p)[1] for p in ("administrador", "gerente", "subgerente", "atendente")}


def test_permissoes_e_salarios_ocultos(client, hs):
    assert client.get("/api/bi/painel", headers=hs["atendente"]).status_code == 403
    assert client.get("/api/bi/dre", headers=hs["atendente"]).status_code == 403
    g = client.get("/api/bi/dre", headers=hs["gerente"]).json()
    assert g["pessoal"] is None and g["ebitda"] is None and g["resultado_operacional"] is None
    a = client.get("/api/bi/dre", headers=hs["administrador"]).json()
    assert a["pessoal"] is not None and a["resultado_operacional"] is not None
    assert client.get("/api/bi/dre?mes=2026-13", headers=hs["gerente"]).status_code == 400
    assert client.get("/api/bi/dre?mes=9999-12", headers=hs["gerente"]).status_code in (200, 400)
    assert client.get("/api/bi/dre.csv", headers=hs["gerente"]).status_code == 200
    assert "pessoal" not in client.get("/api/bi/dre.csv", headers=hs["gerente"]).text


def test_painel_lucratividade_e_producao(client, cardapio, hs):
    h = hs["gerente"]
    queijo = _item(client, h, "insumo", "g")
    _inicial(client, h, queijo["id"], "10000", "0,05")
    assert _ficha(client, h, f"produto/{cardapio['trad']['id']}", [{"item_id": queijo["id"], "quantidade": "100", "perda_pct": "0"}]).status_code == 200
    _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.get("/api/bi/painel", headers=h).json()
    assert D(p["vendas"]) >= 35 and p["pedidos"] >= 1 and p["destaques"]
    assert client.get("/api/bi/painel?data=1999-01-01", headers=h).status_code == 400
    lu = client.get("/api/bi/lucratividade", headers=h).json()
    assert lu["por_sabor"] and lu["por_canal"][0]["nome"] == "balcao" and len(lu["por_dia_semana"]) >= 1
    s = next(x for x in lu["por_sabor"] if x["nome"] == cardapio["trad"]["nome"])
    assert D(s["custo"]) >= D("10.00") and D(s["receita"]) >= 35
    pr = client.get("/api/bi/producao", headers=h).json()
    assert "tempo_por_etapa" in pr and "retrocessos_por_motivo" in pr
    assert client.get("/api/bi/vendas-por-forma.csv", headers=h).text.startswith("forma;valor")
    assert len(client.get("/api/bi/dre/serie?meses=3", headers=h).json()) == 3
    assert client.get("/api/bi/dre/serie?meses=99", headers=h).status_code == 400
    assert isinstance(client.get("/api/bi/alertas", headers=h).json(), list)


def test_folha_nao_vaza_para_quem_nao_ve_salarios(client, hs):
    r = client.get("/api/custos/resultado", headers=hs["gerente"]).json()
    assert r["resultado_operacional"] is None and r["fixos_detalhe"]["pessoal"] is None and r["custos_fixos"] is None
    assert client.get("/api/custos/resultado", headers=hs["administrador"]).json()["resultado_operacional"] is not None
    assert client.get("/api/rh/folha/previa?mes=9999-12", headers=hs["administrador"]).status_code == 400
