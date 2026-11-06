"""Regra de preço da pizza (decisões C2, D1 e T4), sem banco."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from api.services.dinheiro import metade_para_cima
from api.services.preco import conferir_sabores, preco_pizza


def S(nome, valor):
    return {"nome": nome, "valor": Decimal(valor)}


def test_um_sabor_vale_o_preco_do_tamanho():
    r = preco_pizza("broto", [S("Calabresa", "25.00")], [])
    assert r == {"tamanho": "broto", "itens": [{"descricao": "Calabresa (broto)", "valor": "25.00"}], "total": "25.00"}


def test_grande_dois_sabores_e_metade_de_cada_arredondada_para_cima():
    r = preco_pizza("grande", [S("Calabresa", "35.00"), S("Camarão", "50.01")], [])
    assert [i["valor"] for i in r["itens"]] == ["17.50", "25.01"]
    assert r["itens"][1]["descricao"] == "Metade Camarão (Grande 50,01 ÷ 2)"
    assert r["total"] == "42.51"


def test_borda_e_adicional_somam():
    r = preco_pizza("grande", [S("Calabresa", "35.00")], [S("Borda catupiry", "10.00"), S("Bacon", "4.50")])
    assert r["total"] == "49.50"
    assert r["itens"][-1] == {"descricao": "Bacon", "valor": "4.50"}


@pytest.mark.parametrize("v,metade", [("35.00", "17.50"), ("35.01", "17.51"), ("0.01", "0.01"), ("49.99", "25.00")])
def test_metade_para_cima(v, metade):
    assert str(metade_para_cima(Decimal(v))) == metade


def test_dois_sabores_so_na_grande():
    with pytest.raises(HTTPException) as e:
        conferir_sabores("broto", 1, 2)
    assert (e.value.status_code, e.value.detail) == (400, "Só a pizza Grande aceita dois sabores.")


def test_dois_sabores_iguais_recusados():
    with pytest.raises(HTTPException) as e:
        conferir_sabores("grande", 3, 3)
    assert (e.value.status_code, e.value.detail) == (400, "Escolha dois sabores diferentes ou só um sabor.")


def test_um_sabor_em_qualquer_tamanho_passa():
    conferir_sabores("broto", 1, None)
    conferir_sabores("grande", 1, 2)
