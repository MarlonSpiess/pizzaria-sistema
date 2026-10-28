import os
from datetime import date, timedelta
from decimal import Decimal

import psycopg
import pytest

from tests.conftest import BASE, criar_usuario_direto, entrar, novo_login

D = Decimal
TABELAS = ("conciliacao, extrato_linha, baixa_titulo, titulo, folha_resumo, documento_rh, ausencia, banco_horas, ponto, turno, beneficio_funcionario, contrato, funcionario, escala_tipo, funcao_rh, "
           "os_peca, ordem_servico, leitura_bem, limite_leitura, plano_manutencao, conferencia_bem, depreciacao_bem, baixa_bem, bem, categoria_bem, tipo_despesa, recorrente, conta_bancaria")


def _limpar():
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        c.execute("SET session_replication_role = replica")
        c.execute(f"TRUNCATE {TABELAS}")


@pytest.fixture(scope="module", autouse=True)
def ambiente(client):
    _limpar()
    _, h = entrar(client, "administrador")
    client.put("/api/parametros/rh_encargos_pct", json={"valor": "30"}, headers=h)
    client.put("/api/parametros/rh_limite_extra_min_mes", json={"valor": "600"}, headers=h)
    yield
    client.put("/api/parametros/rh_encargos_pct", json={"valor": None}, headers=h)
    client.put("/api/parametros/rh_limite_extra_min_mes", json={"valor": None}, headers=h)
    _limpar()


@pytest.fixture(scope="module")
def base(client):
    hs = {p: entrar(client, p)[1] for p in ("administrador", "proprietario", "gerente", "subgerente", "atendente", "pizzaiolo")}
    assert client.post("/api/rh/iniciar-padrao", headers=hs["gerente"]).status_code == 201
    assert client.post("/api/rh/iniciar-padrao", headers=hs["gerente"]).status_code == 409
    funcs = {f["nome"]: f["id"] for f in client.get("/api/rh/funcoes", headers=hs["gerente"]).json()}
    escalas = {e["nome"]: e["id"] for e in client.get("/api/rh/escalas", headers=hs["gerente"]).json()}
    return {**hs, "funcs": funcs, "escalas": escalas}


def _func(client, b, nome=None, funcao="Pizzaiolo", **kw):
    r = client.post("/api/rh/funcionarios", json={"nome": nome or novo_login("Func"), "funcao_id": b["funcs"][funcao], "admissao": str(date.today() - timedelta(days=400)), **kw}, headers=b["gerente"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _contrato(client, b, fid, **kw):
    c = {"tipo": "clt", "escala_id": b["escalas"]["6x1"], "forma_pagamento": "mensal", "valor": "2000,00", "vigente_desde": str(date.today() - timedelta(days=300)), **kw}
    r = client.post(f"/api/rh/funcionarios/{fid}/contratos", json=c, headers=b["administrador"])
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_permissoes_e_salario_so_para_administrador_e_proprietario(client, base):
    assert client.get("/api/rh/funcionarios", headers=base["atendente"]).status_code == 403
    fid = _func(client, base)
    for h in (base["gerente"], base["subgerente"]):
        assert client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "forma_pagamento": "mensal", "valor": "1500", "vigente_desde": str(date.today())}, headers=h).status_code == 403
        assert client.get("/api/rh/folha/previa", headers=h).status_code == 403
    _contrato(client, base, fid)
    ger = next(f for f in client.get("/api/rh/funcionarios", headers=base["gerente"]).json() if f["id"] == fid)
    assert "valor" not in ger["contrato"] and ger["contrato"]["tipo"] == "clt"  # gerente vê o contrato, não o valor
    adm = next(f for f in client.get("/api/rh/funcionarios", headers=base["proprietario"]).json() if f["id"] == fid)
    assert adm["contrato"]["valor"] == "2000.00"


