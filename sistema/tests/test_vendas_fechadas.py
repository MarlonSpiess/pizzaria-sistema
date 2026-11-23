"""Fechar vendas por ingrediente, estoque negativo e alertas (decisões de Marlon, 04/11/2026)."""
from tests.conftest import entrar, novo_login
from tests.test_fichas import _cat, _ficha, _item, _pizza
from api.services import canais, ingredientes


def _montar(client, h):
    """Dois sabores com ovo (um deles por um preparo) e um sem ovo."""
    cat = _cat(client, h)["id"]
    ovo, queijo = _item(client, h, nome=novo_login("Ovo")), _item(client, h)
    massa_ovo = _item(client, h, classe="preparo", unidade="g")
    _ficha(client, h, f"preparo/{massa_ovo['id']}", [{"item_id": ovo["id"], "quantidade": "1"}])
    portuguesa, baiana, mussarela = _pizza(client, h, cat), _pizza(client, h, cat), _pizza(client, h, cat)
    _ficha(client, h, f"produto/{portuguesa['id']}", [{"item_id": ovo["id"], "quantidade": "1"}, {"item_id": queijo["id"], "quantidade": "50"}])
    _ficha(client, h, f"produto/{baiana['id']}", [{"item_id": massa_ovo["id"], "quantidade": "10"}])  # usa o ovo por um preparo
    _ficha(client, h, f"produto/{mussarela['id']}", [{"item_id": queijo["id"], "quantidade": "80"}])
    return {"ovo": ovo, "queijo": queijo, "portuguesa": portuguesa, "baiana": baiana, "mussarela": mussarela}


def test_marcar_ingrediente_em_falta_fecha_os_sabores_e_reabre(client, admin):
    _, h = admin
    _, ger = entrar(client, "gerente")
    _, atd = entrar(client, "atendente")
    m = _montar(client, h)
    base = f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}"
    assert client.get(base + "/sabores", headers=atd).status_code == 403
    previa = client.get(base + "/sabores", headers=ger).json()
    assert {s["id"] for s in previa["sabores"]} == {m["portuguesa"]["id"], m["baiana"]["id"]}  # inclui o que usa o ovo por um preparo
    assert client.get("/api/vendas-fechadas/ingredientes?busca=" + m["ovo"]["nome"][:6], headers=ger).json()
    r = client.put(base + "/falta", json={"em_falta": True}, headers=ger).json()
    assert r["mudou"] is True and len(r["sabores"]) == 2
    assert client.put(base + "/falta", json={"em_falta": True}, headers=ger).json()["mudou"] is False  # repetir não duplica
    f = client.get("/api/vendas-fechadas", headers=ger).json()
    assert {s["id"] for s in f["sabores_fechados"]} >= {m["portuguesa"]["id"], m["baiana"]["id"]}
    assert m["mussarela"]["id"] not in {s["id"] for s in f["sabores_fechados"]}
    assert client.put(base + "/falta", json={"em_falta": False}, headers=ger).json()["mudou"] is True
    assert m["portuguesa"]["id"] not in {s["id"] for s in client.get("/api/vendas-fechadas", headers=ger).json()["sabores_fechados"]}
    assert client.put("/api/vendas-fechadas/ingredientes/99999999/falta", json={"em_falta": True}, headers=ger).status_code == 404


class Falso:
    codigo = "anotaai"

    def __init__(self):
        self.chamadas = []

    def configurado(self):
        return True

    def pausar_produto(self, ext):
        self.chamadas.append(("pausar", ext))

    def reabrir_produto(self, ext):
        self.chamadas.append(("reabrir", ext))


