from datetime import date, timedelta
from decimal import Decimal

import pytest

from tests.conftest import criar_usuario_direto, entrar, novo_login
from tests.test_cadastros import _cat, _pizza
from tests.test_fichas import _ficha, _item
from tests.test_producao import _ate_acabar, _motivos, _pagar  # noqa: F401
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

D = Decimal


@pytest.fixture(autouse=True)
def fila_limpa(conn_teste):
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'cancelada' WHERE situacao IN ('na lista','em montagem','no forno','saiu do forno')")
    yield


@pytest.fixture(scope="module", autouse=True)
def limites(client):
    _, h = entrar(client, "administrador")
    client.put("/api/parametros/compra_valor_aprovacao", json={"valor": "100,00"}, headers=h)
    client.put("/api/parametros/forno_pizzas_por_vez", json={"valor": "4"}, headers=h)
    assert client.post("/api/producao/motivos/iniciar-padrao", headers=h).status_code in (201, 409)
    yield
    client.put("/api/parametros/compra_valor_aprovacao", json={"valor": None}, headers=h)
    client.put("/api/parametros/forno_pizzas_por_vez", json={"valor": None}, headers=h)


@pytest.fixture
def hs(client):
    return {p: entrar(client, p)[1] for p in ("administrador", "gerente", "subgerente", "atendente", "pizzaiolo", "acabamento")}


def _saldo(client, h, iid):
    return D(client.get(f"/api/estoque/itens/{iid}", headers=h).json()["saldo"])