def test_contrato_historico_e_escala_cadastravel(client, base):
    fid = _func(client, base)
    c1 = _contrato(client, base, fid, vigente_desde=str(date.today() - timedelta(days=200)))
    assert client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "forma_pagamento": "mensal", "valor": "2500", "vigente_desde": str(date.today() - timedelta(days=200))}, headers=base["administrador"]).status_code == 400
    c2 = client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "escala_id": base["escalas"]["5x2"], "forma_pagamento": "mensal", "valor": "2500,00", "vigente_desde": str(date.today() - timedelta(days=10))}, headers=base["administrador"])
    assert c2.status_code == 201
    hist = client.get(f"/api/rh/funcionarios/{fid}/contratos", headers=base["administrador"]).json()
    assert [h["valor"] for h in hist] == ["2500.00", "2000.00"] and hist[1]["vigente_ate"] == str(date.today() - timedelta(days=11))
    # a escala é cadastro: nova regra sem mexer em código
    e = client.post("/api/rh/escalas", json={"nome": "4x3", "dias_trabalho": 4, "dias_folga": 3, "horas_semana": "36"}, headers=base["gerente"])
    assert e.status_code == 201
    assert client.post("/api/rh/escalas", json={"nome": "X", "dias_trabalho": 6, "dias_folga": 3, "horas_semana": "36"}, headers=base["gerente"]).status_code == 400
    assert client.post("/api/rh/escalas", json={"nome": "4X3", "dias_trabalho": 4, "dias_folga": 3, "horas_semana": "36"}, headers=base["gerente"]).status_code == 409


def test_desligar_bloqueia_login_e_encerra_contrato(client, base):
    login, senha = criar_usuario_direto("pizzaiolo")
    uid = client.get("/api/usuarios", headers=base["administrador"]).json()
    uid = next(u["id"] for u in uid if u["usuario"] == login)
    fid = _func(client, base, usuario_id=uid)
    _contrato(client, base, fid)
    assert client.post("/api/auth/login", json={"usuario": login, "senha": senha}).status_code == 200
    assert client.post("/api/rh/funcionarios", json={"nome": "Outro", "funcao_id": base["funcs"]["Massa"], "admissao": str(date.today()), "usuario_id": uid}, headers=base["gerente"]).status_code == 409  # login já ligado
    d = {"data": str(date.today()), "motivo": "Pediu demissão"}
    assert client.post(f"/api/rh/funcionarios/{fid}/desligar", json={**d, "data": "2000-01-01"}, headers=base["gerente"]).status_code == 400
    assert client.post(f"/api/rh/funcionarios/{fid}/desligar", json=d, headers=base["gerente"]).status_code == 200
    assert client.post(f"/api/rh/funcionarios/{fid}/desligar", json=d, headers=base["gerente"]).status_code == 409
    assert client.post("/api/auth/login", json={"usuario": login, "senha": senha}).status_code in (401, 403)
    f = next(x for x in client.get("/api/rh/funcionarios", headers=base["gerente"]).json() if x["id"] == fid)
    assert f["ativo"] is False and f["desligamento"] == str(date.today())
    assert client.patch(f"/api/rh/funcionarios/{fid}", json={"nome": "Novo nome"}, headers=base["gerente"]).status_code == 409
    assert client.post(f"/api/rh/funcionarios/{fid}/contratos", json={"tipo": "clt", "forma_pagamento": "mensal", "valor": "1", "vigente_desde": str(date.today())}, headers=base["administrador"]).status_code == 409


def test_escala_ausencia_escalados_e_meus_dados(client, base):
    hoje = date.today()
    login, senha = criar_usuario_direto("pizzaiolo")
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=base["administrador"]).json() if u["usuario"] == login)
    a, b2 = _func(client, base, usuario_id=uid), _func(client, base)
    dia = hoje + timedelta(days=3)
    t = {"data": str(dia), "funcao_id": base["funcs"]["Pizzaiolo"], "inicio": "17:00", "fim": "23:00"}
    assert client.put("/api/rh/turnos", json={**t, "funcionario_id": a}, headers=base["gerente"]).status_code == 200
    assert client.put("/api/rh/turnos", json={**t, "funcionario_id": b2}, headers=base["gerente"]).status_code == 200
    assert client.put("/api/rh/turnos", json={**t, "funcionario_id": a, "fim": "16:00"}, headers=base["gerente"]).status_code == 400
    assert client.put("/api/rh/turnos", json={**t, "funcionario_id": a, "inicio": "25:00"}, headers=base["gerente"]).status_code == 422
    assert client.get(f"/api/rh/escalados?data={dia}&funcao=pizzaiolo", headers=base["pizzaiolo"]).json()["quantidade"] == 2
    # férias de um deles tiram o turno da escala e impedem novo turno
    assert client.post("/api/rh/ausencias", json={"funcionario_id": b2, "tipo": "ferias", "inicio": str(dia), "fim": str(dia + timedelta(days=10))}, headers=base["gerente"]).status_code == 201
    assert client.post("/api/rh/ausencias", json={"funcionario_id": b2, "tipo": "ferias", "inicio": str(dia), "fim": str(dia + timedelta(days=2))}, headers=base["gerente"]).status_code == 409
    assert client.put("/api/rh/turnos", json={**t, "funcionario_id": b2}, headers=base["gerente"]).status_code == 409
    assert client.get(f"/api/rh/escalados?data={dia}&funcao=pizzaiolo", headers=base["gerente"]).json()["quantidade"] == 1
    # o funcionário vê só o que é dele
    tok = client.post("/api/auth/login", json={"usuario": login, "senha": senha}).json()["token"]
    eu = client.get("/api/rh/meus-dados", headers={"Authorization": "Bearer " + tok})
    assert eu.status_code == 200 and eu.json()["turnos"][0]["data"] == str(dia) and "contrato" not in eu.json() and "salario" not in str(eu.json()).lower()
    assert client.get("/api/rh/funcionarios", headers={"Authorization": "Bearer " + tok}).status_code == 403
    assert client.get("/api/rh/meus-dados", headers=base["atendente"]).status_code == 404  # login sem cadastro de funcionário