def test_sincroniza_pausas_no_canal_e_bloqueia_aceite_sozinho(client, admin, conn_teste):
    from api.database import pool
    _, h = admin
    _, ger = entrar(client, "gerente")
    m = _montar(client, h)
    canal = next(x for x in client.get("/api/canais", headers=h).json() if x["codigo"] == "anotaai")
    for chave, prod in (("PORT", m["portuguesa"]), ("MUSS", m["mussarela"])):
        ext = novo_login(chave)
        m[chave] = ext
        assert client.put(f"/api/canais/{canal['id']}/produtos", json={"produto_id": prod["id"], "id_externo": ext}, headers=h).status_code == 200
    client.put(f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}/falta", json={"em_falta": True}, headers=ger)
    f = Falso()
    try:
        with pool.connection() as conn:
            ingredientes.sincronizar_pausas(conn, canal["id"], f)
            assert ("pausar", m["PORT"]) in f.chamadas and ("pausar", m["MUSS"]) not in f.chamadas
            f.chamadas.clear()
            ingredientes.sincronizar_pausas(conn, canal["id"], f)
            assert f.chamadas == []  # já sincronizado: não repete
            c = {"id": canal["id"], "ativo": True, "aceitar_sozinho": True}
            conn.execute("SELECT 1"); conn.rollback()
            # sabor fechado impede o aceite sozinho (os critérios anteriores são simulados como atendidos)
            orig = (canais.loja_aberta, canais.ultimo_caixa)
            from api.database import hoje
            canais.loja_aberta = lambda conn: True
            canais.ultimo_caixa = lambda conn, loja: {"situacao": "aberto", "data": hoje()}
            try:
                ok, motivo = canais.pode_aceitar_sozinho(conn, c, [m["PORT"]])
                assert not ok and "venda fechada" in motivo and m["ovo"]["nome"] in motivo
                assert canais.pode_aceitar_sozinho(conn, c, [m["MUSS"]]) == (True, None)
            finally:
                canais.loja_aberta, canais.ultimo_caixa = orig
        client.put(f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}/falta", json={"em_falta": False}, headers=ger)
        f.chamadas.clear()
        with pool.connection() as conn:
            ingredientes.sincronizar_pausas(conn, canal["id"], f)
        assert ("reabrir", m["PORT"]) in f.chamadas  # inverso ao reabrir
    finally:
        client.put(f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}/falta", json={"em_falta": False}, headers=ger)


def test_estoque_pode_ficar_negativo_e_o_alerta_classifica(client, admin):
    _, h = admin
    _, ger = entrar(client, "gerente")
    it = _item(client, h)
    assert client.put(f"/api/estoque/itens/{it['id']}/config", json={"estoque_minimo": "100"}, headers=h).status_code == 200
    r = client.post("/api/estoque/movimentos", json={"item_id": it["id"], "tipo": "perda", "quantidade": "30", "motivo": "Caiu no chão"}, headers=ger)
    assert r.status_code == 201 and r.json()["saldo"].startswith("-30")  # sem saldo: não bloqueia, fica negativo
    a = {i["id"]: i for i in client.get("/api/estoque/alertas", headers=ger).json()["repor"]}
    assert a[it["id"]]["situacao"] == "negativo"
    cima = list(a.values())[0]
    assert cima["situacao"] == "negativo"  # os piores primeiro
    for perfil in ("atendente", "massa", "pizzaiolo", "acabamento"):
        assert client.get("/api/estoque/alertas", headers=entrar(client, perfil)[1]).status_code == 403


def test_balcao_bloqueia_sabor_fechado_e_vende_o_que_so_esta_com_estoque_baixo(client, admin):
    _, h = admin
    _, ger = entrar(client, "gerente")
    _, atd = entrar(client, "atendente")
    m = _montar(client, h)
    pz = lambda p, **x: {"itens": [{"tipo": "pizza", "produto_id": p["id"], "tamanho": "grande", **x}]}
    assert client.post("/api/pedidos/calcular", json=pz(m["portuguesa"]), headers=atd).status_code == 200  # aberto
    client.put(f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}/falta", json={"em_falta": True}, headers=ger)
    try:
        r = client.post("/api/pedidos/calcular", json=pz(m["portuguesa"]), headers=atd)  # calcula e avisa, para a tela deixar remover
        assert r.status_code == 200 and "Venda fechada" in r.json()["aviso_venda_fechada"]
        r2 = client.post("/api/pedidos/calcular", json=pz(m["mussarela"], sabor2_id=m["baiana"]["id"]), headers=atd)  # 2o sabor
        assert r2.status_code == 200 and "Venda fechada" in r2.json()["aviso_venda_fechada"]
        assert client.post("/api/pedidos", json={**pz(m["portuguesa"]), "pagamentos": [{"forma": "pix", "valor": "35,00"}]}, headers=atd).status_code == 409
        assert client.post("/api/pedidos", json={**pz(m["baiana"]), "pagamentos": [{"forma": "pix", "valor": "35,00"}]}, headers=atd).status_code == 409
        assert client.post("/api/pedidos/calcular", json=pz(m["mussarela"]), headers=atd).status_code == 200
        lista = {p["id"]: p for p in client.get("/api/produtos?tipo=pizza", headers=atd).json()}
        assert lista[m["portuguesa"]["id"]]["venda_fechada"] is True and lista[m["mussarela"]["id"]]["venda_fechada"] is False
    finally:
        client.put(f"/api/vendas-fechadas/ingredientes/{m['ovo']['id']}/falta", json={"em_falta": False}, headers=ger)
    assert client.post("/api/pedidos/calcular", json=pz(m["portuguesa"]), headers=atd).status_code == 200
