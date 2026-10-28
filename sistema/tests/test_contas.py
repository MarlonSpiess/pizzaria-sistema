import os
from datetime import date, timedelta
from decimal import Decimal

import psycopg
import pytest

from tests.conftest import BASE, criar_usuario_direto, entrar, novo_login

D = Decimal
TABELAS = ("conciliacao, extrato_linha, baixa_titulo, titulo, recorrente, canal_repasse, tipo_despesa, conta_bancaria, "
           "caixa_dia, contagem_caixa, movimento_caixa, motivo_movimento, estorno, entrega, acerto_entregador, regra_recebimento, maquininha, recebimento, recebimento_item")


def _limpar():
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        c.execute("SET session_replication_role = replica")
        c.execute(f"TRUNCATE {TABELAS}")


@pytest.fixture(scope="module", autouse=True)
def ambiente(client):
    _limpar()
    _, h = entrar(client, "administrador")
    client.put("/api/parametros/conta_valor_aprovacao", json={"valor": "1000,00"}, headers=h)
    yield
    client.put("/api/parametros/conta_valor_aprovacao", json={"valor": None}, headers=h)
    _limpar()


@pytest.fixture(scope="module")
def base(client):
    ha, hg, hs, hat = (entrar(client, p)[1] for p in ("administrador", "gerente", "subgerente", "atendente"))
    assert client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=hg).status_code == 201
    assert client.post("/api/contas/tipos-despesa/iniciar-padrao", headers=hg).status_code == 409
    tipos = {t["nome"]: t["id"] for t in client.get("/api/contas/tipos-despesa", headers=hg).json()}
    conta = client.post("/api/contas/contas-bancarias", json={"nome": "Banco Teste", "saldo_inicial": "1000,00", "saldo_inicial_data": str(date.today() - timedelta(days=60))}, headers=hg)
    assert conta.status_code == 201
    return {"ha": ha, "hg": hg, "hs": hs, "hat": hat, "tipos": tipos, "conta": conta.json()["id"]}


def test_permissoes(client, base):
    assert client.get("/api/contas/titulos", headers=base["hat"]).status_code == 403
    assert client.post("/api/contas/titulos", json={"sentido": "receber", "descricao": "X", "valor": "1", "vencimento": str(date.today())}, headers=base["hat"]).status_code == 403
    assert client.get("/api/contas/titulos", headers=base["hs"]).status_code == 200
    t = client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Reforma", "valor": "5000,00", "vencimento": str(date.today()), "tipo_despesa_id": base["tipos"]["Manutenção"]}, headers=base["hs"])
    assert t.status_code == 201 and t.json()["aprovado"] is False
    tid = t.json()["ids"][0]
    assert client.post(f"/api/contas/titulos/{tid}/aprovar", headers=base["hs"]).status_code == 403  # subgerente não aprova


def test_titulo_baixa_parcial_e_total(client, base):
    h, hoje = base["hg"], date.today()
    t = client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Aluguel", "valor": "800,00", "vencimento": str(hoje - timedelta(days=3)),
                                                  "tipo_despesa_id": base["tipos"]["Aluguel"]}, headers=h).json()
    tid = t["ids"][0]
    atrasados = client.get("/api/contas/titulos?atrasados=true", headers=h).json()
    assert any(x["id"] == tid and x["dias_atraso"] == 3 for x in atrasados)
    b = {"forma": "pix", "conta_id": base["conta"]}
    assert client.post(f"/api/contas/titulos/{tid}/baixas", json={**b, "valor": "900,00"}, headers=h).status_code == 400
    assert client.post(f"/api/contas/titulos/{tid}/baixas", json={**b, "valor": "300,00", "data": str(hoje + timedelta(days=1))}, headers=h).status_code == 400
    r = client.post(f"/api/contas/titulos/{tid}/baixas", json={**b, "valor": "300,00", "juros": "5,00"}, headers=h)
    assert r.status_code == 201 and r.json()["valor_movimento"] == "305.00"
    x = next(i for i in client.get("/api/contas/titulos", headers=h).json() if i["id"] == tid)
    assert x["situacao"] == "parcial" and x["saldo"] == "500.00"
    assert client.post(f"/api/contas/titulos/{tid}/cancelar", json={"motivo": "Erro"}, headers=h).status_code == 409  # já tem baixa
    assert client.post(f"/api/contas/titulos/{tid}/baixas", json=b, headers=h).status_code == 201  # o resto
    x = next(i for i in client.get("/api/contas/titulos", headers=h).json() if i["id"] == tid)
    assert x["situacao"] == "baixado"
    assert client.post(f"/api/contas/titulos/{tid}/baixas", json={**b, "valor": "1,00"}, headers=h).status_code == 409
    saldo = next(c for c in client.get("/api/contas/contas-bancarias", headers=h).json() if c["id"] == base["conta"])["saldo"]
    assert saldo == "195.00"  # 1000 - (300 + 5) - 500


