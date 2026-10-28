import os
from datetime import date, timedelta
from decimal import Decimal

import psycopg
import pytest

from tests.conftest import BASE, entrar, novo_login
from tests.test_estoque_compras import _inicial  # noqa: F401
from tests.test_fichas import _item

D = Decimal
TABELAS = "conciliacao, extrato_linha, os_peca, ordem_servico, leitura_bem, limite_leitura, plano_manutencao, conferencia_bem, depreciacao_bem, baixa_bem, titulo, baixa_titulo, bem, categoria_bem"


def _limpar():
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        c.execute("SET session_replication_role = replica")
        c.execute(f"TRUNCATE {TABELAS}")


@pytest.fixture(scope="module", autouse=True)
def ambiente(client):
    _limpar()
    _, h = entrar(client, "administrador")
    client.put("/api/parametros/bem_valor_minimo", json={"valor": "500,00"}, headers=h)
    client.put("/api/parametros/manutencao_valor_aprovacao", json={"valor": "300,00"}, headers=h)
    yield
    client.put("/api/parametros/bem_valor_minimo", json={"valor": None}, headers=h)
    client.put("/api/parametros/manutencao_valor_aprovacao", json={"valor": None}, headers=h)
    _limpar()


@pytest.fixture(scope="module")
def base(client):
    hg, ha, hs, hat = (entrar(client, p)[1] for p in ("gerente", "administrador", "subgerente", "atendente"))
    assert client.post("/api/imobilizado/categorias/iniciar-padrao", headers=hg).status_code == 201
    assert client.post("/api/imobilizado/categorias/iniciar-padrao", headers=hg).status_code == 409
    cats = {c["nome"]: c["id"] for c in client.get("/api/imobilizado/categorias", headers=hg).json()}
    return {"hg": hg, "ha": ha, "hs": hs, "hat": hat, "cats": cats}


