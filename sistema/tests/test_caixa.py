import os
import threading
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

from tests.conftest import BASE, criar_usuario_direto, entrar, novo_login
from tests.test_vendas import _pedido, _pizza_item, _pizzas_prontas, cardapio  # noqa: F401  (fixture reaproveitada)

PARAMS = {"fundo_troco_padrao": "100,00", "tolerancia_diferenca_caixa": "1,00", "sangria_limite_gerente": "50,00",
          "valor_entrega_padrao": "5,00", "diaria_entregador_padrao": "30,00", "taxa_entrega_padrao": "6,00"}
TABELAS = "caixa_dia, contagem_caixa, movimento_caixa, motivo_movimento, estorno, entrega, acerto_entregador, regra_recebimento, maquininha, recebimento, recebimento_item"
D = Decimal


def _limpar():
    """Tabelas só de inserção não aceitam apagar; o teste usa um superusuário com os gatilhos desligados só para zerar o estado."""
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        c.execute("SET session_replication_role = replica")
        c.execute(f"TRUNCATE {TABELAS}")


@pytest.fixture(scope="module", autouse=True)
def ambiente(client):
    _limpar()
    _, h = entrar(client, "administrador")
    for k, v in PARAMS.items():
        assert client.put(f"/api/parametros/{k}", json={"valor": v}, headers=h).status_code == 200
    yield
    for k in PARAMS:
        client.put(f"/api/parametros/{k}", json={"valor": None}, headers=h)
    client.put("/api/parametros/venda_exige_caixa_aberto", json={"valor": None}, headers=h)
    _limpar()


def _esperado_base():
    """Esperado do dia antes do cenário (outros testes do mesmo banco também vendem hoje): o cenário soma em cima disso."""
    from api.database import hoje
    from api.services.caixa import FIM, esperado
    with psycopg.connect(dbname=os.environ["DB_NAME"], row_factory=dict_row, **BASE) as c:
        return esperado(c, 1, (hoje(), FIM), D("0"))


def _pronto_e_entregue(client, conn_teste, pid, h):
    _pizzas_prontas(conn_teste, pid)
    for s in ("em producao", "acabado", "despachado ou retirado"):
        assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": s}, headers=h).status_code == 200


def test_permissoes_e_cadastros(client):
    anon = client.get("/api/caixa/hoje")
    assert anon.status_code == 401
    _, ha = entrar(client, "atendente")
    _, hs = entrar(client, "subgerente")
    _, hg = entrar(client, "gerente")
    assert client.get("/api/caixa/hoje", headers=ha).status_code == 200
    assert client.post("/api/caixa/motivos/iniciar-padrao", headers=ha).status_code == 403
    assert client.post("/api/caixa/maquininhas", json={"nome": "Stone"}, headers=ha).status_code == 403
    r = client.post("/api/caixa/motivos/iniciar-padrao", headers=hg)
    assert r.status_code == 201 and {m["nome"] for m in r.json()} == {"Despesa pequena", "Depósito", "Reforço de troco"}
    assert client.post("/api/caixa/motivos/iniciar-padrao", headers=hg).status_code == 409
    assert client.post("/api/caixa/motivos", json={"nome": "Depósito", "tipo": "sangria"}, headers=hg).status_code == 409  # duplicado
    assert client.post("/api/caixa/motivos", json={"nome": "Troco extra", "tipo": "suprimento", "vira_despesa": True}, headers=hg).status_code == 400
    m = client.post("/api/caixa/motivos", json={"nome": "Gás", "tipo": "sangria", "vira_despesa": True}, headers=hs).json()
    assert client.patch(f"/api/caixa/motivos/{m['id']}", json={"ativo": False}, headers=hs).json()["ativo"] is False
    mq = client.post("/api/caixa/maquininhas", json={"nome": "Stone"}, headers=hg)
    assert mq.status_code == 201 and client.post("/api/caixa/maquininhas", json={"nome": "stone"}, headers=hg).status_code == 409
    base = {"forma": "credito", "maquininha_id": mq.json()["id"], "taxa_pct": "3,5", "prazo_dias": 30}
    assert client.post("/api/caixa/regras-recebimento", json=base, headers=hg).status_code == 201
    assert client.post("/api/caixa/regras-recebimento", json={**base, "taxa_pct": "2,9"}, headers=hg).status_code == 201
    assert client.post("/api/caixa/regras-recebimento", json={**base, "forma": "pix"}, headers=hg).status_code == 400  # maquininha só em cartão
    assert client.post("/api/caixa/regras-recebimento", json={**base, "prazo_dias": 400}, headers=hg).status_code == 422
    reg = client.get("/api/caixa/regras-recebimento", headers=hg).json()
    assert len(reg["historico"]) == 2 and reg["vigentes"][0]["taxa_pct"] == "2.90"


