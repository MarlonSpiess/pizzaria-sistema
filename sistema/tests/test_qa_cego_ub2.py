"""QA cego da segunda rodada ub-mode (23/11/2026): lançamento depois da meia-noite fica no caixa em uso (C1, C4).
Cada teste cria o próprio caixa antigo e o deixa fechado no fim, para não depender da ordem da suíte."""
import os
from datetime import timedelta
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

from tests.conftest import BASE, entrar, novo_login
from tests.test_caixa import _limpar
from tests.test_vendas import _pedido, _pizza_item, cardapio  # noqa: F401  (fixture reaproveitada)

D = Decimal
FORMAS = ["dinheiro", "pix", "credito", "debito"]


def _contagem(**v):
    return {"contagens": [{"forma": f, "valor": v.get(f, "0,00")} for f in FORMAS]}


def _forcar_fechamento(data):
    with psycopg.connect(dbname=os.environ["DB_NAME"], autocommit=True, **BASE) as c:
        c.execute("SET session_replication_role = replica")  # só no teste: desliga o gatilho que impede pular a contagem
        c.execute("UPDATE caixa_dia SET situacao = 'fechado' WHERE data = %s", (data,))


@pytest.fixture(autouse=True)
def _caixas_limpos(client):
    """Cada cenário monta caixas no passado: começa e termina sem caixa nenhum, como o test_caixa."""
    _limpar()
    yield
    _limpar()


def _usuario_qualquer(conn_teste):
    return conn_teste.execute("SELECT id FROM usuario ORDER BY id LIMIT 1").fetchone()[0]


def test_c4_diaria_do_entregador_uma_vez_por_caixa_mesmo_depois_da_meia_noite(client, cardapio, conn_teste):
    """Mesmo caixa ainda aberto (o sistema admite caixa que atravessa a meia-noite). O acerto parcial antes da meia-noite pagou a
    diária; o acerto final depois da meia-noite paga a diária de novo, porque a regra olha a data do relógio e não o caixa."""
    from api.database import hoje
    turno = hoje() - timedelta(days=2)
    uid = _usuario_qualquer(conn_teste)
    conn_teste.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (1, %s, 0, %s, now() - interval '2 day')",
                       (turno, uid))
    try:
        _, hadm = entrar(client, "administrador")
        assert client.put("/api/parametros/diaria_entregador_padrao", json={"valor": "30,00"}, headers=hadm).status_code == 200
        _, hg = entrar(client, "gerente")
        ent = client.post("/api/entregadores", json={"nome": novo_login("Moto")}, headers=hg).json()
        # acerto parcial do mesmo caixa, antes da meia-noite, já com a diária (registro direto: a rota usa a hora do servidor)
        conn_teste.execute("INSERT INTO acerto_entregador (loja_id, data, entregador_id, pedidos, dinheiro_recebido, valor_entregas, diaria, total_devido, "
                           "saldo_gaveta, usuario_id, criado_em) VALUES (1, %s, %s, 1, 0, 0, 30, 30, -30, %s, now() - interval '2 day')", (turno, ent["id"], uid))
        cli = client.post("/api/clientes", json={"nome": "Cliente Noite", "telefone": "5557" + novo_login("")[-4:].rjust(4, "0"),
                                                  "endereco": "Rua C, 3"}, headers=hg).json()
        p = client.post("/api/pedidos", json={"tipo": "entrega", "cliente_id": cli["id"], "itens": [{"tipo": "bebida", "produto_id": cardapio["beb"]["id"]}],
                                             "pagamentos": [{"forma": "pix", "valor": "6,00"}]}, headers=hg)
        assert p.status_code == 201, p.text
        pid = p.json()["id"]
        assert client.post(f"/api/caixa/entregas/{pid}", json={"entregador_id": ent["id"]}, headers=hg).status_code == 201
        for s in ("em producao", "acabado", "despachado ou retirado"):
            assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": s}, headers=hg).status_code == 200
        ac = client.post("/api/caixa/acertos", json={"entregador_id": ent["id"]}, headers=hg)
        assert ac.status_code == 201, ac.text
        assert ac.json()["diaria"] == "0.00", f"diária paga de novo no mesmo caixa: {ac.json()['diaria']}"
    finally:
        client.put("/api/parametros/diaria_entregador_padrao", json={"valor": None}, headers=entrar(client, "administrador")[1])
        _forcar_fechamento(turno)