def test_aprovacao_parcelas_e_cancelamento(client, base):
    hoje = date.today()
    t = client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Forno novo", "valor": "3000,00", "vencimento": str(hoje), "parcelas": 3,
                                                  "tipo_despesa_id": base["tipos"]["Manutenção"]}, headers=base["hg"]).json()
    assert len(t["ids"]) == 3 and t["aprovado"] is False  # 3000 total passa do limite, mesmo com parcelas de 1000
    p = [i for i in client.get("/api/contas/titulos?situacao=pendente", headers=base["hg"]).json() if i["id"] in t["ids"]]
    assert sorted(x["valor"] for x in p) == ["1000.00"] * 3 and p[0]["parcela_total"] == 3
    assert client.post(f"/api/contas/titulos/{t['ids'][0]}/baixas", json={"forma": "pix", "conta_id": base["conta"]}, headers=base["ha"]).status_code == 409
    assert client.post(f"/api/contas/titulos/{t['ids'][0]}/aprovar", headers=base["ha"]).status_code == 200  # administrador aprova o grupo todo
    assert client.get("/api/contas/titulos?situacao=pendente", headers=base["hg"]).json() == [] or all(i["id"] not in t["ids"] for i in client.get("/api/contas/titulos?situacao=pendente", headers=base["hg"]).json())
    c = client.post(f"/api/contas/titulos/{t['ids'][2]}/cancelar", json={"motivo": "Compra desfeita"}, headers=base["hg"])
    assert c.status_code == 200
    assert client.post(f"/api/contas/titulos/{t['ids'][2]}/baixas", json={"forma": "pix", "conta_id": base["conta"]}, headers=base["hg"]).status_code == 409


def test_aprovador_nao_e_quem_lancou(client, base):
    t = client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Obra", "valor": "2000,00", "vencimento": str(date.today()),
                                                  "tipo_despesa_id": base["tipos"]["Manutenção"]}, headers=base["ha"]).json()
    assert t["aprovado"] is False
    assert client.post(f"/api/contas/titulos/{t['ids'][0]}/aprovar", headers=base["ha"]).status_code == 403
    _, hp = entrar(client, "proprietario")
    assert client.post(f"/api/contas/titulos/{t['ids'][0]}/aprovar", headers=hp).status_code == 200


def test_recorrente_gera_um_titulo_por_mes_sem_duplicar(client, base):
    h, hoje = base["hg"], date.today()
    r = client.post("/api/contas/recorrentes", json={"descricao": "Internet", "tipo_despesa_id": base["tipos"]["Internet e telefone"], "valor": "120,00", "dia_vencimento": 10,
                                                      "inicio": str(hoje.replace(day=1) - timedelta(days=65))}, headers=h)
    assert r.status_code == 201
    a = [t for t in client.get("/api/contas/titulos", headers=h).json() if t["descricao"] == "Internet"]
    b = [t for t in client.get("/api/contas/titulos", headers=h).json() if t["descricao"] == "Internet"]
    assert len(a) == len(b) >= 3 and len({t["competencia"] for t in a}) == len(a)
    assert client.post("/api/contas/sincronizar", headers=h).json()["recorrencia"] == 0
    assert client.post("/api/contas/titulos/%d/cancelar" % a[0]["id"], json={"motivo": "Cancelou o plano neste mês"}, headers=h).status_code == 200
    assert client.post("/api/contas/sincronizar", headers=h).json()["recorrencia"] == 0  # cancelado não volta