def _inicial(client, h, iid, qtd, custo, **kw):
    r = client.post("/api/estoque/movimentos", json={"tipo": "entrada_inicial", "item_id": iid, "quantidade": qtd, "custo_unit": custo, "motivo": "Estoque inicial", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_permissoes_locais_e_configuracao(client, hs):
    h, ha = hs["gerente"], hs["atendente"]
    assert client.get("/api/estoque/itens", headers=ha).status_code == 403
    assert client.get("/api/compras/fornecedores", headers=ha).status_code == 403
    assert client.post("/api/estoque/locais", json={"nome": "X"}, headers=hs["pizzaiolo"]).status_code == 403
    r = client.post("/api/estoque/locais/iniciar-padrao", headers=h)
    assert r.status_code in (201, 409)
    assert client.post("/api/estoque/locais/iniciar-padrao", headers=h).status_code == 409
    nome = novo_login("Depósito")
    loc = client.post("/api/estoque/locais", json={"nome": nome}, headers=h)
    assert loc.status_code == 201 and client.post("/api/estoque/locais", json={"nome": nome.upper()}, headers=h).status_code == 409
    it = _item(client, h, "insumo", "g")
    cfg = lambda **c: client.put(f"/api/estoque/itens/{it['id']}/config", json=c, headers=h)
    assert cfg(estoque_minimo="500", ponto_pedido="300").status_code == 400  # ponto abaixo do mínimo
    assert cfg(estoque_minimo="100", ponto_pedido="300", estoque_maximo="200").status_code == 400
    ok = cfg(estoque_minimo="100", ponto_pedido="300", estoque_maximo="1000", critico=True, unidade_compra="caixa", fator_compra="12")
    assert ok.status_code == 200 and ok.json()["critico"] is True and ok.json()["fator_compra"] == "12"
    assert cfg(local_padrao_id=99999).status_code == 404
    assert cfg(fator_compra="0").status_code == 422
    assert client.get(f"/api/estoque/itens/{it['id']}", headers=h).json()["controla_lote"] is True  # padrão de insumo


def test_custo_medio_movel_peps_perda_e_transferencia(client, hs):
    h = hs["gerente"]
    it = _item(client, h, "insumo", "kg")
    amanha, depois = date.today() + timedelta(days=1), date.today() + timedelta(days=30)
    _inicial(client, h, it["id"], "10", "2,00", lote_codigo="B", validade=depois.isoformat())
    _inicial(client, h, it["id"], "10", "4,00", lote_codigo="A", validade=amanha.isoformat())
    d = client.get(f"/api/estoque/itens/{it['id']}", headers=h).json()
    assert d["saldo"] == "20" and D(d["ultimos_custos_medios"][0]["custo_medio"]) == D("3")  # (10x2 + 10x4) / 20
    # PEPS: sai primeiro o lote que vence antes (A), mesmo entrado depois
    assert client.post("/api/estoque/movimentos", json={"tipo": "perda", "item_id": it["id"], "quantidade": "4", "motivo": "Caiu no chão"}, headers=h).status_code == 201
    lotes = {x["codigo"]: D(x["saldo"]) for x in client.get(f"/api/estoque/itens/{it['id']}", headers=h).json()["lotes"]}
    assert lotes == {"A": D(6), "B": D(10)}
    assert client.post("/api/estoque/movimentos", json={"tipo": "perda", "item_id": it["id"], "quantidade": "50", "motivo": "x"}, headers=h).status_code == 400  # sem saldo
    assert client.post("/api/estoque/movimentos", json={"tipo": "perda", "item_id": it["id"], "quantidade": "1"}, headers=h).status_code == 400  # sem motivo
    assert client.post("/api/estoque/movimentos", json={"tipo": "entrada_inicial", "item_id": it["id"], "quantidade": "1", "custo_unit": "1", "motivo": "x"}, headers=hs["atendente"]).status_code == 403
    # consumo interno guarda o custo do momento (vai para Custos)
    assert client.post("/api/estoque/movimentos", json={"tipo": "consumo_interno", "item_id": it["id"], "quantidade": "2", "motivo": "Refeição da equipe"}, headers=h).status_code == 201
    m = client.get("/api/estoque/movimentos", params={"item_id": it["id"], "tipo": "consumo_interno"}, headers=h).json()
    assert D(m[0]["custo_unit"]) == D("3") and m[0]["quantidade"] == "-2"
    # transferência entre locais mantém o saldo
    locais = client.get("/api/estoque/locais", headers=h).json()
    a, b = locais[0]["id"], locais[1]["id"]
    antes = _saldo(client, h, it["id"])
    r = client.post("/api/estoque/movimentos", json={"tipo": "transferencia", "item_id": it["id"], "quantidade": "3", "local_id": a, "destino_id": b}, headers=h)
    assert r.status_code in (201, 400)  # 400 se o saldo está em outro local; o importante é nunca criar nem perder
    assert _saldo(client, h, it["id"]) == antes
    assert client.post("/api/estoque/movimentos", json={"tipo": "transferencia", "item_id": it["id"], "quantidade": "3", "local_id": a, "destino_id": a}, headers=h).status_code == 400


def test_inventario_cego_conferencia_e_ajuste(client, hs):
    h = hs["gerente"]
    a, b = _item(client, h, "insumo", "g"), _item(client, h, "embalagem", "un")
    _inicial(client, h, a["id"], "100", "1,00")
    _inicial(client, h, b["id"], "50", "0,50")
    inv = client.post("/api/estoque/inventarios", json={"tipo": "avulso", "item_ids": [a["id"], b["id"]]}, headers=h)
    assert inv.status_code == 201, inv.text
    iid = inv.json()["id"]
    assert client.post("/api/estoque/inventarios", json={"tipo": "avulso", "item_ids": [a["id"]]}, headers=h).status_code == 409  # um por vez
    assert all(x["esperado"] is None for x in inv.json()["linhas"])
    assert client.post(f"/api/estoque/inventarios/{iid}/conferir", headers=h).status_code == 400  # nada contado
    r = client.put(f"/api/estoque/inventarios/{iid}/contagem", json={"linhas": [{"item_id": a["id"], "contado": "90"}, {"item_id": b["id"], "contado": "55"}]}, headers=h)
    assert r.status_code == 200 and all(x["esperado"] is None for x in r.json()["linhas"])  # contagem cega
    assert client.put(f"/api/estoque/inventarios/{iid}/contagem", json={"linhas": [{"item_id": 99999, "contado": "1"}]}, headers=h).status_code == 400
    assert client.post(f"/api/estoque/inventarios/{iid}/fechar", json={}, headers=h).status_code == 409  # antes de conferir
    conf = client.post(f"/api/estoque/inventarios/{iid}/conferir", headers=h).json()
    dif = {x["item_id"]: (x["esperado"], x["diferenca"]) for x in conf["linhas"]}
    assert dif[a["id"]] == ("100", "-10") and dif[b["id"]] == ("50", "5")
    assert client.put(f"/api/estoque/inventarios/{iid}/contagem", json={"linhas": [{"item_id": a["id"], "contado": "99"}]}, headers=h).status_code == 409
    assert client.post(f"/api/estoque/inventarios/{iid}/fechar", json={"motivos": [{"item_id": a["id"], "motivo": "Quebra"}]}, headers=h).status_code == 400  # falta o motivo do b
    assert client.post(f"/api/estoque/inventarios/{iid}/fechar", json={"motivos": [{"item_id": a["id"], "motivo": "Quebra"}, {"item_id": b["id"], "motivo": "Contagem anterior errada"}]}, headers=hs["atendente"]).status_code == 403
    fim = client.post(f"/api/estoque/inventarios/{iid}/fechar", json={"motivos": [{"item_id": a["id"], "motivo": "Quebra"}, {"item_id": b["id"], "motivo": "Contagem anterior errada"}]}, headers=h)
    assert fim.status_code == 200 and fim.json()["situacao"] == "fechado"
    assert _saldo(client, h, a["id"]) == 90 and _saldo(client, h, b["id"]) == 55  # o saldo passa a ser o contado


def test_diario_usa_so_itens_criticos(client, hs):
    h = hs["gerente"]
    crit = _item(client, h, "insumo", "g")
    client.put(f"/api/estoque/itens/{crit['id']}/config", json={"critico": True}, headers=h)
    inv = client.post("/api/estoque/inventarios", json={"tipo": "diario"}, headers=h)
    assert inv.status_code == 201 and crit["id"] in [x["item_id"] for x in inv.json()["linhas"]]
    assert all(client.get(f"/api/estoque/itens/{x['item_id']}", headers=h).json()["critico"] for x in inv.json()["linhas"])
    client.put(f"/api/estoque/inventarios/{inv.json()['id']}/contagem", json={"linhas": [{"item_id": crit["id"], "contado": "0"}]}, headers=h)
    client.post(f"/api/estoque/inventarios/{inv.json()['id']}/conferir", headers=h)
    assert client.post(f"/api/estoque/inventarios/{inv.json()['id']}/fechar", json={}, headers=h).status_code == 200


def test_baixa_pela_ficha_ao_acabar_perda_e_sem_ficha(client, cardapio, hs, conn_teste):
    h, adm = hs["gerente"], hs["administrador"]
    queijo = _item(client, h, "insumo", "g")
    _inicial(client, h, queijo["id"], "10000", "0,05")
    sabor = cardapio["trad"]
    assert _ficha(client, h, f"produto/{sabor['id']}", [{"item_id": queijo["id"], "quantidade": "100", "perda_pct": "10"}]).status_code == 200
    # Grande de um sabor = 2 meias = 200 g, mais 10% de perda = 220 g
    ped = _pagar(client, hs["atendente"], [{"tipo": "pizza", "produto_id": sabor["id"], "tamanho": "grande", "quantidade": 1}])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert p["pedido_id"] == ped["id"]
    assert _saldo(client, h, queijo["id"]) == 10000  # nada sai antes de acabar
    _ate_acabar(client, hs, p["id"])
    assert _saldo(client, h, queijo["id"]) == 10000 - 220
    n = conn_teste.execute("SELECT count(*) FROM movimento_estoque WHERE item_id = %s AND tipo = 'saida_venda'", (queijo["id"],)).fetchone()[0]
    assert n >= 1
    # Perdida depois de montada: consome a montagem como perda, uma vez só
    _pagar(client, hs["atendente"], [{"tipo": "pizza", "produto_id": sabor["id"], "tamanho": "broto", "quantidade": 1}])
    p2 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    m = _motivos(client, h)
    assert client.post(f"/api/producao/pizzas/{p2['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 200
    assert _saldo(client, h, queijo["id"]) == 10000 - 220 - 110
    assert conn_teste.execute("SELECT count(*) FROM movimento_estoque WHERE item_id = %s AND tipo = 'perda'", (queijo["id"],)).fetchone()[0] == 1
    # Produto sem ficha não trava a produção: vira pendência à vista
    c = _cat(client, adm)
    sem = _pizza(client, adm, c["id"])
    _pagar(client, hs["atendente"], [{"tipo": "pizza", "produto_id": sem["id"], "tamanho": "grande", "quantidade": 1}])
    p3 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    _ate_acabar(client, hs, p3["id"])
    al = client.get("/api/estoque/alertas", headers=h).json()
    assert any(x["produto_id"] == sem["id"] and x["tipo"] == "sem_ficha" for x in al["pendencias"])


def test_bebida_baixa_ao_acabar_o_pedido(client, cardapio, hs, conn_teste):
    h = hs["gerente"]
    lata = _item(client, h, "revenda", "un")
    _inicial(client, h, lata["id"], "20", "3,00")
    assert _ficha(client, h, f"produto/{cardapio['beb']['id']}", [{"item_id": lata["id"], "quantidade": "1", "perda_pct": "0"}]).status_code == 200
    ped = _pagar(client, hs["atendente"], [{"tipo": "bebida", "produto_id": cardapio["beb"]["id"], "quantidade": 3}])
    for s in ("em producao", "acabado"):
        assert client.post(f"/api/pedidos/{ped['id']}/situacao", json={"situacao": s}, headers=h).status_code == 200
    assert _saldo(client, h, lata["id"]) == 17


def test_alertas_repor_e_validade(client, hs):
    h = hs["gerente"]
    it = _item(client, h, "insumo", "g")
    client.put(f"/api/estoque/itens/{it['id']}/config", json={"estoque_minimo": "500", "ponto_pedido": "1000"}, headers=h)
    _inicial(client, h, it["id"], "800", "0,01", lote_codigo="V1", validade=(date.today() + timedelta(days=2)).isoformat())
    al = client.get("/api/estoque/alertas", headers=h).json()
    assert any(x["id"] == it["id"] and x["situacao"] == "repor" for x in al["repor"])
    assert any(x["item_id"] == it["id"] and x["vencido"] is False for x in al["validade"])


# ---------------------------------------------------------------- compras
def _forn(client, h, **kw):
    r = client.post("/api/compras/fornecedores", json={"nome": novo_login("Forn"), **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_fornecedores_cadastro_e_validacao(client, hs):
    h = hs["gerente"]
    f = _forn(client, h, prazo_dias=14, forma_pagamento="boleto")
    assert client.post("/api/compras/fornecedores", json={"nome": f["nome"].upper()}, headers=h).status_code == 409
    assert client.post("/api/compras/fornecedores", json={"nome": "X", "forma_pagamento": "cheque"}, headers=h).status_code == 422
    assert client.post("/api/compras/fornecedores", json={"nome": "X", "prazo_dias": 999}, headers=h).status_code == 422
    assert client.post("/api/compras/fornecedores", json={"nome": "Y"}, headers=hs["atendente"]).status_code == 403
    assert client.patch(f"/api/compras/fornecedores/{f['id']}", json={"ativo": False}, headers=h).json()["ativo"] is False


def test_lista_cotacao_mapa_definicao_aprovacao_pedido_e_recebimento(client, hs):
    h, hsub = hs["gerente"], hs["subgerente"]
    f1, f2 = _forn(client, h, prazo_dias=7, forma_pagamento="boleto"), _forn(client, h)
    queijo, tomate, avulso = (_item(client, h, "insumo", "kg") for _ in range(3))
    client.put(f"/api/estoque/itens/{queijo['id']}/config", json={"estoque_minimo": "10", "ponto_pedido": "20", "estoque_maximo": "50", "unidade_compra": "caixa", "fator_compra": "5"}, headers=h)
    _inicial(client, h, queijo["id"], "5", "10,00")  # abaixo do ponto: o sistema sugere 45, arredondado a caixas de 5
    prev = {x["item_id"]: x for x in client.get("/api/compras/necessidades", headers=h).json()}
    assert prev[queijo["id"]]["quantidade"] == "45" and prev[queijo["id"]]["origem"] == "minimo"
    assert tomate["id"] not in prev
    lista = client.post("/api/compras/listas", json={"itens": [{"item_id": tomate["id"], "quantidade": "20"}]}, headers=h)
    assert lista.status_code == 201, lista.text
    lid = lista.json()["id"]
    for outro in lista.json()["itens"]:  # sobras de outros testes no mesmo banco: tira da lista, com motivo
        if outro["item_id"] not in (queijo["id"], tomate["id"]):
            assert client.patch(f"/api/compras/listas/{lid}/itens/{outro['id']}", json={"removido": True, "motivo": "fora do teste"}, headers=h).status_code == 200
    its = {i["item_id"]: i for i in client.get(f"/api/compras/listas/{lid}", headers=h).json()["itens"] if not i["removido"]}
    assert its[queijo["id"]]["origem"] == "minimo" and its[tomate["id"]]["origem"] == "manual"
    # acrescentar avulso e remover/ajustar com motivo
    assert client.post(f"/api/compras/listas/{lid}/itens", json={"item_id": avulso["id"], "quantidade": "2"}, headers=h).status_code == 201
    assert client.post(f"/api/compras/listas/{lid}/itens", json={"item_id": avulso["id"], "quantidade": "2"}, headers=h).status_code == 409
    liq = its[queijo["id"]]["id"]
    assert client.patch(f"/api/compras/listas/{lid}/itens/{liq}", json={"quantidade": "30"}, headers=h).status_code == 400  # sugerido: exige motivo
    assert client.patch(f"/api/compras/listas/{lid}/itens/{liq}", json={"quantidade": "30", "motivo": "Sem espaço no freezer"}, headers=h).status_code == 200
    det = client.get(f"/api/compras/listas/{lid}", headers=h).json()
    avu = next(i for i in det["itens"] if i["item_id"] == avulso["id"])
    assert client.patch(f"/api/compras/listas/{lid}/itens/{avu['id']}", json={"removido": True}, headers=h).status_code == 200  # manual sai sem motivo
    txt = client.get(f"/api/compras/listas/{lid}/por-fornecedor", headers=h).json()
    assert "caixa" in txt["texto"] and txt["itens"] == 2
    # cotação: preço por caixa de 5, convertido ao quilo
    liq, lit = liq, its[tomate["id"]]["id"]
    assert client.post(f"/api/compras/listas/{lid}/cotacoes", json={"lista_item_id": liq, "fornecedor_id": f1["id"], "preco": "60,00", "prazo_dias": 7}, headers=h).status_code == 201
    assert client.post(f"/api/compras/listas/{lid}/cotacoes", json={"lista_item_id": liq, "fornecedor_id": f2["id"], "preco": "50,00"}, headers=h).status_code == 201
    assert client.post(f"/api/compras/listas/{lid}/cotacoes", json={"lista_item_id": lit, "fornecedor_id": f1["id"], "preco": "4,00"}, headers=h).status_code == 201
    mapa = {m["item"]: m for m in client.get(f"/api/compras/listas/{lid}/mapa", headers=h).json()}
    mq = mapa[next(i["item"] for i in det["itens"] if i["item_id"] == queijo["id"])]
    assert mq["mais_barato"] == f2["id"] and D(mq["cotacoes"][0]["preco_unit"]) == D("10") and len(mq["ultimos_precos"]) == 0
    assert client.get(f"/api/compras/listas/{lid}", headers=h).json()["situacao"] == "cotando"
    # definição: divide o queijo entre dois fornecedores; soma errada é recusada; tomate sem cotação do f2 exige preço
    base = [{"lista_item_id": liq, "fornecedor_id": f2["id"], "quantidade": "20"}, {"lista_item_id": liq, "fornecedor_id": f1["id"], "quantidade": "10"},
            {"lista_item_id": lit, "fornecedor_id": f1["id"], "quantidade": "20"}]
    assert client.post(f"/api/compras/listas/{lid}/definir", json={"escolhas": base[:2]}, headers=h).status_code == 400  # tomate sem fornecedor
    assert client.post(f"/api/compras/listas/{lid}/definir", json={"escolhas": [{**base[0], "quantidade": "25"}, *base[1:]]}, headers=h).status_code == 400  # soma 55 diferente de 30
    assert client.post(f"/api/compras/listas/{lid}/definir", json={"escolhas": [{**base[2], "fornecedor_id": f2["id"]}, *base[:2]]}, headers=h).status_code == 400  # sem preço
    # total: queijo 20x10 + 10x12 = 320; tomate 20x4 = 80 => 400, acima de 100: outra pessoa aprova
    r = client.post(f"/api/compras/listas/{lid}/definir", json={"escolhas": base}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["situacao"] == "definida" and r.json()["total"] == "400.00" and r.json()["pedidos"] == []
    assert client.post(f"/api/compras/listas/{lid}/aprovar", headers=h).status_code == 403  # quem montou não aprova
    assert client.post(f"/api/compras/listas/{lid}/aprovar", headers=hs["atendente"]).status_code == 403
    ap = client.post(f"/api/compras/listas/{lid}/aprovar", headers=hsub)
    assert ap.status_code == 200 and ap.json()["situacao"] == "aprovada" and len(ap.json()["pedidos"]) == 2
    assert client.post(f"/api/compras/listas/{lid}/itens", json={"item_id": avulso["id"], "quantidade": "1"}, headers=h).status_code == 409
    assert client.post(f"/api/compras/listas/{lid}/cancelar", headers=h).status_code == 409
    # recebimento do pedido do f2 (queijo 20 kg a 10,00/kg), com lote e validade
    ped = next(p for p in ap.json()["pedidos"] if p["fornecedor_id"] == f2["id"])
    pd = client.get(f"/api/compras/pedidos/{ped['id']}", headers=h).json()
    assert pd["itens"][0]["quantidade"] == "20" and D(pd["itens"][0]["preco_unit"]) == D("10") and pd["situacao"] == "emitido"
    rec = {"pedido_id": ped["id"], "data_nota": date.today().isoformat(), "numero_nota": novo_login("NF"),
           "itens": [{"item_id": queijo["id"], "quantidade": "12", "preco": "50,00", "lote_codigo": "Q1", "validade": (date.today() + timedelta(days=60)).isoformat()}]}
    assert client.post("/api/compras/recebimentos", json=rec, headers=h).status_code == 400  # falta 8: exige motivo da diferença
    rec["itens"][0]["diferenca_motivo"] = "Entrega parcial"
    r1 = client.post("/api/compras/recebimentos", json=rec, headers=h)
    assert r1.status_code == 201, r1.text
    assert r1.json()["total_nota"] == "120.00" and r1.json()["forma_pagamento"] is None
    assert client.get(f"/api/compras/pedidos/{ped['id']}", headers=h).json()["situacao"] == "parcial"
    assert _saldo(client, h, queijo["id"]) == 17  # 5 + 12
    assert client.post("/api/compras/recebimentos", json=rec, headers=h).status_code == 409  # mesma nota de novo
    rec2 = {**rec, "numero_nota": novo_login("NF"), "itens": [{**rec["itens"][0], "quantidade": "8", "lote_codigo": "Q2", "diferenca_motivo": None}]}
    r2 = client.post("/api/compras/recebimentos", json=rec2, headers=h)
    assert r2.status_code == 201, r2.text
    assert client.get(f"/api/compras/pedidos/{ped['id']}", headers=h).json()["situacao"] == "recebido"
    assert client.post("/api/compras/recebimentos", json={**rec2, "numero_nota": novo_login("NF")}, headers=h).status_code == 409  # pedido já recebido
    d = client.get(f"/api/estoque/itens/{queijo['id']}", headers=h).json()
    assert d["saldo"] == "25" and len(d["ultimos_precos_pagos"]) == 2 and D(d["ultimos_precos_pagos"][0]["preco_unit"]) == D("10")
    # custo médio: (5x10 + 12x10 + 8x10)/25 = 10
    assert D(d["ultimos_custos_medios"][0]["custo_medio"]) == D("10")
    assert any(r["numero_nota"] == rec["numero_nota"] for r in client.get("/api/compras/recebimentos", headers=h).json())


def test_lista_abaixo_do_limite_sai_direto_e_pedido_direto(client, hs):
    h = hs["gerente"]
    f = _forn(client, h, prazo_dias=10, forma_pagamento="prazo")
    it = _item(client, h, "insumo", "un")
    client.put(f"/api/estoque/itens/{it['id']}/config", json={"fornecedor_habitual_id": f["id"]}, headers=h)
    lista = client.post("/api/compras/listas", json={"incluir_sugeridos": False, "itens": [{"item_id": it["id"], "quantidade": "10"}]}, headers=h).json()
    li = lista["itens"][0]["id"]
    # fornecedor habitual sem cotação e sem histórico: precisa de preço
    assert client.post(f"/api/compras/listas/{lista['id']}/definir", json={"escolhas": [{"lista_item_id": li, "fornecedor_id": f["id"], "quantidade": "10"}]}, headers=h).status_code == 400
    ok = client.post(f"/api/compras/listas/{lista['id']}/definir", json={"escolhas": [{"lista_item_id": li, "fornecedor_id": f["id"], "quantidade": "10", "preco": "5,00"}]}, headers=h)
    assert ok.status_code == 200 and ok.json()["situacao"] == "aprovada" and len(ok.json()["pedidos"]) == 1  # 50,00 está abaixo do limite
    ped = client.get(f"/api/compras/pedidos/{ok.json()['pedidos'][0]['id']}", headers=h).json()
    assert ped["total"] == "50.00"
    assert client.post(f"/api/compras/pedidos/{ped['id']}/cancelar", headers=h).json()["situacao"] == "cancelado"
    assert client.post(f"/api/compras/pedidos/{ped['id']}/cancelar", headers=h).status_code == 409
    # pedido digitado direto, sem lista
    direto = client.post("/api/compras/pedidos", json={"fornecedor_id": f["id"], "itens": [{"item_id": it["id"], "quantidade": "4", "preco": "2,50"}]}, headers=h)
    assert direto.status_code == 201 and direto.json()["total"] == "10.00" and direto.json()["prazo_dias"] == 10
    assert client.get("/api/compras/pedidos", headers=h).status_code == 200
    # lista vazia de necessidades
    assert client.post("/api/compras/listas", json={"incluir_sugeridos": False}, headers=h).status_code == 400


def test_compra_urgente_ligada_a_sangria_e_triggers(client, hs, conn_teste):
    h = hs["gerente"]
    f = _forn(client, h)
    it = _item(client, h, "insumo", "un")
    # sangria de caixa para pagar a compra: exige caixa aberto; abre se ainda não houver
    if client.get("/api/caixa/hoje", headers=h).json()["caixa"] is None:
        client.post("/api/caixa/abrir", json={"fundo_troco": "0,00"}, headers=h)
    cx = client.get("/api/caixa/hoje", headers=h).json()["caixa"]
    if cx is None or cx["situacao"] != "aberto":
        pytest.skip("caixa do dia não está aberto neste ambiente")
    client.post("/api/caixa/motivos/iniciar-padrao", headers=h)
    mot = next(m["id"] for m in client.get("/api/caixa/motivos", headers=h).json() if m["nome"] == "Depósito")
    s = client.post("/api/caixa/movimentos", json={"tipo": "sangria", "valor": "30,00", "motivo_id": mot}, headers=h).json()
    nota = {"fornecedor_id": f["id"], "data_nota": date.today().isoformat(), "movimento_caixa_id": s["id"], "itens": [{"item_id": it["id"], "quantidade": "6", "preco": "4,00"}]}
    assert client.post("/api/compras/recebimentos", json=nota, headers=h).status_code == 400  # 24 contra 30
    nota["itens"][0]["preco"] = "5,00"
    r = client.post("/api/compras/recebimentos", json=nota, headers=h)
    assert r.status_code == 201 and r.json()["forma_pagamento"] == "dinheiro"
    assert client.post("/api/compras/recebimentos", json={**nota, "numero_nota": "OUTRA"}, headers=h).status_code in (409, 400)  # a sangria paga uma nota só
    import psycopg
    for sql in ("UPDATE movimento_estoque SET quantidade = 1", "DELETE FROM movimento_estoque", "TRUNCATE movimento_estoque", "UPDATE custo_item SET custo_medio = 0",
                "UPDATE preco_compra SET preco_unit = 0", "UPDATE recebimento SET total_nota = 0", "DELETE FROM recebimento_item", "UPDATE cotacao_resposta SET preco_unit = 1",
                "UPDATE lote_estoque SET codigo = 'x'", "DELETE FROM lote_estoque", "UPDATE lista_compra SET situacao = 'rascunho' WHERE situacao = 'aprovada'",
                "UPDATE pedido_compra SET total = 1", "DELETE FROM pedido_compra", "UPDATE inventario SET situacao = 'aberto' WHERE situacao = 'fechado'",
                "DELETE FROM inventario_linha", "DELETE FROM baixa_origem", "DELETE FROM pendencia_estoque"):
        with pytest.raises(psycopg.Error):
            conn_teste.execute(sql)
            assert conn_teste.execute("SELECT 1").fetchone() and False, sql  # se nenhuma linha casou, o comando não falha: força o teste a notar
