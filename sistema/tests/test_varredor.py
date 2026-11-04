"""Varredura e aviso de status dos canais, com adaptador falso (a API real do Anota Ai está pendente)."""
from datetime import timedelta

import pytest

from api.services import canais, varredor
from tests.conftest import entrar, novo_login
from tests.test_producao import _g, _pagar, hs, parametros, fila_limpa  # noqa: F401  (fixtures)
from tests.test_vendas import cardapio  # noqa: F401  (fixture)


class Falso:
    codigo = "anotaai"

    def __init__(self):
        self.novos, self.avisos, self.falhar = [], [], False

    def configurado(self):
        return True

    def buscar_novos(self):
        if self.falhar:
            raise RuntimeError("sem internet")
        return self.novos

    def avisar(self, id_externo, evento):
        if self.falhar:
            raise RuntimeError("sem internet")
        self.avisos.append((id_externo, evento))


def _canal(client, h):
    c = next(x for x in client.get("/api/canais", headers=h).json() if x["codigo"] == "anotaai")
    return c


def test_varredura_idempotente_e_sem_canal_inativo(client, conn_teste):
    _, adm = entrar(client, "administrador")
    c = _canal(client, adm)
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": False}, headers=adm)
    f = Falso(); f.novos = [{"id_externo": "A1"}, {"id_externo": "A2"}]
    varredor.ciclo([f])  # inativo: não consulta
    assert [e for e in client.get(f"/api/canais/{c['id']}/fila", headers=adm).json() if e["id_externo"] in ("A1", "A2")] == []
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=adm)
    varredor.ciclo([f]); varredor.ciclo([f])  # repetir não duplica
    fila = [e for e in client.get(f"/api/canais/{c['id']}/fila", headers=adm).json() if e["id_externo"] in ("A1", "A2")]
    assert len(fila) == 2
    f.novos = [{"sem_id": 1}, {"id_externo": "A3"}]
    varredor.ciclo([f])  # item inválido é ignorado, o resto entra
    assert any(e["id_externo"] == "A3" for e in client.get(f"/api/canais/{c['id']}/fila", headers=adm).json())
    f.falhar = True
    varredor._proxima_varredura.clear()
    varredor.ciclo([f])  # falha do canal não derruba o ciclo e adia a próxima varredura
    assert varredor._falhas["anotaai"] >= 1 and varredor._proxima_varredura["anotaai"] > 0
    varredor._proxima_varredura.clear(); varredor._falhas.clear()
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": False}, headers=adm)  # não contamina outros testes


def test_aviso_de_status_com_reenvio(client, conn_teste, cardapio, hs):  # noqa: F811
    from api.database import pool
    _, adm = entrar(client, "administrador")
    c = _canal(client, adm)
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=adm)
    pid = _pagar(client, hs["atendente"], [_g(cardapio, 1)])["id"]
    conn_teste.execute("SET session_replication_role = replica")  # o gatilho de imutabilidade do pedido impede esta troca; só no teste
    conn_teste.execute("UPDATE pedido SET canal = 'anotaai', id_canal = %s WHERE id = %s", (f"EXT{pid}", pid))
    conn_teste.execute("SET session_replication_role = DEFAULT")
    assert canais.evento_da_situacao("retirada", "acabado") == "pronto"
    assert canais.evento_da_situacao("retirada", "despachado ou retirado") == "finalizado"
    assert canais.evento_da_situacao("entrega", "acabado") is None  # espera o entregador sair
    assert canais.evento_da_situacao("entrega", "despachado ou retirado") == "pronto"
    assert canais.evento_da_situacao("entrega", "recebido") is None
    f = Falso()
    with pool.connection() as conn:
        canais.enfileirar_aviso(conn, pid, "balcao", "retirada", "acabado")  # pedido de balcão não gera aviso
        canais.enfileirar_aviso(conn, pid, "anotaai", "retirada", "acabado")
        canais.enfileirar_aviso(conn, pid, "anotaai", "retirada", "acabado")  # repetido: ignorado
        conn.commit()
        f.falhar = True
        assert canais.enviar_avisos(conn, c["id"], f) == 0  # falha: reagenda
        a = conn.execute("SELECT tentativas, erro, proxima_tentativa > now() AS adiado FROM aviso_canal WHERE pedido_id = %s", (pid,)).fetchall()
        assert len(a) == 1 and a[0]["tentativas"] == 1 and a[0]["erro"] and a[0]["adiado"]
        f.falhar = False
        assert canais.enviar_avisos(conn, c["id"], f) == 0  # ainda não venceu a espera
        conn.execute("UPDATE aviso_canal SET proxima_tentativa = now() - interval '1 second' WHERE pedido_id = %s", (pid,))
        conn.commit()
        assert canais.enviar_avisos(conn, c["id"], f) == 1
        assert f.avisos == [(f"EXT{pid}", "pronto")]
        assert canais.enviar_avisos(conn, c["id"], f) == 0  # já enviado, não repete
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": False}, headers=adm)


