import pytest

from tests.conftest import criar_usuario_direto, entrar, novo_login
from tests.test_cadastros import _adic, _cat, _pizza

CHAVES = {"limite_desconto_atendente_pct": "5", "limite_desconto_gerente_pct": "20", "limite_desconto_subgerente_pct": "10",
          "taxa_entrega_padrao": "6,00"}


@pytest.fixture(scope="module", autouse=True)
def parametros(client):
    _, h = entrar(client, "administrador")
    for k, v in CHAVES.items():
        assert client.put(f"/api/parametros/{k}", json={"valor": v}, headers=h).status_code == 200
    yield
    for k in CHAVES:
        client.put(f"/api/parametros/{k}", json={"valor": None}, headers=h)


@pytest.fixture
def cardapio(client, admin):
    _, h = admin
    c = _cat(client, h)
    g = {"trad": _pizza(client, h, c["id"], grande="35,00", broto="22,00"), "esp": _pizza(client, h, c["id"], grande="50,00", broto="32,00"),
         "borda": _adic(client, h, "borda", "8,00", "5,00"), "extra": _adic(client, h, "adicional", "6,00", "4,00")}
    g["calz"] = client.post("/api/produtos", json={"tipo": "calzone", "nome": novo_login("cz"), "preco_unico": "28,00"}, headers=h).json()
    g["beb"] = client.post("/api/produtos", json={"tipo": "bebida", "nome": novo_login("bb"), "preco_unico": "6,00"}, headers=h).json()
    return g


def _pizza_item(c, **kw):
    return {"tipo": "pizza", "produto_id": c["trad"]["id"], "tamanho": "grande", **kw}


def _pedido(client, h, itens, pagamentos, **extra):
    return client.post("/api/pedidos", json={"itens": itens, "pagamentos": pagamentos, **extra}, headers=h)


def test_pedido_basico_e_id_do_dia_sequencial(client, cardapio):
    _, h = entrar(client, "atendente")
    r1 = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}])
    r2 = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}])
    assert r1.status_code == 201 and r2.status_code == 201, r1.text + r2.text
    assert r2.json()["id_dia"] == r1.json()["id_dia"] + 1 and r1.json()["total"] == "35.00" and r1.json()["situacao"] == "recebido"


def test_meia_a_meia_borda_adicional_calzone_bebida(client, cardapio):
    _, h = entrar(client, "atendente")
    c = cardapio
    itens = [{"tipo": "pizza", "produto_id": c["trad"]["id"], "sabor2_id": c["esp"]["id"], "tamanho": "grande",
              "adicional_ids": [c["borda"]["id"], c["extra"]["id"]], "quantidade": 2},
             {"tipo": "calzone", "produto_id": c["calz"]["id"]}, {"tipo": "bebida", "produto_id": c["beb"]["id"], "quantidade": 3}]
    r = client.post("/api/pedidos/calcular", json={"itens": itens}, headers=h).json()
    assert r["itens"][0]["total"] == "113.00"  # (42,50 + 8 + 6) x 2
    assert r["total"] == "159.00"  # 113 + 28 + 18


def test_validacoes_de_item(client, cardapio):
    _, h = entrar(client, "atendente")
    c = cardapio
    def calc(it):
        return client.post("/api/pedidos/calcular", json={"itens": [it]}, headers=h).status_code
    assert calc({"tipo": "pizza", "produto_id": c["trad"]["id"]}) == 422  # sem tamanho
    assert calc({"tipo": "bebida", "produto_id": c["beb"]["id"], "tamanho": "grande"}) == 422
    assert calc({"tipo": "calzone", "produto_id": c["beb"]["id"]}) == 404  # tipo não confere
    assert calc(_pizza_item(c, quantidade=0)) == 422 and calc(_pizza_item(c, quantidade=100)) == 422
    borda2 = _adic(client, entrar(client, "administrador")[1], "borda")
    assert calc(_pizza_item(c, adicional_ids=[c["borda"]["id"], borda2["id"]])) == 400  # duas bordas
    assert client.post("/api/pedidos/calcular", json={"itens": []}, headers=h).status_code == 422


