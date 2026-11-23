"""Frete rateado no custo de entrada (C14) e folha mensal proporcional (C15), sem banco."""
from datetime import date
from decimal import Decimal as D

from api.routers.compras import _custos_com_frete
from api.routers.rh import _mensal_proporcional


def _linha(qtd, unit):
    return ({"id": 0}, D(qtd), D(unit), (D(qtd) * D(unit)).quantize(D("0.01")), None, None)


def test_frete_rateado_pelo_valor():
    linhas = [_linha("10", "3.00"), _linha("2", "10.00")]  # 30 + 20 = 50
    custos = _custos_com_frete(linhas, D("10.00"), D("0"))
    assert custos == [D("3.600000"), D("12.000000")]  # 30 + 6 = 36 / 10; 20 + 4 = 24 / 2
    assert sum(c * l[1] for c, l in zip(custos, linhas)) == D("60.00")


def test_desconto_e_centavo_no_ultimo_item():
    linhas = [_linha("3", "1.00"), _linha("3", "1.00"), _linha("3", "1.00")]
    custos = _custos_com_frete(linhas, D("1.00"), D("0"))  # 0,33 + 0,33 + 0,34
    assert sum(c * l[1] for c, l in zip(custos, linhas)).quantize(D("0.01")) == D("10.00")
    custos = _custos_com_frete(linhas, D("0"), D("3.00"))
    assert custos == [D("0.666667")] * 3


def test_sem_frete_mantem_o_preco():
    linhas = [_linha("2", "4.50")]
    assert _custos_com_frete(linhas, D("0"), D("0")) == [D("4.50")]


def test_folha_mes_inteiro_e_proporcional():
    ini, prox = date(2026, 3, 1), date(2026, 4, 1)
    assert _mensal_proporcional(D("3000"), date(2025, 1, 10), None, ini, prox) == D("3000")  # mês cheio, mesmo com 31 dias
    assert _mensal_proporcional(D("3000"), date(2026, 3, 16), None, ini, prox) == D("1600.00")  # 16 dias (16 a 31)
    assert _mensal_proporcional(D("3000"), date(2025, 1, 10), date(2026, 3, 10), ini, prox) == D("1000.00")  # 10 dias
    fev, mar = date(2026, 2, 1), date(2026, 3, 1)
    assert _mensal_proporcional(D("3000"), date(2025, 1, 10), None, fev, mar) == D("3000")  # fevereiro cheio
    assert _mensal_proporcional(D("3000"), date(2026, 2, 15), None, fev, mar) == D("1400.00")  # 14 dias


def test_rateio_cumulativo_nao_joga_o_erro_no_ultimo():
    linhas = [_linha("1", "0.01") for _ in range(21)]  # 21 itens de 0,01 e desconto de 0,15
    custos = _custos_com_frete(linhas, D("0"), D("0.15"))
    assert max(custos) <= D("0.01") and sum(custos) == D("0.06")  # 0,21 − 0,15; nenhum item recebe a sobra dos outros