def test_sincroniza_despesa_do_caixa_acerto_e_fechamento(client, base, conn_teste):
    h, hoje = base["hg"], date.today()
    uid = conn_teste.execute("SELECT id FROM usuario LIMIT 1").fetchone()[0]
    ontem = hoje - timedelta(days=1)
    mid = conn_teste.execute("INSERT INTO motivo_movimento (loja_id, nome, tipo, vira_despesa) VALUES (1,'Despesa teste contas','sangria',true) RETURNING id").fetchone()[0]
    conn_teste.execute("INSERT INTO movimento_caixa (loja_id, data, tipo, valor, motivo_id, motivo_nome, vira_despesa, usuario_id, criado_em) VALUES (1,%s,'sangria',12.50,%s,'Despesa teste contas',true,%s,now())", (ontem, mid, uid))
    eid = conn_teste.execute("INSERT INTO entregador (loja_id, nome, criado_em) VALUES (1,%s,now()) RETURNING id", (novo_login("Ent"),)).fetchone()[0]
    conn_teste.execute("INSERT INTO acerto_entregador (loja_id, data, entregador_id, pedidos, dinheiro_recebido, valor_entregas, diaria, total_devido, saldo_gaveta, usuario_id, criado_em) "
                       "VALUES (1,%s,%s,2,40,10,30,40,0,%s,now())", (ontem, eid, uid))
    cid = conn_teste.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (1,%s,50,%s,now()) RETURNING id", (date(2020, 1, 2), uid)).fetchone()[0]
    conn_teste.execute("INSERT INTO contagem_caixa (caixa_id, forma, contado, esperado, diferenca, usuario_id, criado_em) VALUES (%s,'credito',200,200,0,%s,now())", (cid, uid))
    conn_teste.execute("UPDATE caixa_dia SET situacao = 'contado' WHERE id = %s", (cid,))
    conn_teste.execute("UPDATE caixa_dia SET situacao = 'fechado' WHERE id = %s", (cid,))
    conn_teste.execute("INSERT INTO regra_recebimento (loja_id, forma, taxa_pct, prazo_dias, vigente_desde) VALUES (1,'credito',3.5,30,now())")
    n = client.post("/api/contas/sincronizar", headers=h).json()
    assert n["sangria"] == 1 and n["acerto_entregador"] == 1 and n["fechamento"] == 1
    assert client.post("/api/contas/sincronizar", headers=h).json() == {k: 0 for k in n}
    ts = client.get("/api/contas/titulos", headers=h).json()
    desp = next(t for t in ts if t["descricao"] == "Caixa: Despesa teste contas")
    assert desp["situacao"] == "baixado" and desp["valor"] == "12.50"
    ent = next(t for t in ts if t["descricao"].startswith("Entregador"))
    assert ent["situacao"] == "baixado" and ent["valor"] == "40.00"
    rec = next(t for t in ts if t["sentido"] == "receber" and t["canal"] == "credito" and t["vencimento"] == str(date(2020, 1, 2) + timedelta(days=30)))
    assert rec["taxa_pct"] == "3.50" and rec["situacao"] == "aberto"
    # a maquininha pagou 193,00: desconto de 7,00 revela a taxa real
    conta = base["conta"]
    r = client.post(f"/api/contas/titulos/{rec['id']}/baixas", json={"forma": "credito", "conta_id": conta, "desconto": "7,00"}, headers=h)
    assert r.status_code == 201 and r.json()["valor_movimento"] == "193.00"
    rec = next(t for t in client.get("/api/contas/titulos", headers=h).json() if t["id"] == rec["id"])
    assert rec["taxa_real_pct"] == "3.50"


