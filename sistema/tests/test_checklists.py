"""Checklists (melhoria M4): acesso por função, resposta só de inserção, limites, pendências, periódicos, automáticos e pontos de controle do pedido.
Cada teste cria o próprio modelo direto no banco, com código único, para não depender da ordem nem do que outros testes deixaram."""
import itertools
from datetime import timedelta

import psycopg
import pytest

from api.database import hoje
from tests.conftest import entrar
from tests.test_producao import _g, _pagar, hs, parametros  # noqa: F401  (fixtures)
from tests.test_vendas import cardapio  # noqa: F401  (fixture)

_n = itertools.count(1)


def _item(**kw):
    base = dict(setor="Setor teste", codigo="x", texto="Item", criterio=None, perfil_responsavel=None, tipo_resposta="marcar", fonte_auto=None, unidade=None,
                limite_min=None, limite_max=None, limite_min_param=None, limite_max_param=None, obrigatorio=True, recorrencia="todo_turno", origem="[Teste]")
    base.update(kw)
    return base


def _modelo(conn, itens, tipo="fim_dia"):
    """Cria um modelo vigente (versão 1) com os itens. Devolve o código."""
    codigo = f"teste_{next(_n)}"
    mid = conn.execute("INSERT INTO checklist_modelo (loja_id, codigo, nome, tipo, criado_em) VALUES (1, %s, %s, %s, now()) RETURNING id", (codigo, "Modelo " + codigo, tipo)).fetchone()[0]
    vid = conn.execute("INSERT INTO checklist_versao (modelo_id, numero, vigente, publicada_em) VALUES (%s, 1, true, now()) RETURNING id", (mid,)).fetchone()[0]
    for ordem, i in enumerate(itens):
        conn.execute(
            "INSERT INTO checklist_item (versao_id, setor, ordem, codigo, texto, criterio, perfil_responsavel, tipo_resposta, fonte_auto, unidade, limite_min, limite_max, "
            "limite_min_param, limite_max_param, obrigatorio, recorrencia, origem) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (vid, i["setor"], ordem, i["codigo"], i["texto"], i["criterio"], i["perfil_responsavel"], i["tipo_resposta"], i["fonte_auto"], i["unidade"],
             i["limite_min"], i["limite_max"], i["limite_min_param"], i["limite_max_param"], i["obrigatorio"], i["recorrencia"], i["origem"]))
    return codigo, vid


def _iniciar(client, h, codigo, **kw):
    r = client.post("/api/checklists/execucoes", json={"modelo": codigo, **kw}, headers=h)
    assert r.status_code in (200, 201), r.text  # 201 quando cria, 200 quando devolve a que já existia
    return r.json()["id"]


def _itens(client, h, eid):
    r = client.get(f"/api/checklists/execucoes/{eid}", headers=h)
    assert r.status_code == 200, r.text
    return {i["codigo"]: i for i in r.json()["itens"]}, r.json()["execucao"]


def _resp(client, h, eid, item_id, **corpo):
    return client.put(f"/api/checklists/execucoes/{eid}/itens/{item_id}", json=corpo, headers=h)


@pytest.fixture
def hs3(client, hs):  # noqa: F811
    return {**hs, "subgerente": entrar(client, "subgerente")[1], "admin": entrar(client, "administrador")[1]}


@pytest.fixture(autouse=True)
def _funcoes_ligadas(client, hs3):
    """Os testes do módulo exercitam as funções: liga o parâmetro e devolve ao padrão (piloto: só a gerência)."""
    client.put("/api/parametros/checklist_funcoes_ligado", json={"valor": "sim"}, headers=hs3["admin"])
    yield
    client.put("/api/parametros/checklist_funcoes_ligado", json={"valor": None}, headers=hs3["admin"])


def test_piloto_so_a_gerencia_ve_os_checklists(client, hs3):
    """Decisão de Marlon (23/11/2026): até o piloto em papel, só a gerência vê as abas; o servidor recusa as funções."""
    assert client.put("/api/parametros/checklist_funcoes_ligado", json={"valor": "nao"}, headers=hs3["admin"]).status_code == 200
    for p in ("atendente", "massa", "pizzaiolo", "acabamento"):
        assert client.get("/api/checklists/hoje", headers=hs3[p]).status_code == 403, p
        assert client.get("/api/auth/me", headers=hs3[p]).json()["checklists_funcoes"] is False
    assert client.get("/api/checklists/hoje", headers=hs3["gerente"]).status_code == 200
    assert client.put("/api/parametros/checklist_funcoes_ligado", json={"valor": "sim"}, headers=hs3["gerente"]).status_code == 403  # só administrador e proprietário