def test_pagamento_dividido_e_troco_so_em_dinheiro(client, cardapio):
    _, h = entrar(client, "atendente")
    it = [_pizza_item(cardapio)]  # 35,00
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "30,00"}]).status_code == 400  # falta
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "40,00"}]).status_code == 400  # pix não dá troco
    ok = _pedido(client, h, it, [{"forma": "pix", "valor": "15,00"}, {"forma": "dinheiro", "valor": "50,00"}])
    assert ok.status_code == 201 and ok.json()["troco"] == "30.00"
    assert _pedido(client, h, it, [{"forma": "dinheiro", "valor": "10,00"}, {"forma": "pix", "valor": "35,00"}]).status_code == 400  # troco maior que o dinheiro
    det = client.get(f"/api/pedidos/{ok.json()['id']}", headers=h).json()
    assert [p["troco"] for p in det["pagamentos"]] == ["0.00", "30.00"]


def test_forma_nao_aceita_na_loja(client, cardapio):
    _, adm = entrar(client, "administrador")
    _, h = entrar(client, "atendente")
    client.put("/api/parametros/formas_pagamento_aceitas", json={"valor": ["dinheiro", "pix"]}, headers=adm)
    try:
        assert _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "credito", "valor": "35,00"}]).status_code == 400
    finally:
        client.put("/api/parametros/formas_pagamento_aceitas", json={"valor": None}, headers=adm)


def test_entrega_exige_cliente_com_endereco_e_aplica_taxa(client, cardapio, admin):
    _, h = entrar(client, "atendente")
    it = [_pizza_item(cardapio)]
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "41,00"}], tipo="entrega").status_code == 400
    sem_end = client.post("/api/clientes", json={"nome": "Sem Endereco", "telefone": "5550" + novo_login("")[-4:].rjust(4, "0")}, headers=h).json()
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "41,00"}], tipo="entrega", cliente_id=sem_end["id"]).status_code == 400
    cli = client.post("/api/clientes", json={"nome": "Com Endereco", "telefone": "5551" + novo_login("")[-4:].rjust(4, "0"),
                                              "endereco": "Rua A, 1"}, headers=h).json()
    ok = _pedido(client, h, it, [{"forma": "pix", "valor": "41,00"}], tipo="entrega", cliente_id=cli["id"])
    assert ok.status_code == 201 and ok.json()["taxa_entrega"] == "6.00" and ok.json()["total"] == "41.00"
    # taxa diferente do padrão exige motivo
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "40,00"}], tipo="entrega", cliente_id=cli["id"], taxa_entrega="5,00").status_code == 400
    # taxa menor que a padrão é desconto: atendente precisa de gerente; gerente pode, inclusive entrega grátis (0,00)
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "40,00"}], tipo="entrega", cliente_id=cli["id"], taxa_entrega="5,00",
                   taxa_motivo="Vizinho").status_code == 403
    gl, gs = criar_usuario_direto("gerente")
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "40,00"}], tipo="entrega", cliente_id=cli["id"], taxa_entrega="5,00",
                   taxa_motivo="Vizinho", autorizacao={"usuario": gl, "senha": gs}).status_code == 201
    _, hg = entrar(client, "gerente")
    gratis = _pedido(client, hg, it, [{"forma": "pix", "valor": "35,00"}], tipo="entrega", cliente_id=cli["id"], taxa_entrega="0,00",
                     taxa_motivo="Cortesia")
    assert gratis.status_code == 201 and gratis.json()["total"] == "35.00"
    # taxa maior que a padrão não precisa de autorização, só de motivo
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "45,00"}], tipo="entrega", cliente_id=cli["id"], taxa_entrega="10,00",
                   taxa_motivo="Longe").status_code == 201
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "40,00"}], tipo="retirada", taxa_entrega="5,00").status_code == 400