def _bem(client, b, **kw):
    corpo = {"codigo": novo_login("BEM"), "nome": "Forno esteira", "categoria_id": b["cats"]["Máquinas e equipamentos"], "valor_aquisicao": "12000,00",
             "data_aquisicao": str(date.today() - timedelta(days=400)), **kw}
    r = client.post("/api/imobilizado/bens", json=corpo, headers=b["hg"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_permissoes_e_valor_minimo(client, base):
    assert client.get("/api/imobilizado/bens", headers=base["hat"]).status_code == 403
    assert client.get("/api/imobilizado/bens", headers=base["hs"]).status_code == 200
    r = client.post("/api/imobilizado/bens", json={"codigo": "X1", "nome": "Panela", "categoria_id": base["cats"]["Móveis e utensílios"], "valor_aquisicao": "100,00", "data_aquisicao": str(date.today())}, headers=base["hg"])
    assert r.status_code == 400 and "uso e consumo" in r.json()["detail"]
    c = {"codigo": "DUP-1", "nome": "Freezer", "categoria_id": base["cats"]["Móveis e utensílios"], "valor_aquisicao": "2000,00", "data_aquisicao": str(date.today())}
    assert client.post("/api/imobilizado/bens", json=c, headers=base["hg"]).status_code == 201
    assert client.post("/api/imobilizado/bens", json={**c, "codigo": "dup-1"}, headers=base["hg"]).status_code == 409  # plaqueta única
    assert client.post("/api/imobilizado/bens", json={**c, "codigo": "R1", "valor_residual": "2000,00"}, headers=base["hg"]).status_code == 400


def test_depreciacao_linha_reta_fiscal_e_por_vida_util(client, base):
    hoje = date.today()
    ini = (hoje.replace(day=1) - timedelta(days=100)).replace(day=1)  # começou há ~3 a 4 meses
    b = _bem(client, base, inicio_uso=str(ini), valor_aquisicao="12000,00")  # 10% a.a.: 120 meses, R$ 100 por mês
    x = client.get(f"/api/imobilizado/bens/{b}", headers=base["hg"]).json()
    meses = (hoje.year - ini.year) * 12 + hoje.month - ini.month + 1
    assert x["vida_meses"] == 120 and x["depreciacao_acumulada"] == f"{100 * meses}.00" and x["valor_contabil"] == f"{12000 - 100 * meses}.00"
    assert client.get(f"/api/imobilizado/bens/{b}", headers=base["hg"]).json()["depreciacao_acumulada"] == x["depreciacao_acumulada"]  # idempotente
    v = _bem(client, base, inicio_uso=str(ini), valor_aquisicao="1000,00", valor_residual="100,00", metodo="vida_util", vida_util_meses=9)  # (1000-100)/9 = 100
    assert client.get(f"/api/imobilizado/bens/{v}", headers=base["hg"]).json()["depreciacao_acumulada"] == f"{100 * meses}.00"
    # depois que começou, os parâmetros da depreciação não mudam; o resto sim
    assert client.patch(f"/api/imobilizado/bens/{b}", json={"valor_residual": "50,00"}, headers=base["hg"]).status_code == 409
    assert client.patch(f"/api/imobilizado/bens/{b}", json={"responsavel": "Maria"}, headers=base["hg"]).status_code == 200
    # a depreciação aparece nos Custos como custo fixo do mês
    r = client.get("/api/custos/resultado", headers=base["hg"]).json()
    assert D(r["fixos_detalhe"]["depreciacao"]) >= D("200.00")


def test_bem_sem_inicio_de_uso_nao_deprecia_e_ultima_parcela_fecha(client, base):
    b = _bem(client, base)
    assert client.get(f"/api/imobilizado/bens/{b}", headers=base["hg"]).json()["depreciacao_acumulada"] == "0.00"
    from api.services.imobilizado import parcelas
    bem = {"inicio_uso": date(2026, 1, 15), "valor_aquisicao": D("1000.00"), "valor_residual": D("0"), "metodo": "vida_util", "vida_util_meses": 3}
    ps = parcelas(bem, D("10"))
    assert [v for _, v in ps] == [D("333.33"), D("333.33"), D("333.34")] and ps[0][0] == date(2026, 1, 1) and sum(v for _, v in ps) == D("1000.00")


def test_baixa_so_do_aprovador_e_para_a_depreciacao(client, base):
    hoje = date.today()
    ini = hoje.replace(day=1) - timedelta(days=62)
    b = _bem(client, base, inicio_uso=str(ini.replace(day=1)), valor_aquisicao="6000,00")
    body = {"tipo": "descarte", "data": str(hoje - timedelta(days=40)), "valor": "0", "motivo": "Quebrou sem conserto"}
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json=body, headers=base["hg"]).status_code == 403
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json={**body, "data": str(hoje + timedelta(days=1))}, headers=base["ha"]).status_code == 400
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json={**body, "data": "2000-01-01"}, headers=base["ha"]).status_code == 400
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json=body, headers=base["ha"]).status_code == 201
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json=body, headers=base["ha"]).status_code == 409
    x = client.get(f"/api/imobilizado/bens/{b}", headers=base["hg"]).json()
    assert x["situacao"] == "baixado" and x["baixa"]["tipo"] == "descarte"
    ate = (hoje - timedelta(days=40)).replace(day=1)
    meses = (ate.year - ini.year) * 12 + ate.month - ini.replace(day=1).month + 1
    assert x["depreciacao_acumulada"] == f"{50 * meses}.00"  # 6000 / 120 = 50 por mês, até o mês da baixa
    assert client.patch(f"/api/imobilizado/bens/{b}", json={"responsavel": "Z"}, headers=base["hg"]).status_code == 409