def test_estados_da_importacao(client, conn_teste):
    from api.database import pool
    _, adm = entrar(client, "administrador")
    _, ger = entrar(client, "gerente")
    c = _canal(client, adm)
    conn_teste.execute("DELETE FROM entrada_canal WHERE canal_id = %s AND pedido_id IS NULL", (c["id"],))  # só esta fila
    varredor._proxima_varredura.clear(); varredor._falhas.clear()
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": True}, headers=adm)
    f = Falso(); f.novos = [{"id_externo": "I1"}, {"id_externo": "I2"}]
    varredor.ciclo([f])
    with pool.connection() as conn:
        a = canais.iniciar_importacao(conn, c["id"])
        assert a["id_externo"] == "I1" and canais.ha_importando(conn, c["id"])
        f.novos = [{"id_externo": "I3"}]
        varredor.ciclo([f])  # importando: a varredura espera, I3 não entra
        assert conn.execute("SELECT count(*) AS n FROM entrada_canal WHERE canal_id = %s AND id_externo = 'I3'", (c["id"],)).fetchone()["n"] == 0
        canais.bloquear_importacao(conn, a["id"], "Sabor fora do cardápio"); conn.commit()
        assert not canais.ha_importando(conn, c["id"])
        b = canais.iniciar_importacao(conn, c["id"])
        assert b["id_externo"] == "I2"  # a bloqueada não volta sozinha
        conn.execute("UPDATE entrada_canal SET importando_desde = now() - interval '10 minutes' WHERE id = %s", (b["id"],)); conn.commit()
        assert canais.liberar_importacoes_paradas(conn, c["id"]) == 1  # processo caiu no meio: volta para a fila
    with pool.connection() as conn:  # terceira queda seguida: vira bloqueada em vez de travar a fila
        for _ in range(2):
            b = canais.iniciar_importacao(conn, c["id"])
            assert b["id_externo"] == "I2"
            conn.execute("UPDATE entrada_canal SET importando_desde = now() - interval '10 minutes' WHERE id = %s", (b["id"],)); conn.commit()
            canais.liberar_importacoes_paradas(conn, c["id"])
        assert conn.execute("SELECT situacao FROM entrada_canal WHERE id = %s", (b["id"],)).fetchone()["situacao"] == "bloqueada"
        conn.execute("UPDATE entrada_canal SET situacao = 'pendente', importacao_tentativas = 0 WHERE id = %s", (b["id"],)); conn.commit()
        with pytest.raises(RuntimeError):  # concluir/bloquear fora de 'importando' não passa em silêncio
            canais.concluir_importacao(conn, b["id"], 1)
        conn.rollback()
    fila = {e["id_externo"]: e for e in client.get(f"/api/canais/{c['id']}/fila", headers=adm).json()}
    assert fila["I1"]["situacao"] == "bloqueada" and fila["I1"]["motivo"] and fila["I2"]["situacao"] == "pendente"
    assert client.post(f"/api/canais/fila/{fila['I2']['id']}/reprocessar", headers=ger).status_code == 409  # só bloqueada
    assert client.post(f"/api/canais/fila/{fila['I1']['id']}/reprocessar", headers=ger).status_code == 200
    assert client.post(f"/api/canais/fila/{fila['I1']['id']}/recusar", json={"motivo": "Não fazemos"}, headers=ger).status_code == 200
    client.patch(f"/api/canais/{c['id']}/ativo", json={"ativo": False}, headers=adm)


