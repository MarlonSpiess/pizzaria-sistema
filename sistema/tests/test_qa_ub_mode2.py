"""Segunda rodada ub-mode (23/11/2026): regressões dos achados do QA não cego (N1 a N3) e do QA cego."""
import os
import threading
import time
from datetime import date, timedelta

import psycopg

from tests.conftest import BASE, entrar, novo_login


def _folha_lancada(client, ha, hg, valor="4321,00", dias_atras=200):
    """Administrador lança a folha de um funcionário com contrato `valor` e devolve (titulo_id, conta_id)."""
    client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=hg)
    client.post("/api/contas/tipos-despesa", json={"nome": "Folha de pagamento", "natureza": "pessoal"}, headers=ha)
    client.post("/api/rh/iniciar-padrao", headers=hg)
    funcao = client.get("/api/rh/funcoes", headers=hg).json()[0]["id"]
    fid = client.post("/api/rh/funcionarios", json={"nome": novo_login("Sal"), "funcao_id": funcao,
                                                    "admissao": str(date.today() - timedelta(days=500))}, headers=hg).json()["id"]
    assert client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "forma_pagamento": "mensal", "valor": valor,
                                                                     "vigente_desde": str(date.today() - timedelta(days=450))}, headers=ha).status_code == 201
    mes = (date.today().replace(day=1) - timedelta(days=dias_atras)).strftime("%Y-%m")
    r = client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=ha)
    assert r.status_code == 201, r.text
    conta = client.post("/api/contas/contas-bancarias", json={"nome": novo_login("Bco"), "saldo_inicial": "0",
                                                              "saldo_inicial_data": str(date.today() - timedelta(days=60))}, headers=ha).json()["id"]
    return r.json()["titulo_id"], conta


def test_N1_gerente_nao_descobre_nem_paga_a_folha_pela_baixa(client):
    """N1: o título da folha some da lista do gerente, mas a rota de baixa aceita o id e a mensagem de erro mostra o saldo (o salário)."""
    ha, hg = entrar(client, "administrador")[1], entrar(client, "gerente")[1]
    tid, conta = _folha_lancada(client, ha, hg, dias_atras=200)
    r = client.post(f"/api/contas/titulos/{tid}/baixas", json={"conta_id": conta, "forma": "pix", "valor": "99999999,00"}, headers=hg)
    valor_folha = next(t["valor"] for t in client.get("/api/contas/titulos", headers=ha).json() if t["id"] == tid)  # a folha soma todos os ativos
    assert valor_folha not in r.text, r.text  # hoje: 400 "A baixa passa do saldo do título (R$ 4321.00)."
    r = client.post(f"/api/contas/titulos/{tid}/baixas", json={"conta_id": conta, "forma": "pix"}, headers=hg)
    assert r.status_code in (403, 404), r.text  # hoje: 201, o gerente paga a folha que não pode ver


def test_N1b_gerente_nao_descobre_a_folha_pela_conciliacao(client):
    """N1: POST /conciliacao com o id da baixa da folha (ids são sequenciais) devolve o valor na mensagem de recusa."""
    ha, hg = entrar(client, "administrador")[1], entrar(client, "gerente")[1]
    tid, conta = _folha_lancada(client, ha, hg, valor="3217,00", dias_atras=230)
    baixa = client.post(f"/api/contas/titulos/{tid}/baixas", json={"conta_id": conta, "forma": "pix"}, headers=ha).json()["baixa_id"]
    rx = client.post("/api/contas/extrato", json={"conta_id": conta, "data": str(date.today()), "descricao": "x", "valor": "-1,00"}, headers=hg); ext = rx.json()["id"]
    r = client.post("/api/contas/conciliacao", json={"extrato_id": ext, "baixa_id": baixa}, headers=hg)
    valor_folha = next(t["valor"] for t in client.get("/api/contas/titulos", headers=ha).json() if t["id"] == tid)  # a folha soma todos os ativos
    assert valor_folha not in r.text, r.text  # hoje: 400 "O extrato mostra R$ -1.00 e a baixa R$ -3217.00 ..."


def test_N2_subgerente_nao_bloqueia_login_do_gerente_ao_desligar(client):
    """N2 (A3 incompleto): o vínculo feito pelo dono é legítimo; o desligamento por quem não tem usuarios.gerir bloqueia o login do gerente."""
    ha, hs = entrar(client, "administrador")[1], entrar(client, "subgerente")[1]
    client.post("/api/rh/iniciar-padrao", headers=hs)
    funcao = client.get("/api/rh/funcoes", headers=hs).json()[0]["id"]
    login_g, h_g = entrar(client, "gerente")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=ha).json() if u["usuario"] == login_g)
    fid = client.post("/api/rh/funcionarios", json={"nome": novo_login("Ger"), "funcao_id": funcao, "usuario_id": uid,
                                                    "admissao": str(date.today() - timedelta(days=30))}, headers=ha).json()["id"]
    r = client.post(f"/api/rh/funcionarios/{fid}/desligar", json={"data": str(date.today()), "motivo": "teste"}, headers=hs)
    assert r.status_code == 403, r.text  # decisão de Marlon: recusar
    assert client.get("/api/auth/me", headers=h_g).status_code == 200
    r = client.post(f"/api/rh/funcionarios/{fid}/desligar", json={"data": str(date.today()), "motivo": "teste"}, headers=ha)
    assert r.status_code == 200, r.text  # o dono desliga e o login fica bloqueado
    assert client.get("/api/auth/me", headers=h_g).status_code == 401


def test_N3_titulos_simultaneos_nao_furam_o_limite_acumulado(client):
    """N3 (A6 incompleto): o acumulado do dia do título manual é somado sem trava; dois terminais passam do limite sem aprovação."""
    ha = entrar(client, "administrador")[1]
    hg = entrar(client, "gerente")[1]
    client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=hg)
    tipo = next(t["id"] for t in client.get("/api/contas/tipos-despesa", headers=hg).json() if t["ativo"])
    assert client.put("/api/parametros/conta_valor_aprovacao", json={"valor": "100,00"}, headers=ha).status_code == 200
    corpo = {"sentido": "pagar", "descricao": "Gás", "valor": "90,00", "vencimento": str(date.today() + timedelta(days=5)), "tipo_despesa_id": tipo}
    res = []
    trava = psycopg.connect(dbname=os.environ["DB_NAME"], **BASE)
    trava.execute("LOCK TABLE titulo IN SHARE MODE")  # alarga a janela entre a soma e a inserção
    ts = [threading.Thread(target=lambda: res.append(client.post("/api/contas/titulos", json=corpo, headers=hg).json())) for _ in range(2)]
    [t.start() for t in ts]
    time.sleep(0.8)
    trava.rollback()
    trava.close()
    [t.join(15) for t in ts]
    client.put("/api/parametros/conta_valor_aprovacao", json={"valor": None}, headers=ha)
    assert sorted(x.get("aprovado") for x in res) == [False, True], res  # hoje: [True, True], R$ 180 sem aprovação