def test_c1_venda_depois_da_meia_noite_fica_so_no_caixa_em_uso(client, cardapio, conn_teste):
    """Caixa aberto ontem segue aberto depois da meia-noite: a venda de 00h30 pertence a ele (data operacional de ontem)
    e não entra de novo no caixa de hoje quando este abrir. Antes, a venda ficava com a data de hoje e contava nos dois."""
    from api.database import hoje
    from api.services import caixa as svc
    ontem = hoje() - timedelta(days=1)
    conn_teste.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (1, %s, 0, %s, now() - interval '1 day')",
                       (ontem, _usuario_qualquer(conn_teste)))
    with psycopg.connect(dbname=os.environ["DB_NAME"], row_factory=dict_row, **BASE) as c:
        hoje_antes = svc.relatorio(c, 1, (hoje(), svc.FIM), None, False)["recebido_por_forma"]["dinheiro"]
    _, ha = entrar(client, "atendente")
    venda = _pedido(client, ha, [_pizza_item(cardapio)], [{"forma": "dinheiro", "valor": "35,00"}])  # "00h30"
    assert venda.status_code == 201, venda.text
    assert conn_teste.execute("SELECT data FROM pedido WHERE id = %s", (venda.json()["id"],)).fetchone()[0] == ontem
    _forcar_fechamento(ontem)
    assert client.post("/api/caixa/abrir", json={}, headers=ha).status_code == 201  # caixa de hoje, sem venda nova
    with psycopg.connect(dbname=os.environ["DB_NAME"], row_factory=dict_row, **BASE) as c:
        cx = svc.caixa_do_dia(c, 1, hoje())
        hoje_depois = svc.relatorio(c, 1, svc.faixa(c, 1, cx), cx, False)["recebido_por_forma"]["dinheiro"]
        rel_ontem = svc.relatorio(c, 1, svc.faixa(c, 1, svc.caixa_do_dia(c, 1, ontem)), None, False)
    assert hoje_depois == hoje_antes, "a venda já contada no caixa de ontem entrou de novo no caixa de hoje"
    assert rel_ontem["recebido_por_forma"]["dinheiro"] == D("35.00")


def test_c7_fluxo_do_gerente_soma_a_folha_nas_saidas_sem_linha_propria(client, conn_teste):
    """Decisão de Marlon (23/11/2026): o gerente vê o fluxo verdadeiro, com a folha somada às outras saídas do dia,
    sem descrição nem linha que a identifique."""
    from api.database import hoje
    venc = hoje() + timedelta(days=3)
    conn_teste.execute("INSERT INTO titulo (loja_id, sentido, descricao, valor, vencimento, competencia, origem_tipo, origem_id, criado_em) "
                       "VALUES (1, 'pagar', 'Folha QA', 4321.09, %s, %s, 'folha', 209902, now())", (venc, venc.replace(day=1)))
    _, hg = entrar(client, "gerente")
    fl = client.get("/api/contas/fluxo?dias=10", headers=hg)
    assert fl.status_code == 200, fl.text
    assert "folha" not in fl.text.lower()
    dia = next(x for x in fl.json()["projecao"] if x["data"] == venc.isoformat())
    assert D(dia["saidas"]) >= D("4321.09")  # o saldo projetado continua verdadeiro