def test_conciliacao_exige_valor_igual_e_mesma_conta(client, base):
    h, conta = base["hg"], base["conta"]
    pend = client.get(f"/api/contas/conciliacao/{conta}", headers=h).json()
    bx = next(b for b in pend["baixas"] if b["valor_com_sinal"] == "193.00")
    e1 = client.post("/api/contas/extrato", json={"conta_id": conta, "data": str(date.today()), "descricao": "Crédito maquininha", "valor": "190,00"}, headers=h).json()["id"]
    r = client.post("/api/contas/conciliacao", json={"extrato_id": e1, "baixa_id": bx["id"]}, headers=h)
    assert r.status_code == 400 and "193.00" in r.json()["detail"]
    e2 = client.post("/api/contas/extrato", json={"conta_id": conta, "data": str(date.today()), "descricao": "Crédito maquininha", "valor": "193,00"}, headers=h).json()["id"]
    assert client.post("/api/contas/conciliacao", json={"extrato_id": e2, "baixa_id": bx["id"]}, headers=h).status_code == 201
    assert client.post("/api/contas/conciliacao", json={"extrato_id": e2, "baixa_id": bx["id"]}, headers=h).status_code == 409  # já casada
    saida = next(b for b in pend["baixas"] if b["valor_com_sinal"].startswith("-"))
    e3 = client.post("/api/contas/extrato", json={"conta_id": conta, "data": str(date.today()), "descricao": "PIX enviado", "valor": "-" + saida["valor_com_sinal"][1:].replace(".", ",")}, headers=h).json()["id"]
    assert client.post("/api/contas/conciliacao", json={"extrato_id": e3, "baixa_id": saida["id"]}, headers=h).status_code == 201


def test_fluxo_de_caixa(client, base):
    h, hoje = base["hg"], date.today()
    r0 = client.get("/api/contas/fluxo?dias=30", headers=h).json()
    client.post("/api/contas/titulos", json={"sentido": "receber", "descricao": "Evento", "valor": "400,00", "vencimento": str(hoje + timedelta(days=2))}, headers=h)
    client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Gás", "valor": "100,00", "vencimento": str(hoje + timedelta(days=3)), "tipo_despesa_id": base["tipos"]["Gás"]}, headers=h)
    f = client.get("/api/contas/fluxo?dias=30", headers=h).json()
    assert len(f["projecao"]) == 31 and sum(1 for x in f["projecao"] if x["destaque"]) == 7
    d2, d3 = f["projecao"][2], f["projecao"][3]
    assert D(d2["entradas"]) >= D("400") and D(d3["saidas"]) >= D("100")
    assert D(f["saldo_atual"]) == D(r0["saldo_atual"])
    assert client.get("/api/contas/fluxo?dias=0", headers=h).status_code == 400


def test_gatilhos_e_validacoes(client, base, conn_teste):
    with pytest.raises(psycopg.errors.Error):
        conn_teste.execute("DELETE FROM baixa_titulo")
    with pytest.raises(psycopg.errors.Error):
        conn_teste.execute("UPDATE titulo SET valor = valor + 1 WHERE id = (SELECT min(id) FROM titulo)")
    assert client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Sem tipo", "valor": "10", "vencimento": str(date.today())}, headers=base["hg"]).status_code == 400
    assert client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": "Zero", "valor": "0", "vencimento": str(date.today()), "tipo_despesa_id": base["tipos"]["Gás"]}, headers=base["hg"]).status_code == 422
    assert client.post("/api/contas/canais", json={"canal": "Anota Aí", "taxa_pct": "101", "prazo_dias": 1}, headers=base["hg"]).status_code == 422
    assert client.post("/api/contas/canais", json={"canal": "Anota Aí", "taxa_pct": "2,5", "prazo_dias": 15}, headers=base["hg"]).status_code == 201
    assert client.post("/api/contas/canais", json={"canal": "anota aí", "taxa_pct": "2", "prazo_dias": 15}, headers=base["hg"]).status_code == 409