def test_desconto_dentro_do_limite_exige_motivo(client, cardapio):
    _, h = entrar(client, "atendente")
    it = [_pizza_item(cardapio)]  # 35,00; limite 5% = 1,75
    ok = _pedido(client, h, it, [{"forma": "pix", "valor": "33,25"}], ajuste={"tipo": "desconto", "valor": "1,75", "motivo": "Cliente antigo"})
    assert ok.status_code == 201 and ok.json()["desconto"] == "1.75" and ok.json()["total"] == "33.25"
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "33,25"}], ajuste={"tipo": "desconto", "valor": "1,75", "motivo": "  "}).status_code == 422
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "1,00"}], ajuste={"tipo": "desconto", "valor": "40,00", "motivo": "x"}).status_code == 400  # maior que o subtotal


def test_desconto_acima_do_limite_exige_autorizacao_de_gerente(client, cardapio):
    _, h = entrar(client, "atendente")
    it = [_pizza_item(cardapio)]
    aj = {"tipo": "desconto", "valor": "5,00", "motivo": "Atraso"}  # 14,3%
    pag = [{"forma": "pix", "valor": "30,00"}]
    assert _pedido(client, h, it, pag, ajuste=aj).status_code == 403
    gl, gs = criar_usuario_direto("gerente")
    ok = _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": gs})
    assert ok.status_code == 201, ok.text
    # senha errada, atendente como autorizador e desconto acima do limite do próprio gerente
    assert _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": "errada-errada"}).status_code == 403
    al, as_ = criar_usuario_direto("atendente")
    assert _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": al, "senha": as_}).status_code == 403
    grande = {"tipo": "desconto", "valor": "10,00", "motivo": "Erro nosso"}  # 28,6% > 20% do gerente
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "25,00"}], ajuste=grande, autorizacao={"usuario": gl, "senha": gs}).status_code == 403
    pl, ps = criar_usuario_direto("proprietario")
    assert _pedido(client, h, it, [{"forma": "pix", "valor": "25,00"}], ajuste=grande, autorizacao={"usuario": pl, "senha": ps}).status_code == 201


def test_gerente_sem_autorizacao_ate_o_proprio_limite_e_ninguem_se_autoriza(client, cardapio):
    gl, gs = criar_usuario_direto("gerente")
    _, hg = entrar(client, "gerente")
    it = [_pizza_item(cardapio)]
    ok = _pedido(client, hg, it, [{"forma": "pix", "valor": "28,00"}], ajuste={"tipo": "desconto", "valor": "7,00", "motivo": "Cortesia"})  # 20%
    assert ok.status_code == 201
    r = _pedido(client, hg, it, [{"forma": "pix", "valor": "27,00"}], ajuste={"tipo": "desconto", "valor": "8,00", "motivo": "Cortesia"})  # 22,8%
    assert r.status_code == 403
    login, senha = criar_usuario_direto("gerente")
    # o gerente logado não autoriza o próprio desconto
    h2 = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"usuario": login, "senha": senha}).json()["token"]}
    r = _pedido(client, h2, it, [{"forma": "pix", "valor": "27,00"}], ajuste={"tipo": "desconto", "valor": "8,00", "motivo": "x"},
                autorizacao={"usuario": login, "senha": senha})
    assert r.status_code == 403


def test_acrescimo_com_motivo_sem_limite(client, cardapio):
    _, h = entrar(client, "atendente")
    r = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "40,00"}],
                ajuste={"tipo": "acrescimo", "valor": "5,00", "motivo": "Embalagem especial"})
    assert r.status_code == 201 and r.json()["acrescimo"] == "5.00" and r.json()["total"] == "40.00"


def test_tentativas_de_autorizacao_sao_limitadas(client, cardapio):
    _, h = entrar(client, "atendente")
    gl, gs = criar_usuario_direto("gerente")
    it, pag = [_pizza_item(cardapio)], [{"forma": "pix", "valor": "30,00"}]
    aj = {"tipo": "desconto", "valor": "5,00", "motivo": "Atraso"}
    codigos = [_pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": "errada-errada"}).status_code for _ in range(7)]
    assert codigos[:5] == [403] * 5 and 429 in codigos[5:]
    assert _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": gs}).status_code == 429  # bloqueado mesmo com a senha certa


def test_situacao_um_passo_por_vez_e_permissoes(client, cardapio):
    _, ha = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    pid = _pedido(client, ha, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]).json()["id"]
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha).status_code == 409  # pulou etapas
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "em producao"}, headers=ha).status_code == 403  # é da Produção ou gerência
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "em producao"}, headers=hg).status_code == 200
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "acabado"}, headers=hg).status_code == 200
    r = client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha)
    assert r.status_code == 200 and r.json()["entrega_real"] is not None
    assert [e["situacao"] for e in client.get(f"/api/pedidos/{pid}", headers=ha).json()["eventos"]] == \
        ["recebido", "em producao", "acabado", "despachado ou retirado"]
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "tchau"}, headers=ha).status_code == 422