def test_permissoes_por_funcao(client, hs3):
    for p in ("atendente", "massa", "pizzaiolo", "acabamento", "gerente", "subgerente", "admin"):
        assert client.get("/api/checklists/hoje", headers=hs3[p]).status_code == 200, p
    for p in ("atendente", "massa", "pizzaiolo", "acabamento"):  # painel da gerência
        assert client.get("/api/checklists/pendencias", headers=hs3[p]).status_code == 403, p
        assert client.get("/api/checklists/aderencia", headers=hs3[p]).status_code == 403, p
    assert client.get("/api/checklists/pendencias", headers=hs3["gerente"]).status_code == 200
    assert client.get("/api/checklists/modelos", headers=hs3["gerente"]).status_code == 403  # editar modelos é do administrador e do proprietário
    assert client.get("/api/checklists/modelos", headers=hs3["admin"]).status_code == 200
    assert client.get("/api/checklists/hoje").status_code == 401


def test_modelos_padrao_instalam_e_repetir_nao_duplica(client, hs3):
    r = client.post("/api/checklists/modelos/padrao", headers=hs3["admin"])
    assert r.status_code == 201
    codigos = {m["codigo"] for m in client.get("/api/checklists/modelos", headers=hs3["admin"]).json()}
    assert {"inicio_dia", "acompanhamento", "fim_dia"} <= codigos
    assert client.post("/api/checklists/modelos/padrao", headers=hs3["admin"]).json() == {"instalados": []}
    assert client.post("/api/checklists/modelos/padrao", headers=hs3["gerente"]).status_code == 403


def test_fluxo_resposta_pendencia_e_conclusao(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [
        _item(codigo="a", texto="Item do pizzaiolo", perfil_responsavel="pizzaiolo"),
        _item(codigo="b", texto="Temperatura", perfil_responsavel="massa", tipo_resposta="numero", unidade="°C", limite_max="5"),
        _item(codigo="c", texto="Opcional", obrigatorio=False)])
    eid = _iniciar(client, hs3["gerente"], codigo)
    r = client.post("/api/checklists/execucoes", json={"modelo": codigo}, headers=hs3["gerente"])
    assert r.status_code == 200 and r.json() == {"id": eid, "criada": False}  # idempotente

    ip, _ = _itens(client, hs3["pizzaiolo"], eid)
    im, _ = _itens(client, hs3["massa"], eid)
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert set(ip) == {"a", "c"} and set(im) == {"b", "c"} and set(ig) == {"a", "b", "c"}  # cada função só vê o que é dela

    assert _resp(client, hs3["massa"], eid, ig["a"]["id"], resultado="conforme").status_code == 403  # item de outra função
    assert _resp(client, hs3["pizzaiolo"], eid, ip["a"]["id"], resultado="nao_conforme").status_code == 400  # falta a ação corretiva
    assert _resp(client, hs3["pizzaiolo"], eid, ip["a"]["id"], resultado="nao_conforme", acao_corretiva="Avisei o gerente").status_code == 200
    assert any("Avisei o gerente" in p["descricao"] for p in client.get("/api/checklists/pendencias", headers=hs3["gerente"]).json())

    assert _resp(client, hs3["massa"], eid, im["b"]["id"], valor_numerico="7").status_code == 400  # fora do limite sem ação
    r = _resp(client, hs3["massa"], eid, im["b"]["id"], valor_numerico="7", acao_corretiva="Ajustei o termostato")
    assert r.status_code == 200 and r.json()["resultado"] == "nao_conforme" and r.json()["fora_do_limite"] is True
    assert _resp(client, hs3["massa"], eid, im["b"]["id"], valor_numerico="4,5").status_code == 400  # sair de "não conforme" exige dizer o que foi feito
    r = _resp(client, hs3["massa"], eid, im["b"]["id"], valor_numerico="4,5", acao_corretiva="Remedi depois de ajustar")  # nova resposta substitui a anterior
    assert r.status_code == 200 and r.json()["resultado"] == "conforme"
    pend = client.get("/api/checklists/pendencias", headers=hs3["gerente"]).json()
    assert not any("Ajustei o termostato" in p["descricao"] for p in pend)  # corrigida na própria execução

    assert client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["pizzaiolo"]).status_code == 403  # concluir é da gerência
    r = client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"])
    assert r.status_code == 200 and r.json()["situacao"] == "concluida_com_pendencia"
    assert _resp(client, hs3["pizzaiolo"], eid, ip["a"]["id"], resultado="conforme").status_code == 409  # a função não corrige depois de concluir

    pid = next(p["id"] for p in client.get("/api/checklists/pendencias", headers=hs3["gerente"]).json() if "Avisei o gerente" in p["descricao"])
    assert client.post(f"/api/checklists/pendencias/{pid}/resolver", json={"resolucao": "ok"}, headers=hs3["pizzaiolo"]).status_code == 403
    assert client.post(f"/api/checklists/pendencias/{pid}/resolver", json={"resolucao": "Conversei com a equipe"}, headers=hs3["gerente"]).status_code == 200
    assert client.post(f"/api/checklists/pendencias/{pid}/resolver", json={"resolucao": "de novo"}, headers=hs3["gerente"]).status_code == 409
    assert _itens(client, hs3["gerente"], eid)[1]["situacao"] == "concluida"  # sem pendência aberta, a execução passa a concluída