def test_ponto_saldo_e_banco_de_horas_com_limite(client, base):
    fid = _func(client, base)
    _contrato(client, base, fid, escala_id=base["escalas"]["6x1"])  # 44 h em 6 dias: 440 min por dia
    ontem = date.today() - timedelta(days=1)
    t = {"funcionario_id": fid, "data": str(ontem), "funcao_id": base["funcs"]["Pizzaiolo"], "inicio": "16:00", "fim": "23:00"}
    assert client.put("/api/rh/turnos", json=t, headers=base["gerente"]).status_code == 200
    assert client.put("/api/rh/ponto", json={"funcionario_id": fid, "data": str(ontem), "entrada": "16:00", "saida": "23:30"}, headers=base["gerente"]).status_code == 200
    assert client.put("/api/rh/ponto", json={"funcionario_id": fid, "data": str(ontem), "entrada": "16:00", "saida": "15:00"}, headers=base["gerente"]).status_code == 400
    assert client.put("/api/rh/ponto", json={"funcionario_id": fid, "data": str(date.today() + timedelta(days=1)), "entrada": "10:00", "saida": "11:00"}, headers=base["gerente"]).status_code == 400
    s = client.get(f"/api/rh/ponto/saldo?funcionario_id={fid}&mes={ontem.strftime('%Y-%m')}", headers=base["gerente"]).json()
    dia = next(x for x in s["dias"] if x["data"] == str(ontem))
    assert dia["trabalhado_min"] == 450 and dia["previsto_min"] == 440 and dia["saldo_min"] == 10
    b = {"funcionario_id": fid, "data": str(ontem), "minutos": 500, "motivo": "Evento"}
    assert client.post("/api/rh/banco-horas", json=b, headers=base["subgerente"]).status_code == 403  # só administrador ou gerente aprova
    assert client.post("/api/rh/banco-horas", json=b, headers=base["gerente"]).status_code == 201
    r = client.post("/api/rh/banco-horas", json={**b, "minutos": 200}, headers=base["gerente"])
    assert r.status_code == 403  # 700 > limite de 600 no mês
    assert client.post("/api/rh/banco-horas", json={**b, "minutos": 200}, headers=base["administrador"]).status_code == 201
    assert client.post("/api/rh/banco-horas", json={**b, "minutos": -900}, headers=base["gerente"]).status_code == 400  # passa do saldo
    assert client.post("/api/rh/banco-horas", json={**b, "minutos": -300, "motivo": "Folga compensada"}, headers=base["gerente"]).json()["saldo_min"] == 400