def test_c8_ingrediente_da_base_fecha_o_tamanho_e_o_da_borda_fecha_a_borda(client, cardapio):
    """Decisão de Marlon (23/11/2026): ingrediente da ficha base em falta fecha toda pizza daquele tamanho; ingrediente da
    ficha de uma borda fecha só aquela borda naquele tamanho. O resto continua vendendo."""
    from tests.test_fichas import _ficha, _item
    _, hg = entrar(client, "gerente")
    _, ha = entrar(client, "atendente")
    molho, recheio = _item(client, hg, "insumo", "g"), _item(client, hg, "insumo", "g")
    base = client.get("/api/fichas/base/grande", headers=hg).json()
    linhas = [{"item_id": x["item_id"], "quantidade": str(x["quantidade"]), "perda_pct": str(x.get("perda_pct", "0"))} for x in base.get("linhas", [])]
    assert _ficha(client, hg, "base/grande", linhas + [{"item_id": molho["id"], "quantidade": "80", "perda_pct": "0"}]).status_code == 200
    borda = cardapio["borda"]["id"]
    assert _ficha(client, hg, f"adicional/{borda}/grande", [{"item_id": recheio["id"], "quantidade": "50", "perda_pct": "0"}]).status_code == 200
    pix = lambda v: [{"forma": "pix", "valor": v}]  # noqa: E731
    try:
        r = client.put(f"/api/vendas-fechadas/ingredientes/{molho['id']}/falta", json={"em_falta": True}, headers=hg)
        assert r.status_code == 200 and "toda pizza Grande" in r.json()["outros"], r.text
        venda = _pedido(client, ha, [_pizza_item(cardapio)], pix("35,00"))
        assert venda.status_code == 409 and "toda pizza Grande" in venda.json()["detail"], venda.text
        assert _pedido(client, ha, [_pizza_item(cardapio, tamanho="broto")], pix("22,00")).status_code == 201  # Broto segue
        assert any(o["nome"] == "toda pizza Grande" for o in client.get("/api/vendas-fechadas", headers=hg).json()["outros_fechados"])
        client.put(f"/api/vendas-fechadas/ingredientes/{molho['id']}/falta", json={"em_falta": False}, headers=hg)

        assert client.put(f"/api/vendas-fechadas/ingredientes/{recheio['id']}/falta", json={"em_falta": True}, headers=hg).status_code == 200
        com_borda = _pedido(client, ha, [_pizza_item(cardapio, adicional_ids=[borda])], pix("43,00"))
        assert com_borda.status_code == 409, com_borda.text
        assert _pedido(client, ha, [_pizza_item(cardapio)], pix("35,00")).status_code == 201  # sem a borda segue
    finally:
        for i in (molho, recheio):
            client.put(f"/api/vendas-fechadas/ingredientes/{i['id']}/falta", json={"em_falta": False}, headers=hg)


def test_c2_pizza_perdida_em_pedido_acabado_volta_para_producao_e_e_refeita(client, cardapio, conn_teste):
    """Decisão de Marlon (23/11/2026): perda em pedido acabado devolve o pedido para 'em producao'; a refação é aceita e
    o balcão só entrega depois que ela fica pronta. O pedido nunca sai com pizza a menos."""
    _, hadm = entrar(client, "administrador")
    if not client.get("/api/producao/motivos", headers=hadm).json()["perda"]:
        client.post("/api/producao/motivos/iniciar-padrao", headers=hadm)
    motivo = client.get("/api/producao/motivos", headers=hadm).json()["perda"][0]["id"]
    _, ha = entrar(client, "atendente")
    _, hac = entrar(client, "acabamento")
    p = _pedido(client, ha, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}])
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    pizza = conn_teste.execute("SELECT id FROM pizza_producao WHERE pedido_id = %s", (pid,)).fetchone()[0]
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'acabada' WHERE id = %s", (pizza,))
    assert client.post(f"/api/producao/pedidos/{pid}/acabado", headers=hac).status_code == 200
    assert client.post(f"/api/producao/pizzas/{pizza}/perder", json={"motivo_id": motivo}, headers=hac).status_code == 200
    situacao = lambda: conn_teste.execute("SELECT situacao FROM pedido WHERE id = %s", (pid,)).fetchone()[0]  # noqa: E731
    assert situacao() == "em producao"
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha).status_code == 409
    r = client.post(f"/api/producao/pizzas/{pizza}/refazer", json={"motivo_id": motivo}, headers=hac)
    assert r.status_code == 201, r.text
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'acabada' WHERE id = %s", (r.json()["id"],))
    assert client.post(f"/api/producao/pedidos/{pid}/acabado", headers=hac).status_code == 200
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha).status_code == 200


