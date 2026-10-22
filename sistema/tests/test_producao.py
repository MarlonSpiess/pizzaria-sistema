import pytest

from tests.conftest import criar_usuario_direto, entrar, novo_login
from tests.test_cadastros import _adic, _cat, _pizza
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

PARAMS = {"forno_pizzas_por_vez": "2", "calzone_massa_tamanho": "broto", "producao_montagem_min": "3", "producao_pizzaiolos_ativos": "2",
          "producao_acabamento_min": "2", "entrega_deslocamento_min": "10", "limite_desconto_gerente_pct": "20"}


@pytest.fixture(scope="module", autouse=True)
def parametros(client):
    _, h = entrar(client, "administrador")
    for k, v in PARAMS.items():
        assert client.put(f"/api/parametros/{k}", json={"valor": v}, headers=h).status_code == 200
    assert client.post("/api/producao/motivos/iniciar-padrao", headers=h).status_code in (201, 409)
    yield
    for k in PARAMS:
        client.put(f"/api/parametros/{k}", json={"valor": None}, headers=h)


@pytest.fixture(autouse=True)
def fila_limpa(conn_teste):
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'cancelada' WHERE situacao IN ('na lista','em montagem','no forno','saiu do forno')")
    yield


@pytest.fixture
def hs(client):
    return {p: entrar(client, p)[1] for p in ("atendente", "gerente", "pizzaiolo", "acabamento", "massa")}


def _motivos(client, h):
    m = client.get("/api/producao/motivos", headers=h).json()
    return {"retro": next(x["id"] for x in m["retrocesso"] if x["ativo"]), "perda": next(x["id"] for x in m["perda"] if x["ativo"])}


