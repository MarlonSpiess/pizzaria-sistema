"""Fechar vendas por ingrediente: quais sabores usam um ingrediente e quais estão fechados por falta dele.

O uso vem da ficha técnica mais recente de cada produto, incluindo preparos (item com ficha própria), até 5 níveis.
O produto fechado é calculado a partir dos ingredientes em falta (não é guardado).
"""
from api.config import LOJA_ID
from api.database import agora

_USO = """
WITH RECURSIVE ult_prod AS (
    SELECT DISTINCT ON (produto_id) id, produto_id FROM ficha_versao WHERE loja_id = %(loja)s AND produto_id IS NOT NULL ORDER BY produto_id, id DESC),
ult_item AS (
    SELECT DISTINCT ON (item_id) id, item_id FROM ficha_versao WHERE loja_id = %(loja)s AND item_id IS NOT NULL ORDER BY item_id, id DESC),
usa(produto_id, item_id, nivel) AS (
    SELECT up.produto_id, fl.item_id, 1 FROM ult_prod up JOIN ficha_linha fl ON fl.versao_id = up.id
    UNION ALL
    SELECT u.produto_id, fl.item_id, u.nivel + 1 FROM usa u JOIN ult_item ui ON ui.item_id = u.item_id
        JOIN ficha_linha fl ON fl.versao_id = ui.id WHERE u.nivel < 5)
"""


def sabores_que_usam(conn, item_ids: list[int]) -> list[dict]:
    return conn.execute(_USO + "SELECT DISTINCT p.id, p.nome, p.tipo FROM usa JOIN produto p ON p.id = usa.produto_id "
                        "WHERE usa.item_id = ANY(%(itens)s) AND p.ativo AND p.loja_id = %(loja)s ORDER BY p.nome",
                        {"loja": LOJA_ID, "itens": list(item_ids)}).fetchall()


def contagem_sabores(conn, item_ids: list[int]) -> dict[int, int]:
    """item_id -> quantos sabores usam o item (uma consulta só)."""
    if not item_ids:
        return {}
    r = conn.execute(_USO + "SELECT usa.item_id, count(DISTINCT p.id) AS n FROM usa JOIN produto p ON p.id = usa.produto_id "
                     "WHERE usa.item_id = ANY(%(itens)s) AND p.ativo AND p.loja_id = %(loja)s GROUP BY usa.item_id",
                     {"loja": LOJA_ID, "itens": list(item_ids)}).fetchall()
    return {x["item_id"]: x["n"] for x in r}


def ingredientes_em_falta(conn) -> list[dict]:
    return conn.execute("SELECT f.item_id, i.nome, f.desde FROM ingrediente_em_falta f JOIN item i ON i.id = f.item_id "
                        "WHERE f.loja_id = %s AND f.reaberto_em IS NULL ORDER BY i.nome", (LOJA_ID,)).fetchall()


def produtos_fechados(conn) -> dict[int, list[str]]:
    """produto_id -> nomes dos ingredientes em falta que o fecham."""
    em_falta = ingredientes_em_falta(conn)
    if not em_falta:
        return {}
    r = conn.execute(_USO + "SELECT DISTINCT usa.produto_id, i.nome FROM usa JOIN item i ON i.id = usa.item_id "
                     "WHERE usa.item_id = ANY(%(itens)s)", {"loja": LOJA_ID, "itens": [e["item_id"] for e in em_falta]}).fetchall()
    saida: dict[int, list[str]] = {}
    for x in r:
        saida.setdefault(x["produto_id"], []).append(x["nome"])
    return saida


def marcar_falta(conn, item_id: int, em_falta: bool, usuario_id) -> bool:
    """Marca ou reabre o ingrediente. Devolve se algo mudou. Quem chama faz o commit."""
    ativo = conn.execute("SELECT id FROM ingrediente_em_falta WHERE loja_id = %s AND item_id = %s AND reaberto_em IS NULL FOR UPDATE", (LOJA_ID, item_id)).fetchone()
    if em_falta and not ativo:
        r = conn.execute("INSERT INTO ingrediente_em_falta (loja_id, item_id, desde, marcado_por) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                         (LOJA_ID, item_id, agora(), usuario_id))
        return r.rowcount > 0
    if not em_falta and ativo:
        conn.execute("UPDATE ingrediente_em_falta SET reaberto_em = %s, reaberto_por = %s WHERE id = %s", (agora(), usuario_id, ativo["id"]))
        return True
    return False


def sincronizar_pausas(conn, canal_id: int, adaptador) -> int:
    """Faz o canal refletir os produtos fechados: pausa o que deve estar pausado e reabre o resto. Repetir é seguro.
    A chamada de pausar/reabrir é do adaptador (API do Anota Ai ainda pendente). Cada produto tem seu commit."""
    fechados = produtos_fechados(conn)
    linhas = conn.execute("SELECT id, produto_id, id_externo, pausado_no_canal FROM mapa_produto_canal WHERE canal_id = %s AND id_externo IS NOT NULL AND id_externo <> '' ORDER BY id", (canal_id,)).fetchall()
    conn.commit()
    feitos = 0
    for m in linhas:
        deve = m["produto_id"] in fechados
        if deve == m["pausado_no_canal"]:
            continue
        erro = None
        try:
            (adaptador.pausar_produto if deve else adaptador.reabrir_produto)(m["id_externo"])
        except Exception as e:  # noqa: BLE001 - falha do canal: tenta no próximo ciclo
            erro = str(e)[:200]
        if erro is None:
            conn.execute("UPDATE mapa_produto_canal SET pausado_no_canal = %s, sincronizado_em = %s, erro_sincronia = NULL WHERE id = %s", (deve, agora(), m["id"]))
            feitos += 1
        else:
            conn.execute("UPDATE mapa_produto_canal SET erro_sincronia = %s WHERE id = %s", (erro, m["id"]))
        conn.commit()
    return feitos
