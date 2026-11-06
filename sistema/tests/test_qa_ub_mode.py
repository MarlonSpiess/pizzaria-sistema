"""Regressões dos achados do QA cego da revisão ub-mode (06/11/2026)."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from tests.conftest import entrar, novo_login
from tests.test_fichas import _item
from tests.test_producao import PARAMS, _g, _motivos, _pagar
from tests.test_vendas import cardapio  # noqa: F401  (fixture)


@pytest.fixture(scope="module", autouse=True)
def parametros(client):
    _, h = entrar(client, "administrador")
    for k, v in PARAMS.items():
        assert client.put(f"/api/parametros/{k}", json={"valor": v}, headers=h).status_code == 200
    assert client.post("/api/producao/motivos/iniciar-padrao", headers=h).status_code in (201, 409)
    yield


@pytest.fixture(autouse=True)
def fila_limpa(conn_teste):
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'cancelada' WHERE situacao IN ('na lista','em montagem','no forno','saiu do forno')")
    yield


@pytest.fixture
def hs(client):
    return {p: entrar(client, p)[1] for p in ("atendente", "gerente", "subgerente", "pizzaiolo", "acabamento", "administrador")}


def test_pizzaiolo_nao_perde_pizza_que_ja_saiu_da_montagem(client, cardapio, hs):
    """A2: pizzaiolo só montagem. Pizza no forno é do acabamento."""
    m = _motivos(client, hs["gerente"])
    _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    p1 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p1['id']}/produzida", headers=hs["pizzaiolo"]).status_code == 200
    r = client.post(f"/api/producao/pizzas/{p1['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"])
    assert r.status_code == 403
    assert client.post(f"/api/producao/pizzas/{p1['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["acabamento"]).status_code == 200
    p2 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()  # em montagem: o próprio pizzaiolo perde
    assert client.post(f"/api/producao/pizzas/{p2['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 200


def test_transferencia_nao_deixa_o_local_de_origem_negativo(client, hs):
    """A5: estoque pode ficar negativo pela baixa, a transferência não. A falta sem lote conta no saldo do local."""
    h = hs["gerente"]
    it = _item(client, h, "insumo", "kg")
    a = client.post("/api/estoque/locais", json={"nome": novo_login("LocA")}, headers=h).json()["id"]
    b = client.post("/api/estoque/locais", json={"nome": novo_login("LocB")}, headers=h).json()["id"]
    mov = lambda **kw: client.post("/api/estoque/movimentos", json={"item_id": it["id"], **kw}, headers=h)  # noqa: E731
    assert mov(tipo="entrada_inicial", quantidade="10", custo_unit="1", motivo="ini", local_id=a, lote_codigo="L1").status_code == 201
    assert mov(tipo="perda", quantidade="15", motivo="caiu", local_id=a).status_code == 201  # A fica em -5
    assert mov(tipo="entrada_inicial", quantidade="10", custo_unit="1", motivo="ini", local_id=a, lote_codigo="L2").status_code == 201  # A = 5
    assert mov(tipo="entrada_inicial", quantidade="10", custo_unit="1", motivo="ini", local_id=b, lote_codigo="L3").status_code == 201
    r = mov(tipo="transferencia", quantidade="10", local_id=a, destino_id=b)
    assert r.status_code == 400 and "neste local" in r.json()["detail"]
    assert mov(tipo="transferencia", quantidade="5", local_id=a, destino_id=b).status_code == 201
    por_local = {x["local_id"]: D(x["saldo"]) for x in client.get(f"/api/estoque/itens/{it['id']}", headers=h).json()["por_local"]}
    assert por_local.get(a, 0) == 0 and por_local[b] == 15


def test_sangrias_simultaneas_nao_furam_o_limite_acumulado(client, conn_teste):
    """A6: dois terminais com sangria de R$ 90 e limite acumulado de R$ 100: só uma passa sem gerente."""
    import os
    import threading
    import time

    import psycopg

    from tests.conftest import BASE
    ha = entrar(client, "administrador")[1]
    client.post("/api/caixa/motivos/iniciar-padrao", headers=ha)
    mot = next(m for m in client.get("/api/caixa/motivos", headers=ha).json() if m["tipo"] == "sangria" and not m["vira_despesa"])
    st = client.get("/api/caixa/hoje", headers=ha).json()
    if not st.get("caixa") or st["caixa"]["situacao"] != "aberto":
        assert client.post("/api/caixa/abrir", json={"fundo_troco": "200,00"}, headers=ha).status_code == 201
    ja = conn_teste.execute("SELECT COALESCE(sum(valor), 0) FROM movimento_caixa WHERE tipo = 'sangria' AND autorizado_por IS NULL "
                            "AND data = current_date").fetchone()[0]  # outras sangrias do dia na suíte
    assert client.put("/api/parametros/sangria_limite_gerente", json={"valor": f"{ja + 100:.2f}"}, headers=ha).status_code == 200
    hs = [entrar(client, "atendente")[1] for _ in range(2)]
    res = []
    trava = psycopg.connect(dbname=os.environ["DB_NAME"], **BASE)
    trava.execute("LOCK TABLE movimento_caixa IN SHARE MODE")  # alarga a janela entre a soma e a inserção
    ts = [threading.Thread(target=lambda h=h: res.append(client.post("/api/caixa/movimentos", json={
        "tipo": "sangria", "motivo_id": mot["id"], "valor": "90,00"}, headers=h).status_code)) for h in hs]
    [t.start() for t in ts]
    time.sleep(0.8)
    trava.rollback()
    trava.close()
    [t.join(15) for t in ts]
    assert sorted(res) == [201, 403]


def test_folha_nao_aparece_para_o_gerente_na_conciliacao_nem_na_auditoria(client):
    """A1: só administrador e proprietário veem salários; a baixa do título da folha também é salário."""
    ha, hg = entrar(client, "administrador")[1], entrar(client, "gerente")[1]
    client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=hg)
    assert client.post("/api/contas/tipos-despesa", json={"nome": "Folha de pagamento", "natureza": "pessoal"}, headers=ha).status_code in (201, 409)
    client.post("/api/rh/iniciar-padrao", headers=hg)
    funcao = client.get("/api/rh/funcoes", headers=hg).json()[0]["id"]
    fid = client.post("/api/rh/funcionarios", json={"nome": novo_login("Sal"), "funcao_id": funcao,
                                                    "admissao": str(date.today() - timedelta(days=400))}, headers=hg).json()["id"]
    assert client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "forma_pagamento": "mensal", "valor": "4321,00",
                                                                     "vigente_desde": str(date.today() - timedelta(days=300))}, headers=ha).status_code == 201
    mes = (date.today().replace(day=1) - timedelta(days=100)).strftime("%Y-%m")  # mês que nenhum outro teste lança
    r = client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=ha)
    assert r.status_code == 201, r.text
    tid = r.json()["titulo_id"]
    conta = client.post("/api/contas/contas-bancarias", json={"nome": novo_login("Bco"), "saldo_inicial": "0",
                                                              "saldo_inicial_data": str(date.today() - timedelta(days=60))}, headers=ha).json()["id"]
    assert client.post(f"/api/contas/titulos/{tid}/baixas", json={"conta_id": conta, "forma": "pix"}, headers=ha).status_code == 201
    assert client.get(f"/api/contas/conciliacao/{conta}", headers=hg).json()["baixas"] == []
    assert len(client.get(f"/api/contas/conciliacao/{conta}", headers=ha).json()["baixas"]) == 1
    aud_g = client.get("/api/auditoria", params={"entidade": "titulo", "limite": 500}, headers=hg).json()["data"]
    assert not [a for a in aud_g if str(a["entidade_id"]) == str(tid)]
    aud_a = client.get("/api/auditoria", params={"entidade": "titulo", "limite": 500}, headers=ha).json()["data"]
    assert [a for a in aud_a if str(a["entidade_id"]) == str(tid) and a["acao"] == "baixar"]


def test_relatorio_de_data_sem_caixa_e_404(client):
    """A13: antes devolvia o caixa de hoje com a data de hoje."""
    r = client.get("/api/caixa/2020-01-01/relatorio", headers=entrar(client, "gerente")[1])
    assert r.status_code == 404