def test_flag_aceitar_sozinho_e_criterios(client, conn_teste, cardapio, monkeypatch):  # noqa: F811
    from api.database import hoje, pool
    _, adm = entrar(client, "administrador")
    _, ger = entrar(client, "gerente")
    c = _canal(client, adm)
    assert client.patch(f"/api/canais/{c['id']}/aceitar-sozinho", json={"ativo": False}, headers=adm).status_code == 200
    assert _canal(client, adm)["aceitar_sozinho"] is False  # padrão: aceite explícito
    assert client.patch(f"/api/canais/{c['id']}/aceitar-sozinho", json={"ativo": True}, headers=ger).status_code == 403  # só administrador/proprietário
    assert client.patch("/api/canais/99999999/aceitar-sozinho", json={"ativo": True}, headers=adm).status_code == 404
    pid = cardapio["trad"]["id"]
    conn_teste.execute("DELETE FROM mapa_produto_canal WHERE id_externo IN ('MAPA-OK', 'MAPA-OK2')")
    assert client.put(f"/api/canais/{c['id']}/produtos", json={"produto_id": pid, "id_externo": "MAPA-OK"}, headers=adm).status_code == 200
    try:
        with pool.connection() as conn:
            canal = {"id": c["id"], "ativo": True, "aceitar_sozinho": False}
            assert canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK"]) == (False, "Aceite automático desligado.")
        assert client.patch(f"/api/canais/{c['id']}/aceitar-sozinho", json={"ativo": True}, headers=adm).json()["aceitar_sozinho"] is True
        aud = client.get("/api/auditoria?entidade=canal_venda&limite=20", headers=adm).json()["data"]
        assert any(a["acao"] == "aceitar_sozinho" and a["depois"]["aceitar_sozinho"] is True for a in aud)
        with pool.connection() as conn:
            canal = {"id": c["id"], "ativo": True, "aceitar_sozinho": True}
            aberto = {"situacao": "aberto", "data": hoje()}
            assert client.patch("/api/canais/loja", json={"ativo": False}, headers=ger).status_code == 200
            monkeypatch.setattr(canais, "ultimo_caixa", lambda conn, loja: aberto)
            assert canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK"]) == (False, "A loja não está marcada como aberta.")
            assert client.patch("/api/canais/loja", json={"ativo": True}, headers=ger).json()["loja_aberta"] is True  # gerência liga
            monkeypatch.setattr(canais, "ultimo_caixa", lambda conn, loja: aberto)  # o estado real do caixa depende de outros testes
            assert canais.pode_aceitar_sozinho(conn, canal, []) == (False, "Pedido sem itens identificados.")
            assert canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK", "MAPA-OK"]) == (True, None)  # repetido não atrapalha
            ok, motivo = canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK", "NAO-MAPEADO"])
            assert not ok and "NAO-MAPEADO" in motivo
            assert canais.pode_aceitar_sozinho(conn, {**canal, "ativo": False}, ["MAPA-OK"]) == (False, "Canal desativado.")
            monkeypatch.setattr(canais, "ultimo_caixa", lambda conn, loja: {"situacao": "aberto", "data": hoje() - timedelta(days=1)})
            assert canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK"]) == (False, "O caixa de hoje não está aberto.")  # esquecido de ontem
            for caixa in (None, {"situacao": "contado", "data": hoje()}, {"situacao": "fechado", "data": hoje()}):
                monkeypatch.setattr(canais, "ultimo_caixa", lambda conn, loja, caixa=caixa: caixa)
                assert not canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK"])[0]
            monkeypatch.setattr(canais, "ultimo_caixa", lambda conn, loja: aberto)
            conn_teste.execute("UPDATE produto SET ativo = false WHERE id = %s", (pid,))  # produto inativo não conta como mapeado
            ok, motivo = canais.pode_aceitar_sozinho(conn, canal, ["MAPA-OK"])
            assert not ok and "MAPA-OK" in motivo
    finally:
        conn_teste.execute("UPDATE produto SET ativo = true WHERE id = %s", (pid,))
        client.patch(f"/api/canais/{c['id']}/aceitar-sozinho", json={"ativo": False}, headers=adm)
        client.patch("/api/canais/loja", json={"ativo": False}, headers=ger)


def test_loja_aberta_so_gerencia(client):
    _, ger = entrar(client, "gerente")
    _, atd = entrar(client, "atendente")
    assert client.get("/api/canais/loja", headers=atd).status_code == 403
    assert client.patch("/api/canais/loja", json={"ativo": True}, headers=atd).status_code == 403
    r = client.patch("/api/canais/loja", json={"ativo": True}, headers=ger).json()
    assert r["loja_aberta"] is True and r["desde"]
    assert client.get("/api/canais/loja", headers=ger).json()["loja_aberta"] is True
    client.patch("/api/canais/loja", json={"ativo": False}, headers=ger)
    assert client.get("/api/canais/loja", headers=ger).json()["loja_aberta"] is False