def test_nao_se_aplica_exige_motivo_e_faltando_obrigatorio_nao_conclui(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="A"), _item(codigo="b", texto="B")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="nao_se_aplica").status_code == 400
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="nao_se_aplica", valor_texto="Não há entrega hoje").status_code == 200
    r = client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"])
    assert r.status_code == 409 and r.json()["detail"].startswith("Faltam 1 item(ns) obrigatório(s): b")
    assert _resp(client, hs3["gerente"], eid, ig["b"]["id"], resultado="conforme").status_code == 200
    assert client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"]).json()["situacao"] == "concluida"


def test_resposta_so_insercao_no_banco(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="A")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="conforme").status_code == 200
    with pytest.raises(psycopg.Error):
        conn_teste.execute("UPDATE checklist_resposta SET resultado = 'nao_se_aplica' WHERE execucao_id = %s", (eid,))
    with pytest.raises(psycopg.Error):
        conn_teste.execute("DELETE FROM checklist_resposta WHERE execucao_id = %s", (eid,))


def test_limite_vem_do_parametro_e_sem_limite_so_registra(client, hs3, conn_teste):
    h = hs3["admin"]
    codigo, _ = _modelo(conn_teste, [_item(codigo="t", texto="Freezer", perfil_responsavel="massa", tipo_resposta="numero", unidade="°C", limite_max_param="checklist_temp_congelado_max")])
    eid = _iniciar(client, hs3["massa"], codigo)
    it, _ = _itens(client, hs3["massa"], eid)
    assert it["t"]["limite_max"] is None
    assert _resp(client, hs3["massa"], eid, it["t"]["id"], valor_numerico="-10").json()["resultado"] == "conforme"  # sem limite definido: só registra
    assert client.put("/api/parametros/checklist_temp_congelado_max", json={"valor": "-18"}, headers=h).status_code == 200
    try:
        it, _ = _itens(client, hs3["massa"], eid)
        assert float(it["t"]["limite_max"]) == -18.0
        assert _resp(client, hs3["massa"], eid, it["t"]["id"], valor_numerico="-10").status_code == 400  # agora -10 passa de -18
        assert _resp(client, hs3["massa"], eid, it["t"]["id"], valor_numerico="-20").json()["resultado"] == "conforme"
    finally:
        client.put("/api/parametros/checklist_temp_congelado_max", json={"valor": None}, headers=h)


def test_parametro_temperatura_valida(client, hs3):
    h = hs3["admin"]
    assert client.put("/api/parametros/checklist_temp_refrigerado_max", json={"valor": "abc"}, headers=h).status_code == 400
    assert client.put("/api/parametros/checklist_temp_refrigerado_max", json={"valor": "500"}, headers=h).status_code == 400
    assert client.put("/api/parametros/checklist_temp_refrigerado_max", json={"valor": "5"}, headers=h).status_code == 200
    client.put("/api/parametros/checklist_temp_refrigerado_max", json={"valor": None}, headers=h)


