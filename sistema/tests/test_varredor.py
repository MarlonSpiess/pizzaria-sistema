"""Varredura e aviso de status dos canais, com adaptador falso (a API real do Anota Ai está pendente)."""
from api.services import canais, varredor
from tests.conftest import entrar
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