def test_finalizado_espera_o_pronto_e_nasce_com_ele(client, conn_teste, cardapio, hs):  # noqa: F811
    from api.database import pool
    _, adm = entrar(client, "administrador")
    c = _canal(client, adm)
    cli = client.post("/api/clientes", json={"nome": "Entrega Canal", "telefone": "5558" + novo_login("")[-4:].rjust(4, "0"), "endereco": "Rua C, 9"}, headers=hs["atendente"]).json()
    pid = _pagar(client, hs["atendente"], [_g(cardapio, 1)], tipo="entrega", cliente_id=cli["id"])["id"]
    conn_teste.execute("SET session_replication_role = replica")  # o gatilho de imutabilidade do pedido impede esta troca; só no teste
    conn_teste.execute("UPDATE pedido SET canal = 'anotaai', id_canal = %s WHERE id = %s", (f"EXT{pid}", pid))
    conn_teste.execute("SET session_replication_role = DEFAULT")
    with pool.connection() as conn:
        canais.finalizar_entregas_acertadas(conn, [pid])  # sem o "pronto" do despacho: os dois nascem juntos
        conn.commit()
        ev = sorted(r["evento"] for r in conn.execute("SELECT evento FROM aviso_canal WHERE pedido_id = %s", (pid,)).fetchall())
        assert ev == ["finalizado", "pronto"]
        f = Falso()
        assert canais.enviar_avisos(conn, c["id"], f) >= 1
        mine = [a for a in f.avisos if a[0] == f"EXT{pid}"]
        assert mine == [(f"EXT{pid}", "pronto")]  # finalizado só no ciclo seguinte, depois do pronto enviado
        assert canais.enviar_avisos(conn, c["id"], f) >= 1
        assert [a for a in f.avisos if a[0] == f"EXT{pid}"] == [(f"EXT{pid}", "pronto"), (f"EXT{pid}", "finalizado")]


def test_entrega_de_canal_so_sai_com_entregador(client, conn_teste, cardapio, hs):  # noqa: F811
    cli = client.post("/api/clientes", json={"nome": "Saida Canal", "telefone": "5557" + novo_login("")[-4:].rjust(4, "0"), "endereco": "Rua D, 1"}, headers=hs["atendente"]).json()
    ha, hg = hs["atendente"], hs["gerente"]
    pid = _pagar(client, ha, [_g(cardapio, 1)], tipo="entrega", cliente_id=cli["id"])["id"]
    conn_teste.execute("SET session_replication_role = replica")
    conn_teste.execute("UPDATE pedido SET canal = 'anotaai', id_canal = %s, situacao = 'acabado' WHERE id = %s", (f"SAI{pid}", pid))
    conn_teste.execute("SET session_replication_role = DEFAULT")
    r = client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha)
    assert r.status_code == 409 and "entregador" in r.json()["detail"]
    ent = client.post("/api/entregadores", json={"nome": novo_login("Moto"), "telefone": "5550002222"}, headers=hg).json()
    # a atribuição pela API exige caixa aberto (o estado do caixa depende de outros testes): grava a entrega direto
    conn_teste.execute("INSERT INTO entrega (pedido_id, loja_id, data, entregador_id, valor_entrega, atribuido_por, atribuido_em) "
                       "SELECT id, loja_id, data, %s, 5, criado_por, now() FROM pedido WHERE id = %s", (ent["id"], pid))
    assert client.post(f"/api/pedidos/{pid}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha).status_code == 200
    # pedido de balcão do tipo entrega não é afetado pela regra (só pedido de canal externo exige entregador)
    cli2 = client.post("/api/clientes", json={"nome": "Balcao Entrega", "telefone": "5556" + novo_login("")[-4:].rjust(4, "0"), "endereco": "Rua E, 2"}, headers=ha).json()
    pb = _pagar(client, ha, [_g(cardapio, 1)], tipo="entrega", cliente_id=cli2["id"])["id"]
    conn_teste.execute("SET session_replication_role = replica")
    conn_teste.execute("UPDATE pedido SET situacao = 'acabado' WHERE id = %s", (pb,))
    conn_teste.execute("SET session_replication_role = DEFAULT")
    assert client.post(f"/api/pedidos/{pb}/situacao", json={"situacao": "despachado ou retirado"}, headers=ha).status_code == 200
    conn_teste.execute("SET session_replication_role = replica")
    conn_teste.execute("UPDATE pedido SET situacao = 'cancelado' WHERE id = %s", (pid,))  # sai de qualquer lista de acerto
    conn_teste.execute("SET session_replication_role = DEFAULT")