def test_item_automatico_so_leitura_e_gravado_na_conclusao(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="auto", texto="Caixa aberto", tipo_resposta="automatico", fonte_auto="caixa_aberto")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert ig["auto"]["automatico"]["resultado"] in ("conforme", "nao_conforme")
    assert _resp(client, hs3["gerente"], eid, ig["auto"]["id"], resultado="conforme").status_code == 400  # ninguém marca à mão
    assert client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"]).status_code == 200
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert ig["auto"]["resposta"]["automatica"] is True


def test_item_periodico_so_aparece_quando_vence(client, hs3, conn_teste):
    codigo, vid = _modelo(conn_teste, [_item(codigo="s", texto="Semanal", recorrencia="semanal"), _item(codigo="d", texto="Do dia")])
    e1 = _iniciar(client, hs3["gerente"], codigo)
    i1, _ = _itens(client, hs3["gerente"], e1)
    assert "s" in i1  # nunca feito: vence
    for k in ("s", "d"):
        assert _resp(client, hs3["gerente"], e1, i1[k]["id"], resultado="conforme").status_code == 200
    assert client.post(f"/api/checklists/execucoes/{e1}/concluir", headers=hs3["gerente"]).status_code == 200
    def _outra(dias, turno):
        return conn_teste.execute("INSERT INTO checklist_execucao (loja_id, versao_id, data, turno, iniciada_em) VALUES (1, %s, %s, %s, now()) RETURNING id",
                                  (vid, hoje() + timedelta(days=dias), turno)).fetchone()[0]
    assert "s" not in _itens(client, hs3["gerente"], _outra(3, "t3"))[0]  # fez há pouco: não vence ainda
    assert "s" in _itens(client, hs3["gerente"], _outra(8, "t8"))[0]  # passou da semana


def test_acompanhamento_abre_rodadas(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="A", obrigatorio=False)], tipo="acompanhamento")
    r1 = _iniciar(client, hs3["gerente"], codigo)
    assert _iniciar(client, hs3["gerente"], codigo) == r1  # rodada aberta é reaproveitada
    ig, _ = _itens(client, hs3["gerente"], r1)
    assert client.post(f"/api/checklists/execucoes/{r1}/concluir", headers=hs3["gerente"]).status_code == 200
    r2 = _iniciar(client, hs3["gerente"], codigo)
    assert r2 != r1
    assert _itens(client, hs3["gerente"], r2)[1]["turno"] == "rodada 2"


def test_nova_versao_preserva_execucao_antiga(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="Antigo")], tipo="acompanhamento")  # só o acompanhamento aceita turno
    e1 = _iniciar(client, hs3["gerente"], codigo)
    novo = [_item(codigo="a", texto="Novo texto"), _item(codigo="b", texto="Item novo")]
    corpo = {"itens": [{k: v for k, v in i.items()} for i in novo]}
    r = client.post(f"/api/checklists/modelos/{codigo}/versoes", json=corpo, headers=hs3["admin"])
    assert r.status_code == 201 and r.json()["versao"] == 2, r.text
    assert client.post(f"/api/checklists/modelos/{codigo}/versoes", json=corpo, headers=hs3["gerente"]).status_code == 403
    assert set(_itens(client, hs3["gerente"], e1)[0]) == {"a"}  # a execução antiga segue na versão 1
    assert _itens(client, hs3["gerente"], e1)[0]["a"]["texto"] == "Antigo"
    e2 = _iniciar(client, hs3["gerente"], codigo, turno="tarde")
    assert set(_itens(client, hs3["gerente"], e2)[0]) == {"a", "b"}


