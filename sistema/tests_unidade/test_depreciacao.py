"""Depreciação em linha reta: a soma das parcelas é exatamente o valor depreciável (QA cego C3, 23/11/2026)."""
from datetime import date
from decimal import Decimal

import pytest

from api.services.imobilizado import parcelas


def _bem(valor, meses, residual="0.00"):
    return {"inicio_uso": date(2026, 1, 1), "metodo": "vida_util", "vida_util_meses": meses,
            "valor_aquisicao": Decimal(valor), "valor_residual": Decimal(residual)}


@pytest.mark.parametrize("valor,meses,residual", [("13.00", 120, "0.00"), ("100.00", 600, "0.00"), ("1000.00", 60, "100.00"),
                                                  ("0.07", 12, "0.00"), ("3599.99", 7, "0.10")])
def test_soma_das_parcelas_e_a_base(valor, meses, residual):
    p = parcelas(_bem(valor, meses, residual), None)
    assert sum(v for _, v in p) == Decimal(valor) - Decimal(residual)
    assert all(v > 0 for _, v in p)


def test_parcelas_iguais_quando_divide_exato_e_mes_a_mes():
    p = parcelas(_bem("1200.00", 12), None)
    assert [v for _, v in p] == [Decimal("100.00")] * 12
    assert p[0][0] == date(2026, 1, 1) and p[-1][0] == date(2026, 12, 1)


def test_ate_corta_no_mes():
    assert len(parcelas(_bem("1200.00", 12), None, ate=date(2026, 3, 1))) == 3