def test_venda_exige_caixa_aberto_so_quando_o_parametro_manda(client, cardapio):
    _, adm = entrar(client, "administrador")
    _, ha = entrar(client, "atendente")
    it, pag = [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]
    client.put("/api/parametros/venda_exige_caixa_aberto", json={"valor": "sim"}, headers=adm)
    try:
        r = _pedido(client, ha, it, pag)
        assert r.status_code == 409 and "caixa" in r.json()["detail"].lower()
    finally:
        client.put("/api/parametros/venda_exige_caixa_aberto", json={"valor": "nao"}, headers=adm)
    assert _pedido(client, ha, it, pag).status_code == 201
    assert client.put("/api/parametros/venda_exige_caixa_aberto", json={"valor": "talvez"}, headers=adm).status_code == 400


def test_movimento_sem_caixa_aberto_e_abertura_concorrente(client):
    _, ha = entrar(client, "atendente")
    assert client.post("/api/caixa/movimentos", json={"tipo": "suprimento", "valor": "10,00", "motivo_id": 1}, headers=ha).status_code == 409
    assert client.post("/api/caixa/abrir", json={"fundo_troco": "50,00"}, headers=ha).status_code == 403  # fundo fora do padrão: gerência
    codigos = []
    def abrir():
        codigos.append(client.post("/api/caixa/abrir", json={"fundo_troco": "100,00"}, headers=ha).status_code)
    ts = [threading.Thread(target=abrir) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codigos) == [201, 409]
    assert client.post("/api/caixa/abrir", json={}, headers=ha).status_code == 409


def test_limites_do_atendente(client, cardapio):
    _, ha = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    mot = {m["nome"]: m["id"] for m in client.get("/api/caixa/motivos", headers=ha).json()}
    dep = {"tipo": "sangria", "motivo_id": mot["Depósito"]}
    assert client.post("/api/caixa/movimentos", json={**dep, "valor": "30,00"}, headers=ha).status_code == 201
    assert client.post("/api/caixa/movimentos", json={**dep, "valor": "30,00"}, headers=ha).status_code == 403  # a soma do dia passa do limite
    assert client.post("/api/caixa/movimentos", json={"tipo": "suprimento", "valor": "30,00", "motivo_id": mot["Reforço de troco"]}, headers=ha).status_code == 201
    cli = client.post("/api/clientes", json={"nome": "Limite Entrega", "telefone": "5558" + novo_login("")[-4:].rjust(4, "0"), "endereco": "Rua C, 3"}, headers=ha).json()
    ped = _pedido(client, ha, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "41,00"}], tipo="entrega", cliente_id=cli["id"]).json()
    ent = client.post("/api/entregadores", json={"nome": novo_login("Moto")}, headers=hg).json()
    assert client.post(f"/api/caixa/entregas/{ped['id']}", json={"entregador_id": ent["id"], "valor_entrega": "9999,00"}, headers=ha).status_code == 403
    assert client.post("/api/caixa/acertos", json={"entregador_id": ent["id"], "diaria": "5000,00"}, headers=ha).status_code in (403, 409)
    assert client.post(f"/api/caixa/entregas/{ped['id']}", json={"entregador_id": ent["id"], "valor_entrega": "7,00"}, headers=hg).status_code == 201  # gerência pode
    client.post(f"/api/pedidos/{ped['id']}/cancelar", json={"motivo": "Teste de limites"}, headers=hg)  # sai da lista de acertos pendentes