def test_loja_aberta_avisa_ou_bloqueia_conforme_o_parametro(client, hs3, conn_teste):
    h = hs3["admin"]
    conn_teste.execute("UPDATE checklist_modelo SET ativo = false WHERE tipo = 'inicio_dia'")  # só o modelo deste teste vale
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="A")], tipo="inicio_dia")
    try:
        assert client.patch("/api/canais/loja", json={"ativo": False}, headers=hs3["gerente"]).status_code == 200
        r = client.patch("/api/canais/loja", json={"ativo": True}, headers=hs3["gerente"])  # padrão: só avisa
        assert r.status_code == 200 and r.json()["aviso_checklist"]
        client.patch("/api/canais/loja", json={"ativo": False}, headers=hs3["gerente"])
        assert client.put("/api/parametros/checklist_bloqueia_loja_aberta", json={"valor": "sim"}, headers=h).status_code == 200
        assert client.patch("/api/canais/loja", json={"ativo": True}, headers=hs3["gerente"]).status_code == 409
        r = client.patch("/api/canais/loja", json={"ativo": True, "liberar_motivo": "Abertura antecipada"}, headers=hs3["gerente"])
        assert r.status_code == 200
        client.patch("/api/canais/loja", json={"ativo": False}, headers=hs3["gerente"])
        eid = _iniciar(client, hs3["gerente"], codigo)  # com o checklist concluído a abertura passa sem aviso
        ig, _ = _itens(client, hs3["gerente"], eid)
        assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="conforme").status_code == 200
        assert client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"]).status_code == 200
        r = client.patch("/api/canais/loja", json={"ativo": True}, headers=hs3["gerente"])
        assert r.status_code == 200 and not r.json()["aviso_checklist"]
    finally:
        client.patch("/api/canais/loja", json={"ativo": False}, headers=hs3["gerente"])
        client.put("/api/parametros/checklist_bloqueia_loja_aberta", json={"valor": None}, headers=h)
        conn_teste.execute("UPDATE checklist_modelo SET ativo = false WHERE tipo = 'inicio_dia'")


def test_pontos_de_controle_do_pedido(client, hs3, cardapio):  # noqa: F811
    ped = _pagar(client, hs3["atendente"], [_g(cardapio, 1)])
    pid = ped["id"]
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "leitura_de_volta"}, headers=hs3["atendente"]).status_code == 201
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "causa_atraso", "texto": "Falta de massa"}, headers=hs3["atendente"]).status_code == 403
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "conferencia_final"}, headers=hs3["pizzaiolo"]).status_code == 403
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "conferencia_final"}, headers=hs3["acabamento"]).status_code == 201
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "causa_atraso"}, headers=hs3["gerente"]).status_code == 400  # sem texto
    assert client.post(f"/api/checklists/pedidos/{pid}/controles", json={"ponto": "causa_atraso", "texto": "Falta de massa"}, headers=hs3["gerente"]).status_code == 201
    assert client.post("/api/checklists/pedidos/999999999/controles", json={"ponto": "leitura_de_volta"}, headers=hs3["atendente"]).status_code == 404
    pontos = {c["ponto"] for c in client.get(f"/api/checklists/pedidos/{pid}/controles", headers=hs3["gerente"]).json()}
    assert pontos == {"leitura_de_volta", "conferencia_final", "causa_atraso"}


def test_bi_producao_traz_tempos_de_entrega(client, hs3):
    r = client.get("/api/bi/producao", headers=hs3["gerente"])
    assert r.status_code == 200
    assert "tempos_entrega" in r.json() and isinstance(r.json()["tempos_entrega"]["entregas"], int)


def test_aderencia_so_le(client, hs3):
    r = client.get("/api/checklists/aderencia", headers=hs3["gerente"])
    assert r.status_code == 200 and "modelos" in r.json() and "pendencias_abertas" in r.json()


def test_responder_de_novo_como_nao_conforme_nao_duplica_pendencia(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="Limpeza do forno", perfil_responsavel="acabamento")])
    eid = _iniciar(client, hs3["acabamento"], codigo)
    ia, _ = _itens(client, hs3["acabamento"], eid)
    for acao in ("Primeira ação", "Segunda ação"):
        assert _resp(client, hs3["acabamento"], eid, ia["a"]["id"], resultado="nao_conforme", acao_corretiva=acao).status_code == 200
    abertas = [p for p in client.get("/api/checklists/pendencias", headers=hs3["gerente"]).json() if "Limpeza do forno" in p["descricao"]]
    assert len(abertas) == 1 and "Segunda ação" in abertas[0]["descricao"]
    assert _itens(client, hs3["gerente"], eid)[1]["pendencias_abertas"] == 1


