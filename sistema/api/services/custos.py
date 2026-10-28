"""Custos: custo do produto pela ficha técnica, CMV teórico e real, resultado do mês e ponto de equilíbrio."""
from datetime import date, datetime
from decimal import Decimal

from api.database import agora
from api.services import estoque as est

ZERO = Decimal("0")
Q2 = Decimal("0.01")


def limites_mes(mes: date):
    """Início do mês e início do mês seguinte, em data e em instante (fuso de Brasília)."""
    prox = date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)
    tz = agora().tzinfo
    return prox, datetime(mes.year, mes.month, 1, tzinfo=tz), datetime(prox.year, prox.month, 1, tzinfo=tz)


def fatores(conn, loja_id) -> dict:
    return {r["item_id"]: r["fator_correcao"] for r in conn.execute("SELECT item_id, fator_correcao FROM item_custo WHERE loja_id = %s", (loja_id,)).fetchall()}


def preco_vigente(conn, produto_id: int, tamanho: str):
    r = conn.execute("SELECT valor FROM preco_produto WHERE produto_id = %s AND tamanho = %s ORDER BY id DESC LIMIT 1", (produto_id, tamanho)).fetchone()
    return r["valor"] if r else None


def taxa_cartao_media(conn, loja_id) -> Decimal:
    """Taxa média (%) das formas de pagamento dos últimos 30 dias, pelas regras de recebimento vigentes."""
    r = conn.execute(
        "SELECT COALESCE(sum(p.valor - p.troco), 0) AS total, COALESCE(sum((p.valor - p.troco) * COALESCE(rg.taxa_pct, 0)), 0) AS taxado FROM pagamento p "
        "JOIN pedido d ON d.id = p.pedido_id LEFT JOIN LATERAL (SELECT taxa_pct FROM regra_recebimento WHERE loja_id = d.loja_id AND forma = p.forma AND maquininha_id IS NULL "
        "ORDER BY vigente_desde DESC, id DESC LIMIT 1) rg ON true WHERE d.loja_id = %s AND d.situacao <> 'cancelado' AND d.data >= current_date - 30", (loja_id,)).fetchone()
    return (r["taxado"] / r["total"]) if r["total"] > 0 else ZERO


def custo_unidade(conn, loja_id, tipo, tamanho, produto_id, sabor2_id=None, adicionais=()) -> dict:
    """Custo dos insumos de uma unidade vendida, com o fator de correção. Itens sem custo médio aparecem à parte."""
    consumo, falta = est.consumo_ficha(conn, loja_id, tipo, tamanho, produto_id, sabor2_id, list(adicionais))
    fat = fatores(conn, loja_id)
    linhas, total, sem_custo = [], ZERO, []
    for item_id, qtd in sorted(consumo.items()):
        it = conn.execute("SELECT nome, unidade FROM item WHERE id = %s", (item_id,)).fetchone()
        custo = est.custo_atual(conn, item_id)
        f = Decimal(fat.get(item_id, 1))
        valor = qtd * (custo or ZERO) * f
        if custo is None:
            sem_custo.append(it["nome"])
        total += valor
        linhas.append({"item": it["nome"], "unidade": it["unidade"], "quantidade": qtd, "custo_medio": custo, "fator": f, "valor": valor})
    return {"linhas": linhas, "total": total, "sem_ficha": bool(falta) or not consumo, "sem_custo": sem_custo}


def valor_estoque(conn, ate: datetime) -> Decimal:
    r = conn.execute("SELECT COALESCE(sum(s.saldo * COALESCE(c.custo_medio, 0)), 0) AS v FROM (SELECT item_id, sum(quantidade) AS saldo FROM movimento_estoque WHERE criado_em < %s "
                     "GROUP BY item_id HAVING sum(quantidade) > 0) s LEFT JOIN LATERAL (SELECT custo_medio FROM custo_item WHERE item_id = s.item_id AND criado_em < %s ORDER BY id DESC LIMIT 1) c ON true",
                     (ate, ate)).fetchone()
    return r["v"]


def cmv_mes(conn, loja_id, mes: date) -> dict:
    """CMV teórico (consumo das fichas pelo custo do momento) e real (estoque inicial + compras - estoque final) do mês."""
    prox, ini, fim = limites_mes(mes)
    def soma(tipos):
        return conn.execute("SELECT COALESCE(sum(-quantidade * COALESCE(custo_unit, 0)), 0) AS v FROM movimento_estoque WHERE tipo = ANY(%s) AND criado_em >= %s AND criado_em < %s",
                            (tipos, ini, fim)).fetchone()["v"]
    compras = conn.execute("SELECT COALESCE(sum(quantidade * COALESCE(custo_unit, 0)), 0) AS v FROM movimento_estoque WHERE tipo = 'entrada_compra' AND criado_em >= %s AND criado_em < %s", (ini, fim)).fetchone()["v"]
    inicial, final = valor_estoque(conn, ini), valor_estoque(conn, fim)
    vendas = conn.execute("SELECT COALESCE(sum(subtotal - desconto + acrescimo), 0) AS v FROM pedido WHERE loja_id = %s AND situacao <> 'cancelado' AND data >= %s AND data < %s", (loja_id, mes, prox)).fetchone()["v"]
    real = inicial.quantize(Q2) + compras.quantize(Q2) - final.quantize(Q2)
    teorico = soma(["saida_venda"]).quantize(Q2)
    return {"mes": mes, "estoque_inicial": inicial.quantize(Q2), "compras": compras.quantize(Q2), "estoque_final": final.quantize(Q2), "cmv_real": real, "cmv_teorico": teorico,
            "diferenca": real - teorico, "perdas": soma(["perda"]).quantize(Q2), "consumo_interno": soma(["consumo_interno"]).quantize(Q2), "vendas": vendas.quantize(Q2),
            "cmv_pct": (real / vendas * 100).quantize(Q2) if vendas > 0 else None}


