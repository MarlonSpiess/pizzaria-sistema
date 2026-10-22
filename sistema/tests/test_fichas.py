import os

import psycopg
import pytest

from tests.conftest import entrar, novo_login
from tests.test_cadastros import _adic, _cat, _pizza


def _item(client, h, classe="insumo", unidade="g", nome=None):
    r = client.post("/api/itens", json={"nome": nome or novo_login("it"), "classe": classe, "unidade": unidade}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _ficha(client, h, caminho, linhas):
    return client.put(f"/api/fichas/{caminho}", json={"linhas": linhas}, headers=h)


def test_item_cadastro_e_dominio(client, admin):
    _, h = admin
    nome = novo_login("farinha")
    assert client.post("/api/itens", json={"nome": nome, "classe": "insumo", "unidade": "kg"}, headers=h).status_code == 201
    assert client.post("/api/itens", json={"nome": nome.upper(), "classe": "insumo", "unidade": "kg"}, headers=h).status_code == 409
    for ruim in ({"classe": "xx", "unidade": "g"}, {"classe": "insumo", "unidade": "ton"}):
        assert client.post("/api/itens", json={"nome": novo_login("z"), **ruim}, headers=h).status_code == 422
    i = _item(client, h)
    assert client.patch(f"/api/itens/{i['id']}", json={"ativo": False}, headers=h).json()["ativo"] is False
    assert client.patch(f"/api/itens/{i['id']}", json={"ativo": None}, headers=h).status_code == 422


def test_ficha_do_produto_versoes_perda_padrao_e_validacao(client, admin):
    _, h = admin
    p = _pizza(client, h, _cat(client, h)["id"])
    queijo, molho = _item(client, h), _item(client, h, unidade="ml")
    assert client.get(f"/api/fichas/produto/{p['id']}", headers=h).json()["linhas"] == []
    r = _ficha(client, h, f"produto/{p['id']}", [{"item_id": queijo["id"], "quantidade": "75,5"}, {"item_id": molho["id"], "quantidade": "30", "perda_pct": "5"}])
    assert r.status_code == 200, r.text
    por_item = {x["item_id"]: x for x in r.json()["linhas"]}
    assert por_item[queijo["id"]]["perda_pct"] == "10.00" and por_item[queijo["id"]]["quantidade"] == "75.5"  # perda padrão 10%
    assert por_item[molho["id"]]["perda_pct"] == "5.00"
    v1 = r.json()["versao_id"]
    r2 = _ficha(client, h, f"produto/{p['id']}", [{"item_id": queijo["id"], "quantidade": "80"}])
    assert r2.json()["versao_id"] > v1 and len(r2.json()["linhas"]) == 1  # vale a versão mais recente
    for ruim in ([{"item_id": queijo["id"], "quantidade": "0"}], [{"item_id": queijo["id"], "quantidade": "-1"}],
                 [{"item_id": queijo["id"], "quantidade": "1", "perda_pct": "101"}],
                 [{"item_id": queijo["id"], "quantidade": "1"}, {"item_id": queijo["id"], "quantidade": "2"}],
                 [{"item_id": 99999999, "quantidade": "1"}]):
        assert _ficha(client, h, f"produto/{p['id']}", ruim).status_code in (400, 422)
    client.patch(f"/api/itens/{molho['id']}", json={"ativo": False}, headers=h)
    assert _ficha(client, h, f"produto/{p['id']}", [{"item_id": molho["id"], "quantidade": "1"}]).status_code == 400
    assert _ficha(client, h, "produto/99999999", []).status_code == 404


def test_ficha_adicional_base_e_preparo_com_ciclo(client, admin):
    _, h = admin
    bor = _adic(client, h)
    queijo = _item(client, h)
    assert _ficha(client, h, f"adicional/{bor['id']}/grande", [{"item_id": queijo["id"], "quantidade": "40"}]).status_code == 200
    assert client.get(f"/api/fichas/adicional/{bor['id']}/broto", headers=h).json()["linhas"] == []  # tamanhos separados
    assert _ficha(client, h, f"adicional/{bor['id']}/medio", []).status_code == 400
    massa = _item(client, h, classe="preparo", unidade="un")
    caixa = _item(client, h, classe="embalagem", unidade="un")
    assert _ficha(client, h, "base/grande", [{"item_id": massa["id"], "quantidade": "1"}, {"item_id": caixa["id"], "quantidade": "1"}]).status_code == 200
    assert _ficha(client, h, "base/broto", [{"item_id": caixa["id"], "quantidade": "1"}]).status_code == 200
    farinha = _item(client, h, unidade="kg")
    assert _ficha(client, h, f"preparo/{massa['id']}", [{"item_id": farinha["id"], "quantidade": "0,25"}]).status_code == 200
    assert _ficha(client, h, f"preparo/{queijo['id']}", []).status_code == 400  # só preparo tem ficha própria
    outro = _item(client, h, classe="preparo", unidade="un")
    assert _ficha(client, h, f"preparo/{massa['id']}", [{"item_id": massa["id"], "quantidade": "1"}]).status_code == 400
    assert _ficha(client, h, f"preparo/{outro['id']}", [{"item_id": massa["id"], "quantidade": "1"}]).status_code == 200
    assert _ficha(client, h, f"preparo/{massa['id']}", [{"item_id": outro["id"], "quantidade": "1"}]).status_code == 400  # ciclo indireto


def test_versoes_de_ficha_sao_so_insercao(client, admin):
    _, h = admin
    p = _pizza(client, h, _cat(client, h)["id"])
    _ficha(client, h, f"produto/{p['id']}", [{"item_id": _item(client, h)["id"], "quantidade": "1"}])
    with psycopg.connect(dbname=os.environ["DB_NAME"], host=os.environ["DB_HOST"], port=os.environ["DB_PORT"],
                         user=os.environ["DB_USER"], password=os.environ["DB_PASS"]) as c:
        for sql in ("UPDATE ficha_linha SET quantidade = 1", "DELETE FROM ficha_linha", "UPDATE ficha_versao SET criado_por = NULL", "DELETE FROM ficha_versao"):
            with pytest.raises(psycopg.Error):
                c.execute(sql)
            c.rollback()


def test_etapas_modelo_excecao_e_volta_ao_modelo(client, admin):
    _, h = admin
    r = client.post("/api/etapas/iniciar-padrao", headers=h)
    assert r.status_code in (201, 409)
    etapas = client.get("/api/etapas", headers=h).json()
    assert len(etapas) >= 5
    nomes = {e["nome"]: e["id"] for e in etapas}
    assert {"Forno", "Montagem", "Acabamento"} <= set(nomes)
    p = _pizza(client, h, _cat(client, h)["id"])
    ef = client.get(f"/api/produtos/{p['id']}/etapas", headers=h).json()
    assert ef["personalizado"] is False and len(ef["etapas"]) >= 5  # herda o modelo do tipo
    extra = client.post("/api/etapas", json={"nome": novo_login("Batata palha"), "funcao": "acabamento"}, headers=h).json()
    seq = [{"etapa_id": nomes["Montagem"], "tempo_min": "1,5"}, {"etapa_id": nomes["Forno"]}, {"etapa_id": extra["id"], "tempo_min": "0.5"}, {"etapa_id": nomes["Acabamento"]}]
    r = client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": seq}, headers=h)
    assert r.status_code == 200 and r.json()["personalizado"] is True
    assert [e["etapa_id"] for e in r.json()["etapas"]] == [s["etapa_id"] for s in seq]  # a ordem é a da lista
    assert r.json()["etapas"][0]["tempo_min"] == "1.50" and r.json()["etapas"][1]["tempo_min"] is None
    assert client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": [seq[0], seq[0]]}, headers=h).status_code == 422
    assert client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": [{"etapa_id": 99999999}]}, headers=h).status_code == 400
    assert client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": []}, headers=h).status_code == 400
    assert client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": [{"etapa_id": nomes["Forno"], "tempo_min": "-1"}]}, headers=h).status_code == 422
    assert client.delete(f"/api/produtos/{p['id']}/etapas", headers=h).json()["personalizado"] is False
    client.patch(f"/api/etapas/{extra['id']}", json={"ativo": False}, headers=h)
    assert client.put(f"/api/produtos/{p['id']}/etapas", json={"etapas": [{"etapa_id": extra["id"]}]}, headers=h).status_code == 400
    m = client.get("/api/modelo-etapas/calzone", headers=h).json()["etapas"]
    assert [e["ordem"] for e in m] == list(range(1, len(m) + 1))
    assert client.get("/api/modelo-etapas/xx", headers=h).status_code == 404
    assert client.put("/api/modelo-etapas/bebida", json={"etapas": []}, headers=h).status_code == 200


def test_qualidade_e_permissoes_das_fichas(client, admin):
    _, h = admin
    p = _pizza(client, h, _cat(client, h)["id"])
    q = client.get("/api/fichas/qualidade", headers=h).json()
    assert any(x["id"] == p["id"] for x in q["produtos_sem_ficha"])
    _ficha(client, h, f"produto/{p['id']}", [{"item_id": _item(client, h)["id"], "quantidade": "1"}])
    q = client.get("/api/fichas/qualidade", headers=h).json()
    assert not any(x["id"] == p["id"] for x in q["produtos_sem_ficha"])
    for perfil in ("atendente", "massa", "pizzaiolo", "acabamento"):
        _, hp = entrar(client, perfil)
        assert client.get("/api/itens", headers=hp).status_code == 403
        assert client.get(f"/api/fichas/produto/{p['id']}", headers=hp).status_code == 403
        assert client.put(f"/api/fichas/produto/{p['id']}", json={"linhas": []}, headers=hp).status_code == 403
        assert client.get("/api/etapas", headers=hp).status_code == 403
    _, hg = entrar(client, "gerente")
    assert client.get("/api/itens", headers=hg).status_code == 200
    _, hs = entrar(client, "subgerente")
    assert client.post("/api/itens", json={"nome": novo_login("s"), "classe": "consumo", "unidade": "un"}, headers=hs).status_code == 201