def test_fracionar_nao_foge_do_limite_e_baixa_exagerada_pede_aprovador(client, base):
    h = entrar(client, "subgerente")[1]  # subgerente novo: lança, mas não aprova
    ids = []
    for i in range(3):
        r = client.post("/api/contas/titulos", json={"sentido": "pagar", "descricao": f"Fração {i}", "valor": "450,00", "vencimento": str(date.today()),
                                                      "tipo_despesa_id": base["tipos"]["Manutenção"]}, headers=h).json()
        ids.append((r["ids"][0], r["aprovado"]))
    assert [a for _, a in ids] == [True, True, False]  # o acumulado do dia passou de R$ 1.000 no terceiro
    ok = ids[0][0]
    b = {"forma": "pix", "conta_id": base["conta"]}
    assert client.post(f"/api/contas/titulos/{ok}/baixas", json={**b, "desconto": "450,00"}, headers=h).status_code == 400  # movimento zero
    assert client.post(f"/api/contas/titulos/{ok}/baixas", json={**b, "desconto": "200,00"}, headers=h).status_code == 403  # mais de 20%
    assert client.post(f"/api/contas/titulos/{ok}/baixas", json={**b, "desconto": "200,00"}, headers=base["ha"]).status_code == 201
    assert client.post(f"/api/contas/titulos/{ok}/baixas", json={**b, "data": "2000-01-02"}, headers=h).status_code in (400, 409)


def test_lista_sempre_traz_os_abertos(client, base, conn_teste):
    h = base["hg"]
    uid = conn_teste.execute("SELECT id FROM usuario LIMIT 1").fetchone()[0]
    conn_teste.execute("INSERT INTO titulo (loja_id, sentido, descricao, valor, vencimento, origem_tipo, situacao, criado_em, criado_por) "
                       "SELECT 1, 'pagar', 'Antigo ' || g, 1, DATE '2019-01-01' + g, 'manual', 'baixado', now(), %s FROM generate_series(1, 250) g", (uid,))
    ts = client.get("/api/contas/titulos", headers=h).json()
    assert any(t["situacao"] in ("aberto", "parcial") for t in ts)
    assert sum(1 for t in ts if t["situacao"] == "baixado" and t["descricao"].startswith("Antigo")) <= 200


def test_nota_paga_com_sangria_nao_duplica(client, base, conn_teste):
    h = base["hg"]
    uid = conn_teste.execute("SELECT id FROM usuario LIMIT 1").fetchone()[0]
    ontem = date.today() - timedelta(days=1)
    mid = conn_teste.execute("INSERT INTO motivo_movimento (loja_id, nome, tipo, vira_despesa) VALUES (1,'Compra urgente teste','sangria',true) RETURNING id").fetchone()[0]
    mov = conn_teste.execute("INSERT INTO movimento_caixa (loja_id, data, tipo, valor, motivo_id, motivo_nome, vira_despesa, usuario_id, criado_em) VALUES (1,%s,'sangria',80,%s,'Compra urgente teste',true,%s,now()) RETURNING id", (ontem, mid, uid)).fetchone()[0]
    assert client.post("/api/contas/sincronizar", headers=h).json()["sangria"] >= 1  # a tela abriu antes de a nota ser registrada
    fid = conn_teste.execute("INSERT INTO fornecedor (loja_id, nome, criado_em) VALUES (1,%s,now()) RETURNING id", (novo_login("Forn"),)).fetchone()[0]
    conn_teste.execute("INSERT INTO recebimento (loja_id, fornecedor_id, numero_nota, data_nota, total_nota, movimento_caixa_id, criado_por, criado_em) VALUES (1,%s,'N1',%s,80,%s,%s,now())", (fid, ontem, mov, uid))
    assert client.post("/api/contas/sincronizar", headers=h).json()["recebimento"] == 0
    assert sum(1 for t in client.get("/api/contas/titulos", headers=h).json() if t["valor"] == "80.00" and t["sentido"] == "pagar") == 1
