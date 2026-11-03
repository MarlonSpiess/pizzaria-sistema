"""Acesso rígido por função (decisão de Marlon, 03/11/2026): cada perfil só lê e só faz o que é da sua tela, e o servidor confere."""
import pytest

from tests.conftest import entrar
from tests.test_producao import _g, _pagar, hs, parametros, fila_limpa  # noqa: F401  (fixtures)
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

# rota -> perfis que PODEM ler (os outros recebem 403)
LEITURAS = {
    "/api/producao/massa": {"massa", "gerente", "subgerente"},
    "/api/producao/pedidos": {"acabamento", "atendente", "gerente", "subgerente"},  # atendente: ponte do Andamento (vendas.ver)
    "/api/producao/motivos": {"massa", "pizzaiolo", "acabamento", "gerente", "subgerente"},
    "/api/producao/fila": {"pizzaiolo", "acabamento", "gerente", "subgerente"},
    "/api/rh/escalados?data=2026-01-05": {"gerente", "subgerente"},
}
PERFIS = ("massa", "pizzaiolo", "acabamento", "atendente", "gerente", "subgerente")


@pytest.fixture
def hs2(client, hs):  # noqa: F811
    return {**hs, "subgerente": entrar(client, "subgerente")[1]}


@pytest.mark.parametrize("rota", sorted(LEITURAS))
def test_leitura_so_para_quem_e_da_tela(client, hs2, rota):
    for perfil in PERFIS:
        r = client.get(rota, headers=hs2[perfil])
        esperado = 200 if perfil in LEITURAS[rota] else 403
        assert r.status_code == esperado, f"{perfil} em {rota}: {r.status_code}"


def test_fila_filtra_situacoes_e_cliente_por_funcao(client, hs, cardapio):  # noqa: F811
    _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    montagem = client.get("/api/producao/fila", headers=hs["pizzaiolo"]).json()
    assert montagem["pizzas"] and montagem["forno"] is None
    assert all("cliente" not in p and p["situacao"] == "na lista" for p in montagem["pizzas"])
    # uma pizza segue até o forno
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"]).status_code == 200
    # o pizzaiolo não enxerga a pizza que está no forno, nem pedindo a situação
    vistas = client.get("/api/producao/fila", headers=hs["pizzaiolo"]).json()["pizzas"]
    assert p["id"] not in [x["id"] for x in vistas]
    for sit in ("no forno", "saiu do forno", "acabada"):
        assert client.get("/api/producao/fila", params={"situacao": sit}, headers=hs["pizzaiolo"]).status_code == 403
    # o acabamento vê a pizza do forno, com cliente e estado do forno, mas não a montagem
    ac = client.get("/api/producao/fila", headers=hs["acabamento"]).json()
    achada = [x for x in ac["pizzas"] if x["id"] == p["id"]]
    assert achada and "cliente" in achada[0] and ac["forno"] is not None
    assert all(x["situacao"] in ("no forno", "saiu do forno") for x in ac["pizzas"])
    assert client.get("/api/producao/fila", params={"situacao": "na lista"}, headers=hs["acabamento"]).status_code == 403
    # a gerência vê tudo, e o atendente não lê a fila
    ger = client.get("/api/producao/fila", headers=hs["gerente"]).json()
    assert {"na lista", "no forno"} <= {x["situacao"] for x in ger["pizzas"]} and ger["forno"] is not None
    assert client.get("/api/producao/fila", headers=hs["atendente"]).status_code == 403


def test_acoes_de_producao_so_da_funcao(client, hs):  # noqa: F811
    acoes = {"/api/producao/pizzas/proxima": {"pizzaiolo", "gerente"},
             "/api/producao/pizzas/999999/produzida": {"pizzaiolo", "gerente"},
             "/api/producao/pizzas/999999/saiu-do-forno": {"acabamento", "gerente"},
             "/api/producao/pizzas/999999/acabada": {"acabamento", "gerente"}}
    for rota, quem in acoes.items():
        for perfil in ("massa", "pizzaiolo", "acabamento", "atendente"):
            if perfil not in quem:
                assert client.post(rota, headers=hs[perfil]).status_code == 403, f"{perfil} em {rota}"


@pytest.mark.parametrize("perfil", ["massa", "pizzaiolo", "acabamento"])
@pytest.mark.parametrize("rota", ["/api/pedidos", "/api/produtos", "/api/clientes", "/api/entregadores",
                                  "/api/caixa/hoje", "/api/caixa/entregas", "/api/rh/funcionarios", "/api/auditoria", "/api/bi/painel"])
def test_funcoes_de_producao_nao_leem_outras_areas(client, hs, perfil, rota):  # noqa: F811
    assert client.get(rota, headers=hs[perfil]).status_code == 403, f"{perfil} em {rota}"


@pytest.mark.parametrize("rota", ["/api/auditoria", "/api/bi/painel", "/api/rh/funcionarios", "/api/estoque/itens", "/api/compras/fornecedores"])
def test_atendente_nao_le_o_administrativo(client, hs, rota):  # noqa: F811
    assert client.get(rota, headers=hs["atendente"]).status_code == 403


def test_motivos_so_da_lista_que_a_funcao_usa(client, hs):  # noqa: F811
    massa = client.get("/api/producao/motivos", headers=hs["massa"]).json()
    assert massa["retrocesso"] == [] and massa["perda"]
    pizzaiolo = client.get("/api/producao/motivos", headers=hs["pizzaiolo"]).json()
    assert pizzaiolo["retrocesso"] and pizzaiolo["perda"]
    acabamento = client.get("/api/producao/motivos", headers=hs["acabamento"]).json()
    assert acabamento["retrocesso"] == [] and acabamento["perda"]
    gerente = client.get("/api/producao/motivos", headers=hs["gerente"]).json()
    assert gerente["retrocesso"] and gerente["perda"]


def test_forno_com_pizza_real_so_o_acabamento_opera(client, hs, cardapio):  # noqa: F811
    _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"]).status_code == 200
    for perfil in ("pizzaiolo", "massa", "atendente"):
        assert client.post(f"/api/producao/pizzas/{p['id']}/saiu-do-forno", headers=hs[perfil]).status_code == 403
    assert client.post(f"/api/producao/pizzas/{p['id']}/saiu-do-forno", headers=hs["acabamento"]).status_code == 200