def test_conferencia_plano_leitura_e_alertas(client, base):
    hoje = date.today()
    b = _bem(client, base, critico=True, garantia_ate=str(hoje + timedelta(days=10)), seguro_ate=str(hoje - timedelta(days=1)))
    h = base["hg"]
    p = client.post(f"/api/imobilizado/bens/{b}/planos", json={"tarefa": "Limpeza do forno", "periodicidade_dias": 30, "antecedencia_dias": 5, "base_em": str(hoje - timedelta(days=27))}, headers=h)
    assert p.status_code == 201
    pl = next(x for x in client.get("/api/imobilizado/planos", headers=h).json() if x["id"] == p.json()["id"])
    assert pl["situacao"] == "a vencer" and pl["proximo"] == str(hoje + timedelta(days=3))
    assert client.put(f"/api/imobilizado/bens/{b}/limites", json={"grandeza": "Temperatura", "unidade": "C", "minimo": "250", "maximo": "300"}, headers=h).status_code == 200
    assert client.put(f"/api/imobilizado/bens/{b}/limites", json={"grandeza": "X", "minimo": "9", "maximo": "1"}, headers=h).status_code == 400
    assert client.post(f"/api/imobilizado/bens/{b}/leituras", json={"grandeza": "Temperatura", "valor": "280"}, headers=h).json()["fora_do_normal"] is False
    assert client.post(f"/api/imobilizado/bens/{b}/leituras", json={"grandeza": "Temperatura", "valor": "340,5"}, headers=h).json()["fora_do_normal"] is True
    assert client.post(f"/api/imobilizado/bens/{b}/leituras", json={"grandeza": "Temperatura", "valor": "1", "data": str(hoje + timedelta(days=2))}, headers=h).status_code == 400
    al = client.get("/api/imobilizado/alertas", headers=h).json()
    assert any(x["id"] == p.json()["id"] for x in al["planos"])
    assert {(v["id"], v["o_que"]) for v in al["garantias_e_seguros"]} >= {(b, "garantia"), (b, "seguro")}
    assert any(l["bem_id"] == b and l["grandeza"] == "Temperatura" for l in al["leituras_fora"])
    # conferência: bem não encontrado fica pendente no inventário
    assert client.post(f"/api/imobilizado/bens/{b}/conferencias", json={"encontrado": False, "observacao": "Não achei"}, headers=h).status_code == 201
    assert next(i for i in client.get("/api/imobilizado/inventario", headers=h).json() if i["id"] == b)["pendente"] is True
    assert client.post(f"/api/imobilizado/bens/{b}/conferencias", json={"encontrado": True, "local_encontrado": "Cozinha"}, headers=h).status_code == 201
    assert next(i for i in client.get("/api/imobilizado/inventario", headers=h).json() if i["id"] == b)["local_texto"] == "Cozinha"