def test_dia_completo_contagem_cega_entregador_estorno_e_fechamento(client, cardapio, conn_teste):
    base = _esperado_base()
    _, ha = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    sl, ss = criar_usuario_direto("subgerente")
    gl, gs = criar_usuario_direto("gerente")
    hoje = client.get("/api/caixa/hoje", headers=ha).json()
    assert hoje["caixa"]["situacao"] == "aberto" and hoje["caixa"]["fundo_troco"] == "100.00"
    it = [_pizza_item(cardapio)]  # 35,00
    # A: retirada em dinheiro com troco; B: pix; C: entrega em dinheiro; D: pix cancelado depois
    a = _pedido(client, ha, it, [{"forma": "dinheiro", "valor": "50,00"}]).json()
    b = _pedido(client, ha, it, [{"forma": "pix", "valor": "35,00"}]).json()
    cli = client.post("/api/clientes", json={"nome": "Entrega Caixa", "telefone": "5559" + novo_login("")[-4:].rjust(4, "0"), "endereco": "Rua B, 2"}, headers=ha).json()
    c = _pedido(client, ha, it, [{"forma": "dinheiro", "valor": "41,00"}], tipo="entrega", cliente_id=cli["id"]).json()
    d = _pedido(client, ha, it, [{"forma": "pix", "valor": "35,00"}]).json()
    assert a["troco"] == "15.00"
    assert client.post(f"/api/pedidos/{d['id']}/cancelar", json={"motivo": "Desistiu"}, headers=hg).status_code == 200
    # movimentos: reforço, despesa pequena e sangria acima do limite (precisa de gerente)
    mot = {m["nome"]: m["id"] for m in client.get("/api/caixa/motivos", headers=ha).json()}
    sup = client.post("/api/caixa/movimentos", json={"tipo": "suprimento", "valor": "20,00", "motivo_id": mot["Reforço de troco"]}, headers=ha)
    assert sup.status_code == 201
    assert client.post("/api/caixa/movimentos", json={"tipo": "sangria", "valor": "10,00", "motivo_id": mot["Despesa pequena"], "comprovante": "Recibo 77"}, headers=ha).status_code == 201
    assert client.post("/api/caixa/movimentos", json={"tipo": "sangria", "valor": "1,00", "motivo_id": mot["Despesa pequena"]}, headers=ha).status_code == 400  # despesa sem comprovante
    grande = {"tipo": "sangria", "valor": "60,00", "motivo_id": mot["Depósito"]}
    assert client.post("/api/caixa/movimentos", json=grande, headers=ha).status_code == 403
    assert client.post("/api/caixa/movimentos", json={**grande, "autorizacao": {"usuario": sl, "senha": ss}}, headers=ha).status_code == 403  # subgerente não autoriza
    assert client.post("/api/caixa/movimentos", json={**grande, "autorizacao": {"usuario": gl, "senha": gs}}, headers=ha).status_code == 201
    assert client.post("/api/caixa/movimentos", json={"tipo": "suprimento", "valor": "5,00", "motivo_id": mot["Depósito"]}, headers=ha).status_code == 404  # motivo de outro tipo
    assert client.post("/api/caixa/movimentos", json={"tipo": "sangria", "valor": "0,00", "motivo_id": mot["Depósito"]}, headers=ha).status_code == 422
    # entrega: atribuir, e a contagem espera o acerto
    ent = client.post("/api/entregadores", json={"nome": novo_login("Motoboy")}, headers=hg).json()
    assert client.post(f"/api/caixa/entregas/{a['id']}", json={"entregador_id": ent["id"]}, headers=ha).status_code == 409  # retirada
    assert client.post(f"/api/caixa/entregas/{d['id']}", json={"entregador_id": ent["id"]}, headers=ha).status_code == 409  # cancelado
    r = client.post(f"/api/caixa/entregas/{c['id']}", json={"entregador_id": ent["id"]}, headers=ha)
    assert r.status_code == 201 and r.json()["valor_entrega"] == "5.00"
    assert client.post(f"/api/caixa/entregas/{c['id']}", json={"entregador_id": ent["id"]}, headers=ha).status_code == 409
    formas = ["dinheiro", "pix", "credito", "debito"]
    todas = lambda **v: {"contagens": [{"forma": f, "valor": v.get(f, "0,00")} for f in formas]}
    assert client.post("/api/caixa/contagem", json=todas(), headers=ha).status_code == 409  # entrega sem acerto
    assert client.post("/api/caixa/acertos", json={"entregador_id": ent["id"]}, headers=ha).status_code == 409  # ainda não entregue
    _pronto_e_entregue(client, conn_teste, c["id"], hg)
    ac = client.post("/api/caixa/acertos", json={"entregador_id": ent["id"]}, headers=ha)
    assert ac.status_code == 201, ac.text
    ac = ac.json()
    assert (ac["dinheiro_recebido"], ac["valor_entregas"], ac["diaria"], ac["total_devido"], ac["saldo_gaveta"]) == ("41.00", "5.00", "30.00", "35.00", "6.00")
    assert client.post("/api/caixa/acertos", json={"entregador_id": ent["id"]}, headers=ha).status_code == 409  # nada a acertar
    # contagem cega: antes de contar não há esperado, nem recebido por forma
    cego = client.get("/api/caixa/hoje", headers=ha).json()
    assert cego["recebido_por_forma"] is None and "contagens" not in cego and cego["vendas"] is None
    assert "esperado" not in client.get("/api/caixa/hoje", headers=ha).text
    assert cego["pedidos"] is None and all("total" not in x for x in cego["pedidos_sem_cf"]) and cego["cancelamentos"]["valor"] is None
    assert client.post("/api/caixa/contagem", json={"contagens": [{"forma": "dinheiro", "valor": "1,00"}]}, headers=ha).status_code == 400  # incompleta
    assert client.post("/api/caixa/contagem", json={"contagens": todas()["contagens"] + [{"forma": "pix", "valor": "1,00"}]}, headers=ha).status_code == 400  # repetida
    # esperado: dinheiro = base + fundo 100 + A 35 + C 41 + suprimento 20 - sangrias 70 - acerto 35 ; pix = base + B 35 (D estornado)
    dinheiro = base["dinheiro"] + D("91.00")
    pix = base["pix"] + D("35.00")
    contado = todas(dinheiro=f"{dinheiro - 2}".replace(".", ","), pix=f"{pix}".replace(".", ","),
                    credito=f"{base['credito']}".replace(".", ","), debito=f"{base['debito']}".replace(".", ","))
    r = client.post("/api/caixa/contagem", json=contado, headers=ha)
    assert r.status_code == 200, r.text
    linhas = {x["forma"]: x for x in r.json()["contagens"]}
    assert D(linhas["dinheiro"]["esperado"]) == dinheiro and D(linhas["dinheiro"]["diferenca"]) == D("-2.00")
    assert D(linhas["pix"]["esperado"]) == pix and D(linhas["pix"]["diferenca"]) == 0
    assert r.json()["caixa"]["situacao"] == "contado"
    assert client.post("/api/caixa/contagem", json=contado, headers=ha).status_code == 409  # uma vez só
    # depois da contagem nada entra no caixa
    assert _pedido(client, ha, it, [{"forma": "pix", "valor": "35,00"}]).status_code == 409
    assert client.post(f"/api/pedidos/{b['id']}/cancelar", json={"motivo": "Tarde"}, headers=hg).status_code == 409
    assert client.post("/api/caixa/movimentos", json={"tipo": "suprimento", "valor": "5,00", "motivo_id": mot["Reforço de troco"]}, headers=ha).status_code == 409
    # fechamento: diferença de R$ 2,00 passa da tolerância de R$ 1,00
    assert client.post("/api/caixa/fechar", json={}, headers=ha).status_code == 400  # sem justificativa
    assert client.post("/api/caixa/fechar", json={"justificativa": "Troco errado"}, headers=ha).status_code == 403  # sem aprovador
    assert client.post("/api/caixa/fechar", json={"justificativa": "Troco errado", "autorizacao": {"usuario": sl, "senha": ss}}, headers=ha).status_code == 403
    _, hs = entrar(client, "subgerente")
    assert client.post("/api/caixa/fechar", json={"justificativa": "Troco errado"}, headers=hs).status_code == 403  # subgerente não aprova
    r = client.post("/api/caixa/fechar", json={"justificativa": "Troco errado", "autorizacao": {"usuario": gl, "senha": gs}}, headers=ha)
    assert r.status_code == 200 and r.json()["caixa"]["situacao"] == "fechado" and r.json()["caixa"]["aprovado_por"] is not None
    assert client.post("/api/caixa/fechar", json={"justificativa": "x"}, headers=hg).status_code == 409
    rel = client.get("/api/caixa/hoje", headers=ha).json()
    assert sorted(e["valor"] for e in rel["estornos"]) == ["35.00", "41.00"] and {e["forma"] for e in rel["estornos"]} == {"pix"}
    assert {m["tipo"] for m in rel["movimentos"]} == {"sangria", "suprimento"}
    assert [x["id_dia"] for x in rel["pedidos_sem_cf"]].count(a["id_dia"]) == 1
    assert client.patch(f"/api/pedidos/{a['id']}/cf", json={"numero_cf": "12345"}, headers=ha).json()["numero_cf"] == "12345"
    rel = client.get("/api/caixa/hoje/relatorio".replace("hoje", __import__("api.database", fromlist=["hoje"]).hoje().isoformat()), headers=ha)
    assert rel.status_code == 200 and rel.json()["caixa"]["situacao"] == "fechado"
    assert client.post("/api/caixa/abrir", json={}, headers=ha).status_code == 409


def test_gatilhos_protegem_o_registro(client, conn_teste):
    for sql in ("UPDATE contagem_caixa SET contado = 0", "DELETE FROM movimento_caixa", "UPDATE estorno SET valor = 1", "DELETE FROM acerto_entregador",
                "UPDATE caixa_dia SET situacao = 'aberto'", "UPDATE caixa_dia SET fundo_troco = 1", "DELETE FROM caixa_dia",
                "UPDATE entrega SET valor_entrega = 99", "UPDATE entrega SET acerto_id = 12345", "DELETE FROM entrega", "TRUNCATE contagem_caixa",
                "UPDATE regra_recebimento SET taxa_pct = 0"):
        with pytest.raises(psycopg.Error):
            conn_teste.execute(sql)
