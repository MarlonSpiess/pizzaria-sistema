"""Imobilizado: depreciação mensal em linha reta (fiscal ou por vida útil real) e os alertas dos bens."""
from datetime import date, timedelta
from decimal import Decimal

from api.database import agora

ZERO = Decimal("0.00")
Q2 = Decimal("0.01")


def _mes(d: date) -> date:
    return d.replace(day=1)


def _prox(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def vida_meses(b: dict, taxa_fiscal) -> int:
    """Vida útil em meses: a informada, ou 12 / taxa fiscal anual (10% a.a. = 120 meses)."""
    if b["metodo"] == "vida_util":
        return max(1, min(int(b["vida_util_meses"]), 1200))
    return max(1, min(int((Decimal(12) * 100 / Decimal(taxa_fiscal)).to_integral_value()), 1200))


def parcelas(b: dict, taxa_fiscal, ate: date | None = None) -> list[tuple[date, Decimal]]:
    """Todas as parcelas de depreciação do bem, mês a mês, a partir do mês de início de uso. A última absorve os centavos."""
    if not b["inicio_uso"]:
        return []
    n = vida_meses(b, taxa_fiscal)
    base = Decimal(b["valor_aquisicao"]) - Decimal(b["valor_residual"])
    mensal = (base / n).quantize(Q2)
    mes, saida, acumulado = _mes(b["inicio_uso"]), [], ZERO
    for i in range(n):
        if ate and mes > ate:
            break
        v = mensal if i < n - 1 else base - acumulado
        if v > 0:
            saida.append((mes, v))
        acumulado += v
        mes = _prox(mes)
    return saida


def gerar_depreciacao(conn, loja_id: int) -> int:
    """Lança as parcelas vencidas até o mês corrente que ainda não existem. Bem baixado para de depreciar no mês da baixa. Pode rodar sempre."""
    conn.execute("SELECT pg_advisory_xact_lock(%s, 7003)", (loja_id,))
    hoje, quando, n = agora().date(), agora(), 0
    limite = _mes(hoje)
    for b in conn.execute("SELECT b.*, c.taxa_fiscal_pct, x.data AS baixa_em FROM bem b JOIN categoria_bem c ON c.id = b.categoria_id LEFT JOIN baixa_bem x ON x.bem_id = b.id "
                          "WHERE b.loja_id = %s AND b.inicio_uso IS NOT NULL", (loja_id,)).fetchall():
        fim = min(limite, _mes(b["baixa_em"]) if b["baixa_em"] else limite)  # no mês da baixa o bem ainda é depreciado
        for mes, v in parcelas(b, b["taxa_fiscal_pct"], fim):
            if mes > fim:
                break
            if conn.execute("INSERT INTO depreciacao_bem (loja_id, bem_id, competencia, valor, criado_em) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING 1",
                            (loja_id, b["id"], mes, v, quando)).fetchone():
                n += 1
    return n


def proximo_vencimento(p: dict) -> date:
    return (p["ultima_em"] or p["base_em"]) + timedelta(days=p["periodicidade_dias"])


def saldo_contabil(conn, b: dict) -> Decimal:
    dep = conn.execute("SELECT COALESCE(sum(valor), 0) AS s FROM depreciacao_bem WHERE bem_id = %s", (b["id"],)).fetchone()["s"]
    return Decimal(b["valor_aquisicao"]) - Decimal(dep)
