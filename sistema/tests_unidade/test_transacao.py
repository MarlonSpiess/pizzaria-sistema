"""transacao(): o bloco de gravação comum a todas as rotas."""
import psycopg.errors
import pytest
from fastapi import HTTPException

from api.database import transacao


class Conexao:
    def __init__(self):
        self.eventos = []

    def commit(self):
        self.eventos.append("commit")

    def rollback(self):
        self.eventos.append("rollback")


def test_sem_erro_comita():
    c = Conexao()
    with transacao(c):
        pass
    assert c.eventos == ["commit"]


def test_violacao_de_unicidade_desfaz_e_vira_409():
    c = Conexao()
    with pytest.raises(HTTPException) as e:
        with transacao(c):
            raise psycopg.errors.UniqueViolation()
    assert c.eventos == ["rollback"] and e.value.status_code == 409


def test_regra_de_negocio_no_meio_nao_comita():
    c = Conexao()
    with pytest.raises(HTTPException):
        with transacao(c):
            raise HTTPException(status_code=409, detail="x")
    assert "commit" not in c.eventos


def test_erro_de_banco_desconhecido_desfaz_e_segue_adiante():
    c = Conexao()
    with pytest.raises(psycopg.OperationalError):
        with transacao(c):
            raise psycopg.OperationalError("caiu")
    assert c.eventos == ["rollback"]