def test_progresso_conta_so_os_itens_da_funcao(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="p", texto="Pizzaiolo", perfil_responsavel="pizzaiolo"), _item(codigo="m1", texto="Massa 1", perfil_responsavel="massa"),
                                     _item(codigo="m2", texto="Massa 2", perfil_responsavel="massa")])
    eid = _iniciar(client, hs3["massa"], codigo)
    assert _itens(client, hs3["massa"], eid)[1]["obrigatorios"] == 2
    assert _itens(client, hs3["pizzaiolo"], eid)[1]["obrigatorios"] == 1
    assert _itens(client, hs3["gerente"], eid)[1]["obrigatorios"] == 3
    hoje_massa = next(m for m in client.get("/api/checklists/hoje", headers=hs3["massa"]).json()["modelos"] if m["codigo"] == codigo)
    assert hoje_massa["execucoes"][0]["obrigatorios"] == 2


def test_funcao_sem_item_no_modelo_nao_inicia(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="So da massa", perfil_responsavel="massa")])
    r = client.post("/api/checklists/execucoes", json={"modelo": codigo}, headers=hs3["atendente"])
    assert r.status_code == 403
    assert client.post("/api/checklists/execucoes", json={"modelo": codigo}, headers=hs3["massa"]).status_code == 201


def test_item_periodico_nao_muda_ao_reabrir_execucao_antiga(client, hs3, conn_teste):
    codigo, vid = _modelo(conn_teste, [_item(codigo="s", texto="Semanal", recorrencia="semanal")])
    e1 = _iniciar(client, hs3["gerente"], codigo)
    i1, _ = _itens(client, hs3["gerente"], e1)
    assert _resp(client, hs3["gerente"], e1, i1["s"]["id"], resultado="conforme").status_code == 200
    e2 = conn_teste.execute("INSERT INTO checklist_execucao (loja_id, versao_id, data, turno, iniciada_em) VALUES (1, %s, %s, 'futuro', now()) RETURNING id",
                            (vid, hoje() + timedelta(days=8))).fetchone()[0]
    conn_teste.execute("INSERT INTO checklist_resposta (execucao_id, item_id, resultado, respondida_em) VALUES (%s, %s, 'conforme', now())", (e2, i1["s"]["id"]))
    assert "s" in _itens(client, hs3["gerente"], e1)[0]  # a resposta de uma execução posterior não esconde o item na execução antiga
    assert _itens(client, hs3["gerente"], e1)[1]["obrigatorios"] == 1


def test_publicar_versao_recusa_parametro_inexistente_e_limite_em_item_nao_numerico(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="A")])
    ruim = {"itens": [_item(codigo="t", texto="Temp", tipo_resposta="numero", limite_max_param="checklist_temp_congelado_mx")]}
    r = client.post(f"/api/checklists/modelos/{codigo}/versoes", json=ruim, headers=hs3["admin"])
    assert r.status_code == 400 and "não existe" in r.json()["detail"]
    r = client.post(f"/api/checklists/modelos/{codigo}/versoes", json={"itens": [_item(codigo="x", texto="X", limite_max="5")]}, headers=hs3["admin"])
    assert r.status_code == 422  # limite em item que não é numérico
    ok = {"itens": [_item(codigo="t", texto="Temp", tipo_resposta="numero", limite_max_param="checklist_temp_congelado_max")]}
    assert client.post(f"/api/checklists/modelos/{codigo}/versoes", json=ok, headers=hs3["admin"]).status_code == 201


def test_aderencia_valida_periodo(client, hs3):
    h = hs3["gerente"]
    assert client.get("/api/checklists/aderencia?de=2026-05-10&ate=2026-05-01", headers=h).status_code == 400
    assert client.get("/api/checklists/aderencia?de=2025-01-01&ate=2026-05-01", headers=h).status_code == 400
    assert client.get("/api/checklists/aderencia?de=2026-05-01&ate=2026-05-10", headers=h).status_code == 200


