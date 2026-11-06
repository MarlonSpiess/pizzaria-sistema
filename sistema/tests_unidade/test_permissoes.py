"""Matriz de permissões: regras de acesso rígido por função decididas por Marlon, e coerência com as rotas."""
import re
from pathlib import Path

from api.security import PERMISSOES, tem_permissao

API = Path(__file__).resolve().parent.parent / "api"
SO_DONO = {"usuarios.gerir", "parametros.editar", "canais.configurar", "contas.aprovar", "imobilizado.aprovar", "rh.salarios"}


def test_administrador_e_proprietario_tem_tudo():
    assert PERMISSOES["administrador"] == PERMISSOES["proprietario"]
    todas = set().union(*PERMISSOES.values())
    assert PERMISSOES["administrador"] == todas


def test_subgerente_e_gerente_menos_aprovar_caixa_e_rh():
    assert PERMISSOES["gerente"] - PERMISSOES["subgerente"] == {"caixa.aprovar", "rh.aprovar"}
    assert PERMISSOES["subgerente"] <= PERMISSOES["gerente"]


def test_gerencia_nao_tem_o_que_e_so_do_dono():
    assert not PERMISSOES["gerente"] & SO_DONO
    assert PERMISSOES["administrador"] - PERMISSOES["gerente"] == SO_DONO


def test_funcoes_de_producao_e_atendente():
    assert PERMISSOES["massa"] == {"rh.proprio", "producao.massa", "producao.perda_massa"}
    assert PERMISSOES["pizzaiolo"] == {"rh.proprio", "producao.montagem", "producao.perda"}
    assert PERMISSOES["acabamento"] == {"rh.proprio", "entregas.despachar", "producao.forno", "producao.acabamento",
                                        "producao.perda", "producao.refazer"}
    assert PERMISSOES["atendente"] == {"rh.proprio", "cardapio.ver", "clientes.ver", "clientes.editar", "entregadores.ver",
                                       "vendas.ver", "vendas.criar", "caixa.ver", "caixa.operar"}


def test_matriz_imutavel():
    """Perfis que compartilham o mesmo conjunto não podem ser alterados um pelo outro em tempo de execução."""
    assert all(isinstance(p, frozenset) for p in PERMISSOES.values())


def test_tem_permissao():
    assert tem_permissao({"perfil": "gerente"}, "caixa.aprovar")
    assert not tem_permissao({"perfil": "subgerente"}, "caixa.aprovar")
    assert not tem_permissao({"perfil": "desconhecido"}, "caixa.ver")


def test_toda_permissao_citada_no_codigo_existe():
    """Um erro de digitação em requer("...") negaria a rota a todos sem nenhum aviso."""
    citadas = set()
    for arq in API.rglob("*.py"):
        texto = arq.read_text(encoding="utf-8")
        for chamada in re.findall(r"(?:requer|requer_alguma|tem_permissao)\(([^)]*)\)", texto):
            citadas |= set(re.findall(r'"([a-z_]+\.[a-z_.]+)"', chamada))
    assert citadas, "nenhuma permissão encontrada: o padrão de busca quebrou"
    assert citadas <= PERMISSOES["administrador"], citadas - PERMISSOES["administrador"]
