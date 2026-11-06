"""Fixa o comportamento de normalizar(): o valor que a tela manda e o texto que fica gravado."""
import json

import pytest
from fastapi import HTTPException

from api.services.parametros import CATALOGO, normalizar


def erro(chave, valor):
    with pytest.raises(HTTPException) as e:
        normalizar(chave, valor)
    return e.value.status_code, e.value.detail


def test_chave_desconhecida_e_404():
    assert erro("nao_existe", "1") == (404, "Parâmetro desconhecido.")


@pytest.mark.parametrize("vazio", [None, "", []])
def test_vazio_limpa_o_parametro(vazio):
    assert normalizar("loja_nome", vazio) is None


def test_formas_ordena_pela_ordem_do_catalogo_nao_alfabetica():
    assert json.loads(normalizar("formas_pagamento_aceitas", ["debito", "credito", "pix"])) == ["pix", "credito", "debito"]


@pytest.mark.parametrize("valor,msg", [(["pix", "pix"], "Forma de pagamento inválida ou repetida."),
                                       (["cheque"], "Forma de pagamento inválida ou repetida."),
                                       ("pix", "Informe a lista de formas de pagamento."),
                                       ([1], "Informe a lista de formas de pagamento.")])
def test_formas_invalidas(valor, msg):
    assert erro("formas_pagamento_aceitas", valor) == (400, msg)


def test_nao_texto_e_recusado():
    assert erro("loja_nome", 5) == (400, "Valor deve ser texto ou número em texto.")


def test_texto_apara_e_limita():
    assert normalizar("loja_nome", "  Pizzaria  ") == "Pizzaria"
    assert normalizar("loja_nome", "x" * 120) == "x" * 120
    assert erro("loja_nome", "x" * 121) == (400, "Até 120 caracteres.")


def test_regime():
    assert normalizar("regime_tributario", "mei") == "mei"
    assert erro("regime_tributario", "MEI")[0] == 400


@pytest.mark.parametrize("entrada,gravado", [("0", "0.00"), ("100", "100.00"), ("12,5", "12.50"), ("7.125", "7.12")])
def test_pct(entrada, gravado):
    assert normalizar("limite_desconto_atendente_pct", entrada) == gravado


@pytest.mark.parametrize("valor,msg", [("100.01", "Valor fora da faixa permitida."), ("-1", "Número inválido."),
                                       ("1e2", "Número inválido."), ("abc", "Número inválido."), ("１", "Número inválido."),
                                       ("5\n", "Número inválido.")])
def test_pct_fora(valor, msg):
    assert erro("limite_desconto_atendente_pct", valor) == (400, msg)


def test_dinheiro():
    assert normalizar("taxa_entrega_padrao", "8") == "8.00"
    assert normalizar("taxa_entrega_padrao", "999999.99") == "999999.99"
    assert erro("taxa_entrega_padrao", "1000000")[0] == 400


def test_sim_nao_e_tamanho_massa():
    assert normalizar("bi_alerta_cmv", "nao") == "nao"
    assert erro("bi_alerta_cmv", "talvez") == (400, "Informe sim ou nao.")
    assert normalizar("calzone_massa_tamanho", "broto") == "broto"
    assert erro("calzone_massa_tamanho", "media") == (400, "Informe grande ou broto.")


def test_decimal_pos():
    assert normalizar("forno_tempo_min", "2,50") == "2.5"
    assert normalizar("forno_tempo_min", "0.1") == "0.1"
    assert normalizar("forno_tempo_min", "1000") == "1000"
    assert normalizar("forno_tempo_min", "10") == "10"
    assert erro("forno_tempo_min", "0.09")[0] == 400
    assert erro("forno_tempo_min", "1000.1")[0] == 400


def test_inteiro_pos():
    assert normalizar("forno_pizzas_por_vez", "1") == "1"
    assert normalizar("forno_pizzas_por_vez", "4") == "4"
    assert normalizar("forno_pizzas_por_vez", "4,0") == "4"
    assert normalizar("forno_pizzas_por_vez", "1000") == "1000"
    assert erro("forno_pizzas_por_vez", "2.5") == (400, "Informe um número inteiro.")
    assert erro("forno_pizzas_por_vez", "0")[0] == 400
    assert erro("forno_pizzas_por_vez", "1001")[0] == 400


def test_todo_tipo_do_catalogo_tem_regra():
    """Um tipo novo no catálogo sem regra de validação seria recusado sempre; este teste avisa antes."""
    from api.services.parametros import _REGRAS
    assert {t for t, _, _ in CATALOGO.values()} - {"formas"} <= set(_REGRAS)