def test_c2_banco_so_aceita_voltar_de_acabado_para_producao(client, cardapio, conn_teste):
    """O gatilho aceita acabado para em produção e continua impedindo qualquer outro retorno."""
    _, hg = entrar(client, "gerente")
    p = _pedido(client, hg, [{"tipo": "bebida", "produto_id": cardapio["beb"]["id"]}], [{"forma": "pix", "valor": "6,00"}])
    pid = p.json()["id"]
    for s_ in ("em producao", "acabado"):
        assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": s_}, headers=hg).status_code == 200
    with pytest.raises(psycopg.errors.RaiseException):
        with conn_teste.transaction():
            conn_teste.execute("UPDATE pedido SET situacao = 'recebido' WHERE id = %s", (pid,))
    conn_teste.execute("UPDATE pedido SET situacao = 'em producao' WHERE id = %s", (pid,))
    for s_ in ("acabado", "despachado ou retirado"):
        assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": s_}, headers=hg).status_code == 200
    with pytest.raises(psycopg.errors.RaiseException):
        with conn_teste.transaction():
            conn_teste.execute("UPDATE pedido SET situacao = 'acabado' WHERE id = %s", (pid,))


def test_c6_cancelar_pedido_acabado_devolve_bebida_e_pizza_vira_perda(client, cardapio, conn_teste):
    """Decisão de Marlon (23/11/2026): a lata volta ao estoque; o consumo da pizza já feita sai da venda e entra como perda."""
    from tests.test_fichas import _ficha, _item
    _, hg = entrar(client, "gerente")
    _, ha = entrar(client, "atendente")
    lata, queijo = _item(client, hg, "revenda", "un"), _item(client, hg, "insumo", "g")
    for i, q in ((lata, "10"), (queijo, "1000")):
        r = client.post("/api/estoque/movimentos", json={"tipo": "entrada_inicial", "item_id": i["id"], "quantidade": q, "custo_unit": "3,00",
                                                         "motivo": "Estoque inicial"}, headers=hg)
        assert r.status_code == 201, r.text
    assert _ficha(client, hg, f"produto/{cardapio['beb']['id']}", [{"item_id": lata["id"], "quantidade": "1", "perda_pct": "0"}]).status_code == 200
    assert _ficha(client, hg, f"produto/{cardapio['trad']['id']}", [{"item_id": queijo["id"], "quantidade": "100", "perda_pct": "0"}]).status_code == 200
    p = _pedido(client, ha, [{"tipo": "bebida", "produto_id": cardapio["beb"]["id"]}, _pizza_item(cardapio)], [{"forma": "pix", "valor": "41,00"}])
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    pizza = conn_teste.execute("SELECT id FROM pizza_producao WHERE pedido_id = %s", (pid,)).fetchone()[0]
    from api.database import agora, get_connection
    from api.services import estoque
    with get_connection() as c:  # a Produção acabou a pizza: baixa da ficha como venda (o caminho real está em test_producao)
        estoque.baixar_pizza(c, 1, pizza, "acabada", None, agora())
        c.commit()
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'acabada' WHERE id = %s", (pizza,))
    for s in ("em producao", "acabado"):
        assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": s}, headers=hg).status_code == 200
    assert D(client.get(f"/api/estoque/itens/{lata['id']}", headers=hg).json()["saldo"]) == 9
    assert client.post(f"/api/pedidos/{pid}/cancelar", json={"motivo": "Cliente desistiu no balcão"}, headers=hg).status_code == 200
    assert D(client.get(f"/api/estoque/itens/{lata['id']}", headers=hg).json()["saldo"]) == 10  # a lata voltou
    assert D(client.get(f"/api/estoque/itens/{queijo['id']}", headers=hg).json()["saldo"]) == 800  # Grande = 2 x 100 g, consumidos
    tipos = dict(conn_teste.execute("SELECT tipo, sum(quantidade) FROM movimento_estoque WHERE item_id = %s AND tipo IN ('saida_venda','perda') GROUP BY tipo",
                                    (queijo["id"],)).fetchall())
    assert tipos == {"saida_venda": 0, "perda": -200}, tipos  # saiu da venda, entrou na perda
    assert client.post(f"/api/pedidos/{pid}/cancelar", json={"motivo": "de novo"}, headers=hg).status_code == 409
