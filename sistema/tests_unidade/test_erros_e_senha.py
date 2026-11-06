"""Tradução dos erros do banco para o cliente, valores em reais e hash de senha."""
from decimal import Decimal

import psycopg.errors
import pytest

from api.database import traduzir_erro
from api.security import hash_senha, verificar_senha
from api.services.dinheiro import fmt, parse_reais


@pytest.mark.parametrize("erro,status,msg", [
    (psycopg.errors.UniqueViolation, 409, "Já existe um registro com esses dados."),
    (psycopg.errors.ForeignKeyViolation, 400, "Referência inválida: registro relacionado não encontrado."),
    (psycopg.errors.CheckViolation, 400, "Valor fora do domínio permitido para este campo."),
    (psycopg.errors.NotNullViolation, 400, "Campo obrigatório não informado."),
    (psycopg.errors.NumericValueOutOfRange, 400, "Dado inválido para este campo."),
    (psycopg.errors.ExclusionViolation, 400, "Operação viola uma regra de integridade do banco."),
])
def test_traduzir_erro(erro, status, msg):
    h = traduzir_erro(erro())
    assert (h.status_code, h.detail) == (status, msg)


def test_gatilho_do_banco_vira_409_e_nao_500():
    """QA cego A14: RAISE EXCEPTION dos gatilhos (P0001) caía no erro geral 500."""
    h = traduzir_erro(psycopg.errors.RaiseException())
    assert (h.status_code, h.detail) == (409, "Operação recusada pelas regras do banco.")


def test_erro_que_nao_e_de_dado_segue_adiante():
    with pytest.raises(psycopg.OperationalError):
        traduzir_erro(psycopg.OperationalError("caiu"))


def test_hash_de_senha_confere_e_nao_guarda_a_senha():
    h = hash_senha("senha-forte-1")
    assert h.startswith("$2") and "senha-forte-1" not in h
    assert verificar_senha("senha-forte-1", h)
    assert not verificar_senha("senha-forte-2", h)
    assert hash_senha("senha-forte-1") != h  # sal novo a cada vez
    assert not verificar_senha("x", "isto não é hash")


def test_fmt_e_parse_reais():
    assert fmt(None) is None
    assert fmt(Decimal("35")) == "35.00"
    assert fmt("1000000") == "1000000.00"
    assert parse_reais(" 35,5 ") == Decimal("35.50")
    for ruim in ("-1", "1e2", "35,555", "", 35):
        with pytest.raises(ValueError, match="^Valor em reais inválido. Use números, com ponto ou vírgula e até 2 casas.$"):
            parse_reais(ruim)