def test_gerencia_corrige_execucao_concluida_com_motivo(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="a", texto="Item A")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="conforme").status_code == 200
    assert client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"]).json()["situacao"] == "concluida"
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="nao_conforme").status_code == 400  # falta a ação
    assert _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="conforme").status_code == 400  # corrigir depois de concluir exige motivo
    r = _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="nao_conforme", acao_corretiva="Conferi de novo e estava errado")
    assert r.status_code == 200 and r.json()["situacao"] == "concluida_com_pendencia"
    r = _resp(client, hs3["gerente"], eid, ig["a"]["id"], resultado="conforme", acao_corretiva="Refeito e conferido")
    assert r.status_code == 200 and r.json()["situacao"] == "concluida"
    # as respostas anteriores continuam gravadas e a auditoria registrou cada passo
    assert conn_teste.execute("SELECT count(*) FROM checklist_resposta WHERE execucao_id = %s", (eid,)).fetchone()[0] == 3
    assert conn_teste.execute("SELECT count(*) FROM auditoria WHERE acao = 'responder_checklist' AND depois->>'execucao' = %s", (str(eid),)).fetchone()[0] == 3
    assert conn_teste.execute("SELECT count(*) FROM auditoria WHERE acao = 'concluir_checklist' AND entidade_id = %s", (str(eid),)).fetchone()[0] == 1