def depreciacao_mes(conn, loja_id, mes: date) -> Decimal:
    """Depreciação do mês, lançada pelo Imobilizado."""
    from api.services import imobilizado
    imobilizado.gerar_depreciacao(conn, loja_id)
    return conn.execute("SELECT COALESCE(sum(valor), 0) AS v FROM depreciacao_bem WHERE loja_id = %s AND competencia = %s", (loja_id, mes)).fetchone()["v"]


def resultado_mes(conn, loja_id, mes: date) -> dict:
    prox, ini, fim = limites_mes(mes)
    ped = conn.execute("SELECT COALESCE(sum(subtotal + acrescimo), 0) AS bruta, COALESCE(sum(desconto), 0) AS descontos, COALESCE(sum(taxa_entrega), 0) AS entrega, "
                       "COUNT(*) AS pedidos FROM pedido WHERE loja_id = %s AND situacao <> 'cancelado' AND data >= %s AND data < %s", (loja_id, mes, prox)).fetchone()
    receita = ped["bruta"] - ped["descontos"] + ped["entrega"]
    cmv = cmv_mes(conn, loja_id, mes)
    fech = conn.execute("SELECT cmv_real FROM fechamento_cmv WHERE loja_id = %s AND mes = %s", (loja_id, mes)).fetchone()
    cmv_valor = fech["cmv_real"] if fech else cmv["cmv_real"]
    taxa_cartao = conn.execute(
        "SELECT COALESCE(sum((p.valor - p.troco) * COALESCE(rg.taxa_pct, 0) / 100), 0) AS v FROM pagamento p JOIN pedido d ON d.id = p.pedido_id LEFT JOIN LATERAL "
        "(SELECT taxa_pct FROM regra_recebimento WHERE loja_id = d.loja_id AND forma = p.forma AND maquininha_id IS NULL ORDER BY vigente_desde DESC, id DESC LIMIT 1) rg ON true "
        "WHERE d.loja_id = %s AND d.situacao <> 'cancelado' AND d.data >= %s AND d.data < %s AND p.forma IN ('credito','debito')", (loja_id, mes, prox)).fetchone()["v"]
    taxa_canal = conn.execute(
        "SELECT COALESCE(sum(d.total * c.taxa_pct / 100), 0) AS v FROM pedido d JOIN canal_repasse c ON c.loja_id = d.loja_id AND lower(replace(replace(c.canal, ' ', ''), 'í', 'i')) = d.canal "
        "WHERE d.loja_id = %s AND d.situacao <> 'cancelado' AND d.data >= %s AND d.data < %s AND c.ativo", (loja_id, mes, prox)).fetchone()["v"]
    entregas = conn.execute("SELECT COALESCE(sum(total_devido), 0) AS v FROM acerto_entregador WHERE loja_id = %s AND data >= %s AND data < %s", (loja_id, mes, prox)).fetchone()["v"]
    por_nat = {r["natureza"]: r["v"] for r in conn.execute(
        "SELECT COALESCE(d.natureza, CASE WHEN t.origem_tipo = 'sangria' THEN 'variavel' END) AS natureza, sum(t.valor) AS v FROM titulo t LEFT JOIN tipo_despesa d ON d.id = t.tipo_despesa_id "
        "WHERE t.loja_id = %s AND t.sentido = 'pagar' AND t.situacao <> 'cancelado' AND t.competencia = %s AND t.origem_tipo <> 'recebimento' GROUP BY 1", (loja_id, mes)).fetchall() if r["natureza"]}
    fixos_titulos = por_nat.get("fixa", ZERO) + por_nat.get("pessoal", ZERO) + por_nat.get("outra", ZERO)
    deprec = depreciacao_mes(conn, loja_id, mes)
    fixos = fixos_titulos + deprec
    variaveis = taxa_cartao + taxa_canal + entregas + por_nat.get("variavel", ZERO)
    margem = receita - cmv_valor - variaveis
    mc_pct = (margem / receita) if receita > 0 else None
    return {"mes": mes, "pedidos": ped["pedidos"], "receita_bruta": ped["bruta"] + ped["entrega"], "descontos": ped["descontos"], "receita": receita,
            "cmv": cmv_valor, "cmv_fechado": bool(fech), "taxas_cartao": taxa_cartao.quantize(Q2), "taxas_canal": taxa_canal.quantize(Q2), "entregas": entregas, "outras_variaveis": por_nat.get("variavel", ZERO),
            "custos_variaveis": variaveis.quantize(Q2), "margem_contribuicao": margem.quantize(Q2), "margem_contribuicao_pct": (mc_pct * 100).quantize(Q2) if mc_pct is not None else None,
            "custos_fixos": fixos.quantize(Q2), "fixos_detalhe": {"fixas": por_nat.get("fixa", ZERO), "pessoal": por_nat.get("pessoal", ZERO), "outras": por_nat.get("outra", ZERO), "depreciacao": deprec},
            "tributos": por_nat.get("tributo", ZERO), "financiamento": por_nat.get("financiamento", ZERO), "retiradas": por_nat.get("retirada", ZERO),
            "resultado_operacional": (margem - fixos).quantize(Q2),
            "ponto_equilibrio": (fixos / mc_pct).quantize(Q2) if mc_pct and mc_pct > 0 else None}