def test_cancelamento_atendente_precisa_de_gerente_e_motivo(client, cardapio):
    _, ha = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    gl, gs = criar_usuario_direto("subgerente")
    it, pag = [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]
    a = _pedido(client, ha, it, pag).json()["id"]
    assert client.post(f"/api/pedidos/{a}/cancelar", json={"motivo": "Desistiu"}, headers=ha).status_code == 403
    assert client.post(f"/api/pedidos/{a}/cancelar", json={"motivo": " "}, headers=ha).status_code == 422
    r = client.post(f"/api/pedidos/{a}/cancelar", json={"motivo": "Desistiu", "autorizacao": {"usuario": gl, "senha": gs}}, headers=ha)
    assert r.status_code == 200 and r.json()["situacao"] == "cancelado"
    assert client.post(f"/api/pedidos/{a}/cancelar", json={"motivo": "De novo"}, headers=hg).status_code == 409
    b = _pedido(client, ha, it, pag).json()["id"]
    assert client.post(f"/api/pedidos/{b}/cancelar", json={"motivo": "Erro de digitação"}, headers=hg).status_code == 200
    c = _pedido(client, ha, it, pag).json()["id"]
    for s in ("em producao", "acabado", "despachado ou retirado"):
        client.post(f"/api/pedidos/{c}/situacao", json={"situacao": s}, headers=hg)
    assert client.post(f"/api/pedidos/{c}/cancelar", json={"motivo": "Tarde demais"}, headers=hg).status_code == 409


def test_urgente_so_antes_da_producao(client, cardapio):
    _, ha = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    pid = _pedido(client, ha, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]).json()["id"]
    assert client.post(f"/api/pedidos/{pid}/urgente", json={"urgente": True}, headers=ha).json()["urgente"] is True
    client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "em producao"}, headers=hg)
    assert client.post(f"/api/pedidos/{pid}/urgente", json={"urgente": False}, headers=ha).status_code == 409


def test_permissoes_de_vendas(client, cardapio):
    for perfil in ("massa", "pizzaiolo", "acabamento"):
        _, h = entrar(client, perfil)
        assert client.get("/api/pedidos", headers=h).status_code == 403
        assert client.post("/api/pedidos/calcular", json={"itens": [_pizza_item(cardapio)]}, headers=h).status_code == 403
    assert client.get("/api/pedidos").status_code == 401


def test_historico_e_triggers_so_insercao(client, cardapio, conn_teste):
    _, h = entrar(client, "atendente")
    pid = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]).json()["id"]
    import psycopg
    for sql in ("UPDATE item_pedido SET quantidade = 2 WHERE pedido_id = %s", "DELETE FROM pagamento WHERE pedido_id = %s",
                "UPDATE evento_pedido SET situacao = 'x' WHERE pedido_id = %s", "UPDATE pedido SET total = 1 WHERE id = %s",
                "DELETE FROM pedido WHERE id = %s"):
        with pytest.raises(psycopg.Error):
            conn_teste.execute(sql, (pid,))
    conn_teste.execute("UPDATE pedido SET numero_cf = '123' WHERE id = %s", (pid,))  # CF pode ser informado depois


def test_preco_copiado_nao_muda_com_novo_preco(client, cardapio, admin):
    _, adm = admin
    _, h = entrar(client, "atendente")
    pid = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]).json()["id"]
    client.patch(f"/api/produtos/{cardapio['trad']['id']}", json={"preco_grande": "99,00"}, headers=adm)
    assert client.get(f"/api/pedidos/{pid}", headers=h).json()["itens"][0]["preco_unit"] == "35.00"