def test_ordem_de_servico_completa_com_peca_aprovacao_e_titulo(client, base, conn_teste):
    h, ha, hoje = base["hg"], base["ha"], date.today()
    b = _bem(client, base, critico=True)
    p = client.post(f"/api/imobilizado/bens/{b}/planos", json={"tarefa": "Revisão", "periodicidade_dias": 90, "base_em": str(hoje - timedelta(days=90))}, headers=h).json()["id"]
    peca = _item(client, h, "consumo", "un")
    _inicial(client, h, peca["id"], "10", "50,00")
    o = client.post("/api/imobilizado/os", json={"bem_id": b, "tipo": "preventiva", "plano_id": p, "descricao": "Revisão geral", "parou": True}, headers=h).json()
    assert o["situacao"] == "aberta" and o["parada_inicio"]
    parados = client.get("/api/imobilizado/alertas", headers=h).json()["bens_criticos_parados"]
    assert any(x["os_id"] == o["id"] for x in parados)
    assert client.post(f"/api/imobilizado/os/{o['id']}/fechar", json={"servico_feito": "x"}, headers=h).status_code == 409  # não iniciada
    assert client.post(f"/api/imobilizado/os/{o['id']}/iniciar", json={"executor_tipo": "terceiro"}, headers=h).status_code == 400
    forn = client.post("/api/compras/fornecedores", json={"nome": novo_login("Tec")}, headers=h).json()
    assert client.post(f"/api/imobilizado/os/{o['id']}/iniciar", json={"executor_tipo": "terceiro", "fornecedor_id": forn["id"]}, headers=h).status_code == 200
    # peça só da classe consumo; sai do estoque pelo custo médio
    insumo = _item(client, h, "insumo", "g")
    assert client.post(f"/api/imobilizado/os/{o['id']}/pecas", json={"item_id": insumo["id"], "quantidade": "1"}, headers=h).status_code == 404
    r = client.post(f"/api/imobilizado/os/{o['id']}/pecas", json={"item_id": peca["id"], "quantidade": "2"}, headers=h).json()
    assert r["custo_pecas"] == "100.00"
    assert D(client.get(f"/api/estoque/itens/{peca['id']}", headers=h).json()["saldo"]) == 8
    # custo total 100 + 400 = 500 > 300: precisa de aprovação de quem não abriu
    fechar = {"servico_feito": "Trocou resistência", "causa": "Desgaste", "mao_obra": "400,00"}
    assert client.post(f"/api/imobilizado/os/{o['id']}/fechar", json=fechar, headers=h).status_code == 409
    assert client.post(f"/api/imobilizado/os/{o['id']}/aprovar", headers=h).status_code == 403  # gerente não aprova
    assert any(a["id"] == o["id"] for a in client.get("/api/imobilizado/alertas", headers=h).json()["ordens_aguardando_aprovacao"])
    assert client.post(f"/api/imobilizado/os/{o['id']}/aprovar", headers=ha).status_code == 200
    # a aprovação vale só até o valor aprovado: custo maior exige nova aprovação
    assert client.post(f"/api/imobilizado/os/{o['id']}/fechar", json=fechar | {"mao_obra": "50000,00"}, headers=h).status_code == 409
    assert client.post(f"/api/imobilizado/os/{o['id']}/aprovar", headers=ha).status_code == 200
    # terceiro com mão de obra precisa de tipo de despesa (ou o tipo "Manutenção" cadastrado)
    assert client.post(f"/api/imobilizado/os/{o['id']}/fechar", json=fechar, headers=h).status_code == 400
    client.post("/api/contas/tipos-despesa", json={"nome": "Manutenção", "natureza": "fixa"}, headers=h)
    f = client.post(f"/api/imobilizado/os/{o['id']}/fechar", json=fechar, headers=h)
    assert f.status_code == 200 and f.json()["situacao"] == "fechada" and f.json()["custo_total"] == "500.00" and f.json()["parada_minutos"] is not None
    assert client.post(f"/api/imobilizado/os/{o['id']}/cancelar", headers=h).status_code == 409
    # plano ficou em dia e a mão de obra do terceiro virou conta a pagar ligada ao bem
    assert next(x for x in client.get("/api/imobilizado/planos", headers=h).json() if x["id"] == p)["situacao"] == "em dia"
    t = next(x for x in client.get("/api/contas/titulos", headers=h).json() if x["origem_tipo"] == "manutencao")
    assert t["valor"] == "400.00" and t["sentido"] == "pagar"
    assert conn_teste.execute("SELECT bem_id FROM titulo WHERE id = %s", (t["id"],)).fetchone()[0] == b
    cm = client.get("/api/imobilizado/custos-manutencao", headers=h).json()
    assert any(x["bem_id"] == b and x["custo"] == "500.00" for x in cm["por_bem"]) and any(x["tipo"] == "preventiva" for x in cm["por_tipo"])
    # bem com ordem em aberto não recebe baixa
    o2 = client.post("/api/imobilizado/os", json={"bem_id": b, "tipo": "corretiva", "descricao": "Quebrou"}, headers=h).json()
    assert client.post(f"/api/imobilizado/bens/{b}/baixa", json={"tipo": "perda", "data": str(hoje), "motivo": "x"}, headers=ha).status_code == 409
    assert client.post(f"/api/imobilizado/os/{o2['id']}/cancelar", headers=h).status_code == 200


def test_gatilhos(client, base, conn_teste):
    b = _bem(client, base)
    with pytest.raises(psycopg.errors.Error):
        conn_teste.execute("UPDATE bem SET valor_aquisicao = 1 WHERE id = %s", (b,))
    with pytest.raises(psycopg.errors.Error):
        conn_teste.execute("DELETE FROM bem WHERE id = %s", (b,))
    with pytest.raises(psycopg.errors.Error):
        conn_teste.execute("DELETE FROM depreciacao_bem")


def test_entradas_extremas_nao_derrubam(client, base):
    h = base["hg"]
    assert client.post("/api/imobilizado/categorias", json={"nome": novo_login("Cat"), "taxa_fiscal_pct": "0,01"}, headers=h).status_code == 422
    assert client.post("/api/imobilizado/categorias", json={"nome": novo_login("Cat"), "taxa_fiscal_pct": "NaN"}, headers=h).status_code == 422
    assert client.get("/api/imobilizado/bens", headers=h).status_code == 200
    assert client.get("/api/custos/resultado?mes=2026-10", headers=h).status_code == 200
