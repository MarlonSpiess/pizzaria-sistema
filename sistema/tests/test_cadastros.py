import pytest

from tests.conftest import criar_usuario_direto, entrar, novo_login


def _cat(client, h, nome=None, grande="35,00", broto="22,00"):
    nome = nome or novo_login("cat")
    r = client.post("/api/categorias", json={"nome": nome, "preco_padrao_grande": grande, "preco_padrao_broto": broto}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _pizza(client, h, cat_id, nome=None, grande="35,00", broto="22,00", **extra):
    r = client.post("/api/produtos", json={"tipo": "pizza", "nome": nome or novo_login("sabor"), "categoria_id": cat_id,
                                           "preco_grande": grande, "preco_broto": broto, **extra}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _adic(client, h, tipo="borda", g="8,00", b="5,00", nome=None):
    r = client.post("/api/adicionais", json={"tipo": tipo, "nome": nome or novo_login("add"), "preco_grande": g, "preco_broto": b}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _simular(client, h, **corpo):
    return client.post("/api/precos/pizza", json=corpo, headers=h)


def test_exemplo_de_marlon_meia_e_meia_35_e_50_da_42_50(client, admin):
    _, h = admin
    trad, esp = _cat(client, h), _cat(client, h, grande="50,00")
    a, b = _pizza(client, h, trad["id"], grande="35,00"), _pizza(client, h, esp["id"], grande="50,00", broto="32,00")
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"], sabor2_id=b["id"]).json()["total"] == "42.50"
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"]).json()["total"] == "35.00"
    assert _simular(client, h, tamanho="grande", sabor1_id=b["id"]).json()["total"] == "50.00"


def test_arredondamento_para_cima_por_sabor(client, admin):
    _, h = admin
    c = _cat(client, h)
    a, b = _pizza(client, h, c["id"], grande="35,01"), _pizza(client, h, c["id"], grande="50,01")
    r = _simular(client, h, tamanho="grande", sabor1_id=a["id"], sabor2_id=b["id"]).json()
    assert [i["valor"] for i in r["itens"]] == ["17.51", "25.01"] and r["total"] == "42.52"


def test_borda_e_adicional_somam_por_tamanho(client, admin):
    _, h = admin
    c = _cat(client, h)
    p = _pizza(client, h, c["id"])
    borda, extra = _adic(client, h, "borda", "8,00", "5,00"), _adic(client, h, "adicional", "6,00", "4,00")
    g = _simular(client, h, tamanho="grande", sabor1_id=p["id"], adicional_ids=[borda["id"], extra["id"]]).json()
    b = _simular(client, h, tamanho="broto", sabor1_id=p["id"], adicional_ids=[borda["id"], extra["id"]]).json()
    assert g["total"] == "49.00" and b["total"] == "31.00"


def test_regras_de_sabores(client, admin):
    _, h = admin
    c = _cat(client, h)
    a, b = _pizza(client, h, c["id"]), _pizza(client, h, c["id"])
    assert _simular(client, h, tamanho="broto", sabor1_id=a["id"], sabor2_id=b["id"]).status_code == 400  # Broto: 1 sabor
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"], sabor2_id=a["id"]).status_code == 400
    assert _simular(client, h, tamanho="media", sabor1_id=a["id"]).status_code == 422
    assert _simular(client, h, tamanho="grande", sabor1_id=99999999).status_code == 404
    cz = client.post("/api/produtos", json={"tipo": "calzone", "nome": novo_login("cz"), "preco_unico": "28,00"}, headers=h).json()
    assert _simular(client, h, tamanho="grande", sabor1_id=cz["id"]).status_code == 404  # só pizza
    client.patch(f"/api/produtos/{b['id']}", json={"ativo": False}, headers=h)
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"], sabor2_id=b["id"]).status_code == 400  # fora do cardápio
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"], adicional_ids=[1, 1]).status_code == 422
    assert _simular(client, h, tamanho="grande", sabor1_id=a["id"], adicional_ids=[99999999]).status_code == 404


def test_preco_novo_vira_historico_e_vale_o_mais_recente(client, admin):
    login, h = admin
    p = _pizza(client, h, _cat(client, h)["id"], grande="35,00")
    assert client.patch(f"/api/produtos/{p['id']}", json={"preco_grande": "38,50"}, headers=h).json()["preco_grande"] == "38.50"
    client.patch(f"/api/produtos/{p['id']}", json={"preco_grande": "38,50"}, headers=h)  # igual: não cria linha
    hist = client.get(f"/api/produtos/{p['id']}/historico-precos", headers=h).json()
    assert [(x["tamanho"], x["valor"]) for x in hist if x["tamanho"] == "grande"] == [("grande", "38.50"), ("grande", "35.00")]
    assert hist[0]["alterado_por"] == login


def test_validacao_de_precos_e_tipos(client, admin):
    _, h = admin
    c = _cat(client, h)
    base = {"tipo": "pizza", "nome": novo_login("v"), "categoria_id": c["id"], "preco_grande": "35", "preco_broto": "20"}
    assert client.post("/api/produtos", json=base, headers=h).status_code == 201
    for ruim in ("1e1", "-5", "abc", "1,234", "١٢", " ", "", "9999999999"):
        assert client.post("/api/produtos", json={**base, "nome": novo_login("v"), "preco_grande": ruim}, headers=h).status_code == 422, ruim
    assert client.post("/api/produtos", json={**base, "nome": novo_login("v"), "preco_unico": "5"}, headers=h).status_code == 422
    assert client.post("/api/produtos", json={**base, "nome": novo_login("v"), "categoria_id": None}, headers=h).status_code == 422
    assert client.post("/api/produtos", json={"tipo": "bebida", "nome": novo_login("v"), "preco_unico": "6", "categoria_id": c["id"]}, headers=h).status_code == 422
    assert client.post("/api/produtos", json={"tipo": "bebida", "nome": novo_login("v")}, headers=h).status_code == 422
    assert client.post("/api/produtos", json={**base, "tipo": "sushi"}, headers=h).status_code == 422
    assert client.post("/api/produtos", json={**base, "nome": novo_login("v"), "categoria_id": 99999999}, headers=h).status_code == 400
    assert client.post("/api/produtos", json={**base, "nome": novo_login("v") + "\x00"}, headers=h).status_code == 422


def test_nome_duplicado_ignora_maiusculas(client, admin):
    _, h = admin
    c = _cat(client, h)
    nome = novo_login("Dup")
    _pizza(client, h, c["id"], nome=nome)
    r = client.post("/api/produtos", json={"tipo": "pizza", "nome": nome.upper(), "categoria_id": c["id"], "preco_grande": "1", "preco_broto": "1"}, headers=h)
    assert r.status_code == 409
    assert client.post("/api/produtos", json={"tipo": "calzone", "nome": nome, "preco_unico": "28"}, headers=h).status_code == 201  # tipo diferente pode


def test_calzone_bebida_preco_unico_e_patch_nao_aplicavel(client, admin):
    _, h = admin
    bb = client.post("/api/produtos", json={"tipo": "bebida", "nome": novo_login("refri"), "preco_unico": "6,50"}, headers=h).json()
    assert bb["preco_unico"] == "6.50" and bb["preco_grande"] is None
    assert client.patch(f"/api/produtos/{bb['id']}", json={"preco_grande": "9"}, headers=h).status_code == 400
    p = _pizza(client, h, _cat(client, h)["id"])
    assert client.patch(f"/api/produtos/{p['id']}", json={"preco_unico": "9"}, headers=h).status_code == 400
    assert client.patch(f"/api/produtos/{bb['id']}", json={"preco_unico": "7"}, headers=h).json()["preco_unico"] == "7.00"


@pytest.mark.parametrize("corpo", [{"nome": None}, {"ativo": None}, {"preco_grande": None}, {"nome": ""}, {"nome": "A\x00"}, {"extra": 1}, {}])
def test_patch_produto_hostil(client, admin, corpo):
    _, h = admin
    p = _pizza(client, h, _cat(client, h)["id"])
    assert client.patch(f"/api/produtos/{p['id']}", json=corpo, headers=h).status_code in (400, 422)


def test_categoria_inativa_nao_recebe_sabor_novo_e_padrao_pode_ser_limpo(client, admin):
    _, h = admin
    c = _cat(client, h)
    assert client.patch(f"/api/categorias/{c['id']}", json={"preco_padrao_grande": None}, headers=h).json()["preco_padrao_grande"] is None
    client.patch(f"/api/categorias/{c['id']}", json={"ativo": False}, headers=h)
    r = client.post("/api/produtos", json={"tipo": "pizza", "nome": novo_login("x"), "categoria_id": c["id"], "preco_grande": "1", "preco_broto": "1"}, headers=h)
    assert r.status_code == 400
    assert client.patch(f"/api/categorias/{c['id']}", json={"nome": None}, headers=h).status_code == 422


def test_listagens_e_filtros(client, admin):
    _, h = admin
    c = _cat(client, h)
    p = _pizza(client, h, c["id"])
    client.patch(f"/api/produtos/{p['id']}", json={"ativo": False}, headers=h)
    ids_ativos = {x["id"] for x in client.get("/api/produtos?tipo=pizza&ativo=true", headers=h).json()}
    ids_todos = {x["id"] for x in client.get("/api/produtos?tipo=pizza", headers=h).json()}
    assert p["id"] not in ids_ativos and p["id"] in ids_todos
    assert client.get("/api/produtos?tipo=sushi", headers=h).status_code == 422


def test_permissoes_do_cadastro(client):
    _, ha = entrar(client, "atendente")
    assert client.get("/api/produtos", headers=ha).status_code == 200
    assert client.get("/api/adicionais", headers=ha).status_code == 200
    assert client.post("/api/produtos", json={"tipo": "bebida", "nome": novo_login("p"), "preco_unico": "5"}, headers=ha).status_code == 403
    assert client.post("/api/categorias", json={"nome": novo_login("c")}, headers=ha).status_code == 403
    assert client.get("/api/produtos/1/historico-precos", headers=ha).status_code == 403
    assert client.post("/api/entregadores", json={"nome": novo_login("e")}, headers=ha).status_code == 403
    assert client.post("/api/clientes", json={"nome": "Ana", "telefone": "11999990000"}, headers=ha).status_code in (201, 409)
    for perfil in ("massa", "pizzaiolo", "acabamento"):  # produção não vê valores
        _, hp = entrar(client, perfil)
        for caminho in ("/api/produtos", "/api/adicionais", "/api/clientes", "/api/entregadores", "/api/categorias"):
            assert client.get(caminho, headers=hp).status_code == 403
    _, hg = entrar(client, "gerente")
    assert client.post("/api/categorias", json={"nome": novo_login("c")}, headers=hg).status_code == 201


def test_clientes_telefone_unico_normalizado_e_busca(client, admin):
    _, h = admin
    tel = "11" + str(98000000 + int(novo_login("t")[1:]))
    r = client.post("/api/clientes", json={"nome": "Ana Teste", "telefone": f"({tel[:2]}) {tel[2:7]}-{tel[7:]}", "endereco": "Rua X, 1"}, headers=h)
    assert r.status_code == 201 and r.json()["telefone"] == tel
    assert client.post("/api/clientes", json={"nome": "Outra", "telefone": tel}, headers=h).status_code == 409
    assert client.get(f"/api/clientes/por-telefone/{tel}", headers=h).json()["nome"] == "Ana Teste"
    assert client.get(f"/api/clientes/por-telefone/({tel[:2]}) {tel[2:]}", headers=h).status_code == 200
    assert client.get("/api/clientes/por-telefone/0000000000", headers=h).status_code == 404
    assert any(c["telefone"] == tel for c in client.get(f"/api/clientes?q={tel[-6:]}", headers=h).json())
    assert any(c["telefone"] == tel for c in client.get("/api/clientes?q=ana%20tes", headers=h).json())
    assert client.get("/api/clientes?q=%25", headers=h).json() == []  # % não vira curinga
    for ruim in ("123", "abc", "1" * 16, ""):
        assert client.post("/api/clientes", json={"nome": "X", "telefone": ruim}, headers=h).status_code == 422


def test_cliente_alterar_e_auditoria_sem_dados_pessoais(client, admin):
    _, h = admin
    tel = "21" + str(97000000 + int(novo_login("t")[1:]))
    c = client.post("/api/clientes", json={"nome": "Beto", "telefone": tel, "endereco": "Rua Secreta, 99"}, headers=h).json()
    assert client.patch(f"/api/clientes/{c['id']}", json={"endereco": "Av. Nova, 5"}, headers=h).json()["endereco"] == "Av. Nova, 5"
    assert client.patch(f"/api/clientes/{c['id']}", json={"nome": None}, headers=h).status_code == 422
    assert client.patch(f"/api/clientes/{c['id']}", json={"ativo": False}, headers=h).json()["ativo"] is False
    aud = client.get("/api/auditoria?entidade=cliente&limite=20", headers=h).json()["data"]
    assert tel not in str(aud) and "Rua Secreta" not in str(aud) and "Av. Nova" not in str(aud)


def test_entregadores(client, admin):
    _, h = admin
    nome = novo_login("Ent")
    e = client.post("/api/entregadores", json={"nome": nome, "telefone": "(11) 91234-5678"}, headers=h)
    assert e.status_code == 201 and e.json()["telefone"] == "11912345678"
    assert client.post("/api/entregadores", json={"nome": nome.upper()}, headers=h).status_code == 409
    assert client.patch(f"/api/entregadores/{e.json()['id']}", json={"ativo": False}, headers=h).json()["ativo"] is False
    assert nome not in [x["nome"] for x in client.get("/api/entregadores?ativo=true", headers=h).json()]
    assert client.patch(f"/api/entregadores/{e.json()['id']}", json={"telefone": ""}, headers=h).json()["telefone"] is None
    assert client.patch("/api/entregadores/99999999", json={"nome": "X"}, headers=h).status_code == 404


def test_adicionais_alterar_e_validar(client, admin):
    _, h = admin
    a = _adic(client, h)
    assert client.patch(f"/api/adicionais/{a['id']}", json={"preco_grande": "9,90"}, headers=h).json()["preco_grande"] == "9.90"
    assert client.patch(f"/api/adicionais/{a['id']}", json={"preco_broto": None}, headers=h).status_code == 422
    assert client.post("/api/adicionais", json={"tipo": "molho", "nome": "x", "preco_grande": "1", "preco_broto": "1"}, headers=h).status_code == 422
    r = _simular(client, h, tamanho="grande", sabor1_id=_pizza(client, h, _cat(client, h)["id"])["id"], adicional_ids=[a["id"]])
    assert r.status_code == 200
    client.patch(f"/api/adicionais/{a['id']}", json={"ativo": False}, headers=h)
    assert _simular(client, h, tamanho="grande", sabor1_id=_pizza(client, h, _cat(client, h)["id"])["id"], adicional_ids=[a["id"]]).status_code == 400


def test_alteracoes_de_cadastro_ficam_na_auditoria(client, admin):
    login, h = admin
    p = _pizza(client, h, _cat(client, h)["id"], grande="30,00")
    client.patch(f"/api/produtos/{p['id']}", json={"preco_grande": "33,00"}, headers=h)
    aud = [a for a in client.get("/api/auditoria?entidade=produto&limite=20", headers=h).json()["data"] if a["entidade_id"] == str(p["id"])]
    assert {a["acao"] for a in aud} == {"criar", "alterar"} and all(a["usuario"] == login for a in aud)
    alterar = next(a for a in aud if a["acao"] == "alterar")
    assert alterar["antes"]["preco_grande"] == "30.00" and alterar["depois"]["preco_grande"] == "33.00"