def _pedido(client, h, itens, **extra):
    r = client.post("/api/pedidos", json={"itens": itens, "pagamentos": [{"forma": "pix", "valor": "9999,00"}], **extra}, headers=h)
    if r.status_code == 400:  # pagamento de teste só precisa cobrir o total; ajusta para o total exato
        total = client.post("/api/pedidos/calcular", json={"itens": itens, "tipo": extra.get("tipo", "retirada")}, headers=h).json()["total"]
        r = client.post("/api/pedidos", json={"itens": itens, "pagamentos": [{"forma": "pix", "valor": total}], **extra}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _pagar(client, h, itens, **extra):
    total = client.post("/api/pedidos/calcular", json={"itens": itens, **{k: v for k, v in extra.items() if k == "tipo"}}, headers=h).json()["total"]
    r = client.post("/api/pedidos", json={"itens": itens, "pagamentos": [{"forma": "pix", "valor": total}], **extra}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _g(c, qtd=1, **kw):
    return {"tipo": "pizza", "produto_id": c["trad"]["id"], "tamanho": "grande", "quantidade": qtd, **kw}


def _fila(client, h):
    return client.get("/api/producao/fila", headers=h).json()


def test_gera_uma_pizza_por_unidade_e_ignora_bebida(client, cardapio, hs):
    c = cardapio
    p = _pagar(client, hs["atendente"], [_g(c, 2), {"tipo": "calzone", "produto_id": c["calz"]["id"]}, {"tipo": "bebida", "produto_id": c["beb"]["id"], "quantidade": 3}])
    fila = _fila(client, hs["pizzaiolo"])["pizzas"]
    mias = [x for x in fila if x["pedido_id"] == p["id"]]
    assert len(mias) == 3 and sorted(x["tipo"] for x in mias) == ["calzone", "pizza", "pizza"]
    assert all(x["situacao"] == "na lista" for x in mias)


def test_pizzaiolo_recebe_a_proxima_urgente_primeiro_e_pedido_entra_em_producao(client, cardapio, hs):
    c = cardapio
    a = _pagar(client, hs["atendente"], [_g(c)])
    b = _pagar(client, hs["atendente"], [_g(c)])
    assert client.post(f"/api/pedidos/{b['id']}/urgente", json={"urgente": True}, headers=hs["atendente"]).status_code == 200
    p1 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert p1["pedido_id"] == b["id"] and p1["situacao"] == "em montagem"
    assert client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()["id"] == p1["id"]  # a mesma até terminar
    assert client.get(f"/api/pedidos/{b['id']}", headers=hs["gerente"]).json()["situacao"] == "em producao"
    assert client.get(f"/api/pedidos/{a['id']}", headers=hs["gerente"]).json()["situacao"] == "recebido"


def test_dois_pizzaiolos_recebem_pizzas_diferentes(client, cardapio, hs):
    _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    outro = entrar(client, "pizzaiolo")[1]
    p1 = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    p2 = client.post("/api/producao/pizzas/proxima", headers=outro).json()
    assert p1["id"] != p2["id"]
    assert client.post(f"/api/producao/pizzas/{p1['id']}/produzida", headers=outro).status_code == 403  # é do outro
    assert client.post("/api/producao/pizzas/proxima", headers=entrar(client, "pizzaiolo")[1]).status_code == 404  # lista vazia


def test_produzida_vai_ao_forno_e_estados_errados_dao_409(client, cardapio, hs):
    _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p['id']}/acabada", headers=hs["acabamento"]).status_code == 409
    assert client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"]).status_code == 200
    assert client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"]).status_code == 409


def test_retroceder_volta_uma_posicao_e_exige_motivo_da_tabela(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    ped = _pagar(client, hs["atendente"], [_g(cardapio, 3)])
    a = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{a['id']}/retroceder", json={"motivo_id": 999999}, headers=hs["pizzaiolo"]).status_code == 404
    assert client.post(f"/api/producao/pizzas/{a['id']}/retroceder", json={}, headers=hs["pizzaiolo"]).status_code == 422
    r = client.post(f"/api/producao/pizzas/{a['id']}/retroceder", json={"motivo_id": m["retro"]}, headers=hs["pizzaiolo"])
    assert r.status_code == 200 and r.json()["situacao"] == "na lista"
    ordem = [x["id"] for x in _fila(client, hs["pizzaiolo"])["pizzas"] if x["pedido_id"] == ped["id"]]
    assert ordem.index(a["id"]) == 1  # uma posição abaixo: a segunda da lista


def test_forno_avisa_acima_da_capacidade_e_acabamento_gera_etiqueta(client, cardapio, hs):
    _pagar(client, hs["atendente"], [_g(cardapio, 3)])
    ids = []
    for _ in range(3):
        p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
        client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"])
        ids.append(p["id"])
    assert _fila(client, hs["acabamento"])["forno"] == {"quantidade": 3, "capacidade": 2, "tempo_min": "2", "acima_capacidade": True}
    assert client.post(f"/api/producao/pizzas/{ids[0]}/acabada", headers=hs["acabamento"]).status_code == 409  # ainda no forno
    assert client.post(f"/api/producao/pizzas/{ids[0]}/saiu-do-forno", headers=hs["acabamento"]).status_code == 200
    assert client.post(f"/api/producao/pizzas/{ids[0]}/acabada", headers=hs["pizzaiolo"]).status_code == 403
    r = client.post(f"/api/producao/pizzas/{ids[0]}/acabada", headers=hs["acabamento"]).json()
    assert r["situacao"] == "acabada" and r["etiqueta"]["id_dia"] >= 1 and r["etiqueta"]["cliente"] == "Balcão"


def test_pedido_so_acaba_a_mao_e_com_todas_as_pizzas(client, cardapio, hs):
    ped = _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    ids = []
    for _ in range(2):
        p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
        for rota, h in (("produzida", hs["pizzaiolo"]), ("saiu-do-forno", hs["acabamento"])):
            client.post(f"/api/producao/pizzas/{p['id']}/{rota}", headers=h)
        ids.append(p["id"])
    client.post(f"/api/producao/pizzas/{ids[0]}/acabada", headers=hs["acabamento"])
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["acabamento"]).status_code == 409  # falta uma
    assert client.get(f"/api/pedidos/{ped['id']}", headers=hs["gerente"]).json()["situacao"] == "em producao"  # nunca sozinho
    client.post(f"/api/producao/pizzas/{ids[1]}/acabada", headers=hs["acabamento"])
    assert client.get(f"/api/pedidos/{ped['id']}", headers=hs["gerente"]).json()["situacao"] == "em producao"
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["pizzaiolo"]).status_code == 403
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["acabamento"]).json()["situacao"] == "acabado"
    ev = [e["situacao"] for e in client.get(f"/api/pedidos/{ped['id']}", headers=hs["gerente"]).json()["eventos"]]
    assert ev == ["recebido", "em producao", "acabado"]
    # o balcão marca despachado ou retirado e grava a hora real
    r = client.post(f"/api/pedidos/{ped['id']}/situacao", json={"situacao": "despachado ou retirado"}, headers=hs["atendente"])
    assert r.status_code == 200 and r.json()["entrega_real"]