def test_folha_previa_resumo_e_titulo_em_contas(client, base):
    ini = date.today().replace(day=1)
    mes = ini.strftime("%Y-%m")
    clt, dia, hora = _func(client, base), _func(client, base), _func(client, base)
    _contrato(client, base, clt, valor="2000,00")
    _contrato(client, base, dia, tipo="diarista", forma_pagamento="diaria", valor="100,00", escala_id=None)
    _contrato(client, base, hora, tipo="freelancer", forma_pagamento="hora", valor="20,00", escala_id=None)
    assert client.post(f"/api/rh/funcionarios/{clt}/beneficios", json={"nome": "Vale-transporte", "valor_mensal": "150,00"}, headers=base["administrador"]).status_code == 201
    base_dia = ini if ini < date.today() else ini
    for n in range(2):
        d = ini + timedelta(days=n)
        if d <= date.today():
            client.put("/api/rh/ponto", json={"funcionario_id": dia, "data": str(d), "entrada": "10:00", "saida": "16:00"}, headers=base["gerente"])
            client.put("/api/rh/ponto", json={"funcionario_id": hora, "data": str(d), "entrada": "10:00", "saida": "13:30"}, headers=base["gerente"])
    p = client.get(f"/api/rh/folha/previa?mes={mes}", headers=base["administrador"]).json()
    l = {x["funcionario_id"]: x for x in p["linhas"]}
    assert l[clt]["bruto"] == "2000.00" and l[clt]["encargos"] == "600.00" and l[clt]["beneficios"] == "150.00" and l[clt]["total"] == "2750.00"  # 30% de encargos só em CLT
    dias = sum(1 for n in range(2) if ini + timedelta(days=n) <= date.today())
    assert l[dia]["bruto"] == f"{100 * dias}.00" and l[dia]["encargos"] == "0.00" and l[hora]["bruto"] == f"{70 * dias}.00"
    # sem o tipo de despesa não lança; com ele, uma vez só
    assert client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=base["administrador"]).status_code == 400
    assert client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=base["gerente"]).status_code in (201, 409)
    r = client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=base["administrador"])
    assert r.status_code == 201 and r.json()["origem"] == "prévia gerencial" and D(r.json()["total"]) == D(p["total"])
    assert client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=base["administrador"]).status_code == 409
    assert client.post("/api/rh/folha/resumo", json={"competencia": mes, "funcionario_id": clt, "bruto": "2100,00"}, headers=base["administrador"]).status_code == 409  # já lançada
    t = next(x for x in client.get("/api/contas/titulos", headers=base["administrador"]).json() if x["origem_tipo"] == "folha")
    assert t["sentido"] == "pagar" and t["tipo_despesa"] == "Folha de pagamento"
    # o custo de pessoal entra nos custos fixos
    r = client.get(f"/api/custos/resultado?mes={mes}", headers=base["administrador"]).json()
    assert D(r["fixos_detalhe"]["pessoal"]) >= D(t["valor"])


def test_resumo_do_contador_vale_no_lugar_da_previa(client, base):
    mes = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")  # mês passado
    f = _func(client, base)
    assert client.post("/api/rh/folha/resumo", json={"competencia": mes, "funcionario_id": f, "bruto": "3000,00", "encargos": "900,00", "beneficios": "100,00"}, headers=base["administrador"]).status_code == 201
    assert client.post("/api/rh/folha/resumo", json={"competencia": mes, "funcionario_id": f, "bruto": "1,00"}, headers=base["administrador"]).status_code == 409
    previa = client.get(f"/api/rh/folha/previa?mes={mes}", headers=base["administrador"]).json()["linhas"]
    outros = [l["funcionario_id"] for l in previa if l["funcionario_id"] != f]
    if outros:  # resumo incompleto não se lança
        assert client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=base["administrador"]).status_code == 409
        for o in outros:
            assert client.post("/api/rh/folha/resumo", json={"competencia": mes, "funcionario_id": o, "bruto": "1,00"}, headers=base["administrador"]).status_code == 201
    r = client.post("/api/rh/folha/lancar", json={"competencia": mes}, headers=base["administrador"])
    assert r.status_code == 201 and r.json()["origem"] == "resumo do contador" and D(r.json()["total"]) == D("4000.00") + len(outros)


def test_documentos_e_alertas(client, base):
    f = _func(client, base)
    _contrato(client, base, f)
    hoje = date.today()
    assert client.post("/api/rh/documentos", json={"funcionario_id": f, "nome": "Manipulação de alimentos", "validade": str(hoje + timedelta(days=10))}, headers=base["gerente"]).status_code == 201
    assert client.post("/api/rh/documentos", json={"funcionario_id": f, "nome": "ASO", "emitido": str(hoje), "validade": str(hoje - timedelta(days=1))}, headers=base["gerente"]).status_code == 400
    al = client.get("/api/rh/alertas", headers=base["gerente"]).json()
    assert any(d["funcionario"] and d["nome"] == "Manipulação de alimentos" for d in al["documentos"])
    assert any(x["funcionario"] for x in al["ferias_vencendo"])  # CLT admitido há 400 dias sem férias
    novo = _func(client, base)
    assert any(x["id"] == novo for x in client.get("/api/rh/alertas", headers=base["gerente"]).json()["sem_contrato"])