def test_limites_minimo_e_valor_igual_ao_limite(client, hs3, conn_teste):
    codigo, _ = _modelo(conn_teste, [_item(codigo="t", texto="Faixa", tipo_resposta="numero", unidade="°C", limite_min="2", limite_max="5")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    it, _ = _itens(client, hs3["gerente"], eid)
    for v in ("2", "5", "3,5"):  # os extremos valem
        assert _resp(client, hs3["gerente"], eid, it["t"]["id"], valor_numerico=v).json()["resultado"] == "conforme", v
    assert _resp(client, hs3["gerente"], eid, it["t"]["id"], valor_numerico="1,99").status_code == 400  # abaixo do mínimo sem ação
    r = _resp(client, hs3["gerente"], eid, it["t"]["id"], valor_numerico="1,99", acao_corretiva="Religuei o equipamento")
    assert r.json()["resultado"] == "nao_conforme" and r.json()["fora_do_limite"] is True


def test_item_automatico_nao_conforme_vira_pendencia_na_conclusao(client, hs3, conn_teste):
    assert client.patch("/api/canais/loja", json={"ativo": False}, headers=hs3["gerente"]).status_code == 200
    codigo, _ = _modelo(conn_teste, [_item(codigo="auto", texto="Loja aberta", tipo_resposta="automatico", fonte_auto="loja_aberta")])
    eid = _iniciar(client, hs3["gerente"], codigo)
    r = client.post(f"/api/checklists/execucoes/{eid}/concluir", headers=hs3["gerente"])
    assert r.status_code == 200 and r.json()["situacao"] == "concluida_com_pendencia" and r.json()["pendencias_abertas"] == 1
    ig, _ = _itens(client, hs3["gerente"], eid)
    assert ig["auto"]["resposta"]["resultado"] == "nao_conforme" and ig["auto"]["resposta"]["automatica"] is True
    assert ig["auto"]["resposta"]["respondida_por_nome"]  # mostra quem estava com o checklist ao concluir


def test_item_periodico_corrigido_para_nao_conforme_continua_vencido(client, hs3, conn_teste):
    """Revisão cega da integração (23/11/2026): só vale a resposta vigente de cada execução."""
    codigo, vid = _modelo(conn_teste, [_item(codigo="s", texto="Semanal", recorrencia="semanal")])
    e1 = _iniciar(client, hs3["gerente"], codigo)
    i1, _ = _itens(client, hs3["gerente"], e1)
    assert _resp(client, hs3["gerente"], e1, i1["s"]["id"], resultado="conforme").status_code == 200
    r = _resp(client, hs3["gerente"], e1, i1["s"]["id"], resultado="nao_conforme", acao_corretiva="Não foi feito de verdade")
    assert r.status_code == 200, r.text
    e2 = conn_teste.execute("INSERT INTO checklist_execucao (loja_id, versao_id, data, turno, iniciada_em) VALUES (1, %s, %s, 't3', now()) RETURNING id",
                            (vid, hoje() + timedelta(days=3))).fetchone()[0]
    assert "s" in _itens(client, hs3["gerente"], e2)[0]  # a última resposta foi não conforme: o item continua cobrado


def test_item_numerico_aceita_nao_conforme_explicito(client, hs3, conn_teste):
    """Sem limite definido, quem mede ainda pode marcar não conforme (termômetro quebrado, leitura suspeita), com ação."""
    codigo, _ = _modelo(conn_teste, [_item(codigo="t", texto="Câmara", perfil_responsavel="massa", tipo_resposta="numero", unidade="°C")])
    eid = _iniciar(client, hs3["massa"], codigo)
    it, _ = _itens(client, hs3["massa"], eid)
    assert _resp(client, hs3["massa"], eid, it["t"]["id"], valor_numerico="4", resultado="nao_conforme").status_code == 400  # sem ação
    r = _resp(client, hs3["massa"], eid, it["t"]["id"], valor_numerico="4", resultado="nao_conforme", acao_corretiva="Termômetro trocado")
    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "nao_conforme"


def test_checklist_usa_a_data_do_caixa_aberto_depois_da_meia_noite(client, hs3, conn_teste):
    """Caixa de ontem ainda aberto (depois da meia-noite): o checklist do dia é o de ontem, como vendas e caixa."""
    from tests.test_qa_cego_ub2 import _forcar_fechamento, _usuario_qualquer
    ontem = hoje() - timedelta(days=1)
    if conn_teste.execute("SELECT 1 FROM caixa_dia WHERE situacao <> 'fechado'").fetchone():
        pytest.skip("há caixa em uso deixado por outro teste")
    conn_teste.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (1, %s, 0, %s, now() - interval '1 day')",
                       (ontem, _usuario_qualquer(conn_teste)))
    try:
        codigo, _ = _modelo(conn_teste, [_item(codigo="f", texto="Fechar")])
        assert client.get("/api/checklists/hoje", headers=hs3["gerente"]).json()["data"] == str(ontem)
        eid = _iniciar(client, hs3["gerente"], codigo)
        assert conn_teste.execute("SELECT data FROM checklist_execucao WHERE id = %s", (eid,)).fetchone()[0] == ontem
    finally:
        _forcar_fechamento(ontem)
        with psycopg.connect(dbname=conn_teste.info.dbname, autocommit=True, host=conn_teste.info.host, port=conn_teste.info.port,
                             user=conn_teste.info.user, password=conn_teste.info.password) as c:
            c.execute("SET session_replication_role = replica")
            c.execute("DELETE FROM caixa_dia WHERE data = %s", (ontem,))


def test_fim_do_dia_depois_de_fechar_o_caixa_da_madrugada_fica_no_dia_do_caixa(client, hs3, conn_teste):
    """Revisão não cega (23/11/2026): o caixa de ontem fechou depois da meia-noite; o fim do dia feito em seguida é o de ontem."""
    from tests.test_qa_cego_ub2 import _forcar_fechamento, _usuario_qualquer
    ontem = hoje() - timedelta(days=1)
    if conn_teste.execute("SELECT 1 FROM caixa_dia WHERE data >= %s", (ontem,)).fetchone():
        pytest.skip("há caixa de ontem ou de hoje deixado por outro teste")
    conn_teste.execute("INSERT INTO caixa_dia (loja_id, data, fundo_troco, aberto_por, aberto_em) VALUES (1, %s, 0, %s, now() - interval '1 day')",
                       (ontem, _usuario_qualquer(conn_teste)))
    try:
        _forcar_fechamento(ontem)
        codigo, _ = _modelo(conn_teste, [_item(codigo="f", texto="Fechar")], tipo="fim_dia")
        eid = _iniciar(client, hs3["gerente"], codigo, turno="outro")  # turno livre é ignorado no fim do dia
        linha = conn_teste.execute("SELECT data, turno FROM checklist_execucao WHERE id = %s", (eid,)).fetchone()
        assert linha[0] == ontem and linha[1] == "dia"
        assert _iniciar(client, hs3["gerente"], codigo) == eid  # não cria outro
    finally:
        with psycopg.connect(dbname=conn_teste.info.dbname, autocommit=True, host=conn_teste.info.host, port=conn_teste.info.port,
                             user=conn_teste.info.user, password=conn_teste.info.password) as c:
            c.execute("SET session_replication_role = replica")
            c.execute("DELETE FROM caixa_dia WHERE data = %s", (ontem,))
