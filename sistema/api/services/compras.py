"""Compras: sugestão de necessidades, preços e conversão entre unidade de compra e unidade do item."""
import math
from datetime import timedelta
from decimal import Decimal

from api.services import estoque as est
from api.services.parametros import vigentes

ZERO = Decimal("0")


def converter_preco(conn, loja_id: int, item_id: int, preco_embalagem: Decimal) -> tuple[Decimal, Decimal]:
    """(fator, preço por unidade do item). O fator vem do cadastro de estoque do item (1 quando não há unidade de compra)."""
    fator = Decimal(est.config_item(conn, loja_id, item_id)["fator_compra"])
    return fator, (Decimal(preco_embalagem) / fator).quantize(Decimal("0.000001"))


def ultimo_preco(conn, item_id: int, fornecedor_id: int | None = None):
    sql, args = "SELECT preco_unit FROM preco_compra WHERE item_id = %s", [item_id]
    if fornecedor_id:
        sql, args = sql + " AND fornecedor_id = %s", args + [fornecedor_id]
    r = conn.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()
    return r["preco_unit"] if r else None


def ultimos_precos(conn, item_id: int, n: int = 3) -> list[dict]:
    return conn.execute("SELECT p.preco_unit, p.data, f.nome AS fornecedor FROM preco_compra p LEFT JOIN fornecedor f ON f.id = p.fornecedor_id "
                        "WHERE p.item_id = %s ORDER BY p.id DESC LIMIT %s", (item_id, n)).fetchall()


def sugestoes(conn, loja_id: int, hoje) -> list[dict]:
    """O que o sistema aponta para comprar. Gatilho: saldo no ponto de pedido (ou no mínimo, se não há ponto).
    Quantidade: até o máximo (ou o dobro do mínimo), em múltiplos da unidade de compra. Lote perto de vencer também entra."""
    dias = int(vigentes(conn, loja_id)["alerta_validade_dias"]["valor"] or 7)
    vencendo = {r["item_id"]: r["saldo"] for r in conn.execute(
        "SELECT m.item_id, sum(m.quantidade) AS saldo FROM movimento_estoque m JOIN lote_estoque l ON l.id = m.lote_id "
        "WHERE m.loja_id = %s AND l.validade IS NOT NULL AND l.validade <= %s GROUP BY m.item_id, l.id HAVING sum(m.quantidade) > 0",
        (loja_id, hoje + timedelta(days=dias))).fetchall()}
    saida = []
    for it in conn.execute("SELECT id FROM item WHERE loja_id = %s AND ativo ORDER BY nome", (loja_id,)).fetchall():
        c = est.config_item(conn, loja_id, it["id"])
        saldo = est.saldo_item(conn, it["id"])
        gatilho = c["ponto_pedido"] if c["ponto_pedido"] is not None else c["estoque_minimo"]
        origem, qtd = None, ZERO
        if gatilho is not None and saldo <= gatilho:
            alvo = c["estoque_maximo"] if c["estoque_maximo"] is not None else (c["estoque_minimo"] or gatilho) * 2
            qtd, origem = max(alvo - saldo, Decimal("0.0001")), "minimo"
        elif it["id"] in vencendo:
            qtd, origem = vencendo[it["id"]], "validade"
        if origem:
            f = Decimal(c["fator_compra"])
            qtd = Decimal(math.ceil(qtd / f)) * f
            saida.append({"item_id": it["id"], "quantidade": est.q4(qtd), "origem": origem, "saldo": saldo})
    return saida