def test_listagem_do_dia(client, cardapio):
    _, h = entrar(client, "atendente")
    _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}])
    lista = client.get("/api/pedidos", headers=h).json()
    assert lista and lista[0]["id_dia"] == 1
    assert client.get("/api/pedidos?situacao=xx", headers=h).status_code == 400
    assert client.get("/api/pedidos?data=2000-01-01", headers=h).json() == []


def test_id_do_dia_nao_repete_com_pedidos_simultaneos(client, cardapio):
    from concurrent.futures import ThreadPoolExecutor
    _, h = entrar(client, "atendente")
    def novo(_):
        return _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}])
    with ThreadPoolExecutor(6) as ex:
        rs = list(ex.map(novo, range(8)))
    assert all(r.status_code == 201 for r in rs), [r.text for r in rs if r.status_code != 201]
    ids = [r.json()["id_dia"] for r in rs]
    assert len(set(ids)) == 8


def test_limite_comparado_em_dinheiro_sem_arredondar_percentual(client, cardapio):
    _, h = entrar(client, "atendente")
    c = cardapio
    # 17 pizzas de 35,00 = 595,00; 5% = 29,75. 29,76 passa por 0,01 e deve exigir gerente; 29,75 não.
    itens = [{"tipo": "pizza", "produto_id": c["trad"]["id"], "tamanho": "grande", "quantidade": 17}]
    def pedir(valor, pago):
        return _pedido(client, h, itens, [{"forma": "pix", "valor": pago}], ajuste={"tipo": "desconto", "valor": valor, "motivo": "Teste"})
    assert pedir("29,75", "565,25").status_code == 201
    assert pedir("29,76", "565,24").status_code == 403


def test_reenvio_com_a_mesma_chave_nao_duplica(client, cardapio):
    _, h = entrar(client, "atendente")
    chave = "chave-" + novo_login("k")
    a = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "dinheiro", "valor": "40,00"}], chave=chave)
    b = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "dinheiro", "valor": "40,00"}], chave=chave)
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"] and b.json()["troco"] == "5.00"
    assert _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}], chave="curta").status_code == 422


def test_trava_de_autorizacao_nao_bloqueia_o_login_do_gerente(client, cardapio):
    _, h = entrar(client, "atendente")
    gl, gs = criar_usuario_direto("gerente")
    it, pag = [_pizza_item(cardapio)], [{"forma": "pix", "valor": "30,00"}]
    aj = {"tipo": "desconto", "valor": "5,00", "motivo": "Atraso"}
    for _ in range(6):
        _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": "errada-errada"})
    assert client.post("/api/auth/login", json={"usuario": gl, "senha": gs}).status_code == 200


def test_desconto_acima_do_limite_do_autorizador_conta_como_falha(client, cardapio):
    _, h = entrar(client, "atendente")
    gl, gs = criar_usuario_direto("gerente")
    it, pag = [_pizza_item(cardapio)], [{"forma": "pix", "valor": "25,00"}]
    aj = {"tipo": "desconto", "valor": "10,00", "motivo": "Erro nosso"}  # 28,6% > 20% do gerente
    r = _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": gs})
    r2 = _pedido(client, h, it, pag, ajuste=aj, autorizacao={"usuario": gl, "senha": "errada-errada"})
    assert r.status_code == r2.status_code == 403 and r.json()["detail"] == r2.json()["detail"]


def test_banco_impede_voltar_pedido_cancelado_ou_pular_etapa(client, cardapio, conn_teste):
    import psycopg
    _, h = entrar(client, "atendente")
    _, hg = entrar(client, "gerente")
    pid = _pedido(client, h, [_pizza_item(cardapio)], [{"forma": "pix", "valor": "35,00"}]).json()["id"]
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE pedido SET situacao = 'acabado' WHERE id = %s", (pid,))
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE pedido SET observacoes = 'x' WHERE id = %s", (pid,))
    client.post(f"/api/pedidos/{pid}/cancelar", json={"motivo": "Teste"}, headers=hg)
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE pedido SET situacao = 'recebido' WHERE id = %s", (pid,))