def test_refacao_liga_a_original_vai_a_frente_e_conta_para_acabar(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    ped = _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    for rota, h in (("produzida", hs["pizzaiolo"]), ("saiu-do-forno", hs["acabamento"])):
        client.post(f"/api/producao/pizzas/{p['id']}/{rota}", headers=h)
    assert client.post(f"/api/producao/pizzas/{p['id']}/refazer", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 403
    r = client.post(f"/api/producao/pizzas/{p['id']}/refazer", json={"motivo_id": m["perda"]}, headers=hs["acabamento"])
    assert r.status_code == 201 and r.json()["original_id"] == p["id"]
    assert client.post(f"/api/producao/pizzas/{p['id']}/refazer", json={"motivo_id": m["perda"]}, headers=hs["acabamento"]).status_code == 409
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["acabamento"]).status_code == 409  # a nova ainda não acabou
    nova = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert nova["id"] == r.json()["id"]


def test_perda_de_pizza_exige_motivo_ativo(client, cardapio, hs, conn_teste):
    m = _motivos(client, hs["gerente"])
    _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p['id']}/perder", json={"motivo_id": 999999}, headers=hs["pizzaiolo"]).status_code == 404
    assert client.post(f"/api/producao/pizzas/{p['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 200
    assert conn_teste.execute("SELECT count(*) FROM perda WHERE pizza_id = %s", (p["id"],)).fetchone()[0] == 1
    assert client.post(f"/api/producao/pizzas/{p['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 409


def test_cancelar_pedido_cancela_o_que_nao_comecou_e_perde_o_que_foi_feito(client, cardapio, hs, conn_teste):
    ped = _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"])
    assert client.post(f"/api/pedidos/{ped['id']}/cancelar", json={"motivo": "Cliente desistiu"}, headers=hs["gerente"]).status_code == 200
    sit = {r[0]: r[1] for r in conn_teste.execute("SELECT id, situacao FROM pizza_producao WHERE pedido_id = %s", (ped["id"],)).fetchall()}
    assert sorted(sit.values()) == ["cancelada", "perdida"] and sit[p["id"]] == "perdida"
    assert conn_teste.execute("SELECT count(*) FROM perda WHERE pizza_id = %s", (p["id"],)).fetchone()[0] == 1
    assert client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).status_code == 404  # nada a produzir


def test_saldo_de_massa_contagem_lote_uso_e_perda(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    assert client.post("/api/producao/massa/contagem", json={"tamanho": "grande", "quantidade": 5}, headers=hs["massa"]).status_code == 201
    r = client.post("/api/producao/massa/lote", json={"tamanho": "grande", "quantidade": 10}, headers=hs["massa"]).json()
    assert r["grande"]["saldo"] == 15
    _pagar(client, hs["atendente"], [_g(cardapio, 2), {"tipo": "calzone", "produto_id": cardapio["calz"]["id"]}])
    r = client.get("/api/producao/massa", headers=hs["massa"]).json()
    assert r["grande"]["necessidade"] == 2 and r["grande"]["falta"] == 0 and r["broto"]["necessidade"] == 1  # calzone usa broto (parâmetro)
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    client.post(f"/api/producao/pizzas/{p['id']}/produzida", headers=hs["pizzaiolo"])
    assert client.get("/api/producao/massa", headers=hs["massa"]).json()["grande"]["saldo"] == 14
    assert client.post("/api/producao/massa/perda", json={"tamanho": "grande", "quantidade": 2, "motivo_id": m["perda"]}, headers=hs["massa"]).json()["grande"]["saldo"] == 12
    assert client.post("/api/producao/massa/contagem", json={"tamanho": "grande", "quantidade": 3}, headers=hs["massa"]).json()["grande"]["saldo"] == 3
    assert client.post("/api/producao/massa/lote", json={"tamanho": "media", "quantidade": 1}, headers=hs["massa"]).status_code == 422
    assert client.post("/api/producao/massa/lote", json={"tamanho": "grande", "quantidade": 0}, headers=hs["massa"]).status_code == 422


def test_permissoes_por_funcao(client, cardapio, hs):
    assert client.post("/api/producao/massa/lote", json={"tamanho": "grande", "quantidade": 1}, headers=hs["pizzaiolo"]).status_code == 403
    assert client.post("/api/producao/pizzas/proxima", headers=hs["massa"]).status_code == 403
    assert client.post("/api/producao/pizzas/proxima", headers=hs["acabamento"]).status_code == 403
    assert client.post("/api/producao/pizzas/proxima", headers=hs["atendente"]).status_code == 403
    assert client.get("/api/producao/fila", headers=hs["atendente"]).status_code == 200  # consulta
    assert client.post("/api/producao/motivos/perda", json={"nome": "X"}, headers=hs["atendente"]).status_code == 403
    assert client.get("/api/producao/fila").status_code == 401
    assert client.get("/api/pedidos", headers=hs["pizzaiolo"]).status_code == 403  # produção não vê vendas


def test_motivos_sao_tabela_editavel(client, hs):
    h = hs["gerente"]
    nome = novo_login("motivo")
    r = client.post("/api/producao/motivos/retrocesso", json={"nome": nome, "avisa_estoque": True}, headers=h)
    assert r.status_code == 201 and r.json()["avisa_estoque"] is True
    assert client.post("/api/producao/motivos/retrocesso", json={"nome": nome.upper()}, headers=h).status_code == 409
    assert client.post("/api/producao/motivos/xx", json={"nome": "A"}, headers=h).status_code == 404
    mid = r.json()["id"]
    assert client.patch(f"/api/producao/motivos/retrocesso/{mid}", json={"ativo": False}, headers=h).json()["ativo"] is False
    assert client.post("/api/producao/pizzas/1/retroceder", json={"motivo_id": mid}, headers=hs["pizzaiolo"]).status_code in (404, 400, 409)
    assert client.patch(f"/api/producao/motivos/perda/{mid}", json={}, headers=h).status_code == 400
    assert client.post("/api/producao/motivos/iniciar-padrao", headers=h).status_code == 409  # já existem


def test_estimativa_de_entrega_usa_os_parametros(client, cardapio, hs):
    ped = _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    assert client.get(f"/api/pedidos/{ped['id']}", headers=hs["gerente"]).json()["entrega_calculada"] is not None
    assert ped["entrega_calculada"] is not None


def test_banco_protege_a_pizza_e_o_historico(client, cardapio, hs, conn_teste):
    import psycopg
    _pagar(client, hs["atendente"], [_g(cardapio)])
    pid = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()["id"]
    for sql in ("UPDATE pizza_producao SET sabores = 'x' WHERE id = %s", "DELETE FROM pizza_producao WHERE id = %s",
                "UPDATE evento_producao SET situacao = 'x' WHERE pizza_id = %s", "DELETE FROM evento_producao WHERE pizza_id = %s"):
        with pytest.raises(psycopg.Error):
            conn_teste.execute(sql, (pid,))
    conn_teste.execute("UPDATE pizza_producao SET situacao = 'perdida' WHERE id = %s", (pid,))
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE pizza_producao SET situacao = 'na lista' WHERE id = %s", (pid,))
    eventos = [r[0] for r in conn_teste.execute("SELECT situacao FROM evento_producao WHERE pizza_id = %s ORDER BY id", (pid,)).fetchall()]
    assert eventos[:2] == ["na lista", "em montagem"]


def _ate_acabar(client, hs, pid):
    for rota, h in (("produzida", hs["pizzaiolo"]), ("saiu-do-forno", hs["acabamento"]), ("acabada", hs["acabamento"])):
        assert client.post(f"/api/producao/pizzas/{pid}/{rota}", headers=h).status_code == 200


def test_refacao_so_enquanto_o_pedido_esta_em_producao(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    ped = _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    _ate_acabar(client, hs, p["id"])
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["acabamento"]).status_code == 200
    assert client.post(f"/api/producao/pizzas/{p['id']}/refazer", json={"motivo_id": m["perda"]}, headers=hs["acabamento"]).status_code == 409
    assert client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).status_code == 404


def test_gerencia_nao_marca_acabado_com_pizza_pendente(client, cardapio, hs):
    ped = _pagar(client, hs["atendente"], [_g(cardapio)])
    client.post(f"/api/pedidos/{ped['id']}/situacao", json={"situacao": "em producao"}, headers=hs["gerente"])
    r = client.post(f"/api/pedidos/{ped['id']}/situacao", json={"situacao": "acabado"}, headers=hs["gerente"])
    assert r.status_code == 409


def test_perfil_massa_nao_perde_pizza_e_perda_antes_do_forno_baixa_a_massa(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    client.post("/api/producao/massa/contagem", json={"tamanho": "grande", "quantidade": 5}, headers=hs["massa"])
    _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert client.post(f"/api/producao/pizzas/{p['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["massa"]).status_code == 403
    assert client.post(f"/api/producao/pizzas/{p['id']}/perder", json={"motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 200
    assert client.get("/api/producao/massa", headers=hs["massa"]).json()["grande"]["saldo"] == 4  # a massa da pizza perdida já tinha sido usada
    assert client.post("/api/producao/massa/perda", json={"tamanho": "grande", "quantidade": 1, "motivo_id": m["perda"]}, headers=hs["pizzaiolo"]).status_code == 403


def test_retroceder_respeita_o_grupo_de_urgencia(client, cardapio, hs):
    _pagar(client, hs["atendente"], [_g(cardapio, 2)])
    b = _pagar(client, hs["atendente"], [_g(cardapio, 3)])
    client.post(f"/api/pedidos/{b['id']}/urgente", json={"urgente": True}, headers=hs["atendente"])
    m = _motivos(client, hs["gerente"])
    a = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert a["pedido_id"] == b["id"]
    client.post(f"/api/producao/pizzas/{a['id']}/retroceder", json={"motivo_id": m["retro"]}, headers=hs["pizzaiolo"])
    ordem = [x["id"] for x in _fila(client, hs["pizzaiolo"])["pizzas"] if x["pedido_id"] == b["id"]]
    assert ordem.index(a["id"]) == 1 and len(ordem) == 3


def test_muitos_retrocessos_nao_esgotam_a_ordem(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    _pagar(client, hs["atendente"], [_g(cardapio, 3)])
    ids = []
    for _ in range(26):
        p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
        assert client.post(f"/api/producao/pizzas/{p['id']}/retroceder", json={"motivo_id": m["retro"]}, headers=hs["pizzaiolo"]).status_code == 200
        ids.append(p["id"])
    ordens = [x["ordem"] for x in _fila(client, hs["pizzaiolo"])["pizzas"]]
    assert len(set(ordens)) == len(ordens) == 3


def test_pedidos_abertos_contam_a_refacao_no_lugar_da_original(client, cardapio, hs):
    m = _motivos(client, hs["gerente"])
    ped = _pagar(client, hs["atendente"], [_g(cardapio)])
    p = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    for rota, h in (("produzida", hs["pizzaiolo"]), ("saiu-do-forno", hs["acabamento"])):
        client.post(f"/api/producao/pizzas/{p['id']}/{rota}", headers=h)
    nova = client.post(f"/api/producao/pizzas/{p['id']}/refazer", json={"motivo_id": m["perda"]}, headers=hs["acabamento"]).json()
    linha = next(x for x in client.get("/api/producao/pedidos", headers=hs["acabamento"]).json() if x["id"] == ped["id"])
    assert (linha["pizzas"], linha["acabadas"]) == (1, 0)
    pn = client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).json()
    assert pn["id"] == nova["id"]
    _ate_acabar(client, hs, pn["id"])
    linha = next(x for x in client.get("/api/producao/pedidos", headers=hs["acabamento"]).json() if x["id"] == ped["id"])
    assert (linha["pizzas"], linha["acabadas"]) == (1, 1)
    assert client.post(f"/api/producao/pedidos/{ped['id']}/acabado", headers=hs["acabamento"]).status_code == 200


def test_pegar_e_cancelar_ao_mesmo_tempo_nao_travam_nem_dao_erro_500(client, cardapio, hs):
    from concurrent.futures import ThreadPoolExecutor
    for _ in range(6):
        ped = _pagar(client, hs["atendente"], [_g(cardapio, 2)])
        with ThreadPoolExecutor(2) as ex:
            f1 = ex.submit(lambda: client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"]).status_code)
            f2 = ex.submit(lambda: client.post(f"/api/pedidos/{ped['id']}/cancelar", json={"motivo": "Teste de corrida"}, headers=hs["gerente"]).status_code)
        assert f1.result() in (200, 404) and f2.result() == 200
        sit = client.get(f"/api/pedidos/{ped['id']}", headers=hs["gerente"]).json()["situacao"]
        assert sit == "cancelado"
        restantes = [x for x in _fila(client, hs["pizzaiolo"])["pizzas"] if x["pedido_id"] == ped["id"]]
        assert restantes == []
        client.post("/api/producao/pizzas/proxima", headers=hs["pizzaiolo"])  # libera o pizzaiolo para a próxima rodada, se sobrou algo
