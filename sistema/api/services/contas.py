"""Contas a pagar e receber: sincronização com as outras fatias (idempotente) e saldos."""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from api.database import agora

ZERO = Decimal("0.00")
Q2 = Decimal("0.01")


def _soma_meses(d: date, n: int) -> date:
    m = d.month - 1 + n
    ano, mes = d.year + m // 12, m % 12 + 1
    return date(ano, mes, min(d.day, calendar.monthrange(ano, mes)[1]))


def _novo(conn, **c):
    """Insere o título; devolve o id, ou None quando a origem já gerou um (índice único)."""
    cols = list(c)
    r = conn.execute(f"INSERT INTO titulo ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) ON CONFLICT DO NOTHING RETURNING id",
                     [c[k] for k in cols]).fetchone()
    return r["id"] if r else None


def baixar(conn, titulo_id: int, data: date, valor: Decimal, forma: str, conta_id, usuario_id, desconto=ZERO, juros=ZERO, multa=ZERO) -> dict:
    """Insere a baixa e acerta a situação do título (quem chama já travou o título)."""
    mov = valor - desconto + juros + multa
    b = conn.execute("INSERT INTO baixa_titulo (titulo_id, data, valor, desconto, juros, multa, valor_movimento, forma, conta_id, usuario_id, criado_em) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (titulo_id, data, valor, desconto, juros, multa, mov, forma, conta_id, usuario_id, agora())).fetchone()
    t = conn.execute("SELECT valor, (SELECT COALESCE(sum(valor),0) FROM baixa_titulo WHERE titulo_id = %s) AS pago FROM titulo WHERE id = %s", (titulo_id, titulo_id)).fetchone()
    conn.execute("UPDATE titulo SET situacao = %s WHERE id = %s", ("baixado" if t["pago"] >= t["valor"] else "parcial", titulo_id))
    return {"baixa_id": b["id"], "valor_movimento": mov}


def sincronizar(conn, loja_id: int) -> dict:
    """Cria os títulos que as outras fatias já originaram e ainda não estão aqui. Pode rodar quantas vezes quiser."""
    conn.execute("SELECT pg_advisory_xact_lock(%s, 7001)", (loja_id,))
    quando, hoje = agora(), agora().date()
    n = {"recebimento": 0, "sangria": 0, "acerto_entregador": 0, "fechamento": 0, "recorrencia": 0}

    # Notas recebidas: a pagar. Compra urgente paga com sangria já nasce baixada, no dinheiro da gaveta.
    for r in conn.execute("SELECT r.*, f.nome AS forn FROM recebimento r JOIN fornecedor f ON f.id = r.fornecedor_id WHERE r.loja_id = %s AND r.total_nota > 0 "
                          "AND NOT EXISTS (SELECT 1 FROM titulo t WHERE t.origem_tipo = 'recebimento' AND t.origem_id = r.id) "
                          "AND NOT EXISTS (SELECT 1 FROM titulo t WHERE t.origem_tipo = 'sangria' AND t.origem_id = r.movimento_caixa_id)", (loja_id,)).fetchall():
        venc = r["vencimento"] or r["data_nota"]
        tid = _novo(conn, loja_id=loja_id, sentido="pagar", descricao=f"Nota {r['numero_nota'] or r['id']} - {r['forn']}", fornecedor_id=r["fornecedor_id"],
                    valor=r["total_nota"], vencimento=venc, competencia=r["data_nota"].replace(day=1), origem_tipo="recebimento", origem_id=r["id"],
                    criado_em=quando, criado_por=r["criado_por"])
        if tid:
            n["recebimento"] += 1
            if r["movimento_caixa_id"]:
                baixar(conn, tid, r["data_nota"], r["total_nota"], "dinheiro", None, r["criado_por"])

    # Sangrias de pequena despesa (as que pagaram uma nota já estão no título da nota).
    for m in conn.execute("SELECT m.* FROM movimento_caixa m WHERE m.loja_id = %s AND m.tipo = 'sangria' AND m.vira_despesa "
                          "AND NOT EXISTS (SELECT 1 FROM recebimento r WHERE r.movimento_caixa_id = m.id) "
                          "AND NOT EXISTS (SELECT 1 FROM titulo t WHERE t.origem_tipo = 'sangria' AND t.origem_id = m.id)", (loja_id,)).fetchall():
        tid = _novo(conn, loja_id=loja_id, sentido="pagar", descricao=f"Caixa: {m['motivo_nome']}", valor=m["valor"], vencimento=m["data"],
                    competencia=m["data"].replace(day=1), comprovante=m["comprovante"], origem_tipo="sangria", origem_id=m["id"], criado_em=quando, criado_por=m["usuario_id"])
        if tid:
            n["sangria"] += 1
            baixar(conn, tid, m["data"], m["valor"], "dinheiro", None, m["usuario_id"])

    # Acerto do entregador: conta a pagar baixada no acerto do dia.
    for a in conn.execute("SELECT a.*, e.nome FROM acerto_entregador a JOIN entregador e ON e.id = a.entregador_id WHERE a.loja_id = %s AND a.total_devido > 0 "
                          "AND NOT EXISTS (SELECT 1 FROM titulo t WHERE t.origem_tipo = 'acerto_entregador' AND t.origem_id = a.id)", (loja_id,)).fetchall():
        tid = _novo(conn, loja_id=loja_id, sentido="pagar", descricao=f"Entregador {a['nome']} ({a['pedidos']} entrega(s))", valor=a["total_devido"], vencimento=a["data"],
                    competencia=a["data"].replace(day=1), origem_tipo="acerto_entregador", origem_id=a["id"], criado_em=quando, criado_por=a["usuario_id"])
        if tid:
            n["acerto_entregador"] += 1
            baixar(conn, tid, a["data"], a["total_devido"], "dinheiro", None, a["usuario_id"])

    # Caixa fechado: crédito, débito e Pix viram a receber, com a taxa e o prazo da regra vigente.
    for c in conn.execute("SELECT k.id, k.forma, k.esperado, d.data FROM contagem_caixa k JOIN caixa_dia d ON d.id = k.caixa_id "
                          "WHERE d.loja_id = %s AND d.situacao = 'fechado' AND k.forma <> 'dinheiro' AND k.esperado > 0 "
                          "AND NOT EXISTS (SELECT 1 FROM titulo t WHERE t.origem_tipo = 'fechamento' AND t.origem_id = k.id)", (loja_id,)).fetchall():
        reg = conn.execute("SELECT taxa_pct, prazo_dias FROM regra_recebimento WHERE loja_id = %s AND forma = %s AND maquininha_id IS NULL ORDER BY vigente_desde DESC, id DESC LIMIT 1",
                           (loja_id, c["forma"])).fetchone()
        taxa, prazo = (reg["taxa_pct"], reg["prazo_dias"]) if reg else (ZERO, 0)
        if _novo(conn, loja_id=loja_id, sentido="receber", descricao=f"Vendas em {c['forma']} de {c['data'].strftime('%d/%m/%Y')}", canal=c["forma"], valor=c["esperado"],
                 taxa_pct=taxa, vencimento=c["data"] + timedelta(days=prazo), competencia=c["data"].replace(day=1), origem_tipo="fechamento", origem_id=c["id"],
                 criado_em=quando, criado_por=None):
            n["fechamento"] += 1

    # Despesas recorrentes: um título por mês, do início até o mês que vem (no máximo 24 meses para trás).
    limite = _soma_meses(hoje.replace(day=1), 1)
    for r in conn.execute("SELECT * FROM recorrente WHERE loja_id = %s AND ativo", (loja_id,)).fetchall():
        mes = max(r["inicio"].replace(day=1), _soma_meses(hoje.replace(day=1), -24))
        while mes <= limite:
            venc = mes.replace(day=r["dia_vencimento"])
            if venc >= r["inicio"] and (r["fim"] is None or venc <= r["fim"]):
                if _novo(conn, loja_id=loja_id, sentido="pagar", descricao=r["descricao"], fornecedor_id=r["fornecedor_id"], tipo_despesa_id=r["tipo_despesa_id"],
                         valor=r["valor"], vencimento=venc, competencia=mes, origem_tipo="recorrencia", origem_id=r["id"], criado_em=quando, criado_por=r["criado_por"]):
                    n["recorrencia"] += 1
            mes = _soma_meses(mes, 1)
    return n


def saldo_conta(conn, conta: dict, ate: date | None = None) -> Decimal:
    """Saldo inicial mais o que entrou menos o que saiu pelas baixas na conta, a partir da data do saldo inicial."""
    r = conn.execute("SELECT COALESCE(sum(CASE WHEN t.sentido = 'receber' THEN b.valor_movimento ELSE -b.valor_movimento END), 0) AS s "
                     "FROM baixa_titulo b JOIN titulo t ON t.id = b.titulo_id WHERE b.conta_id = %s AND b.data >= %s AND (%s::date IS NULL OR b.data <= %s::date)",
                     (conta["id"], conta["saldo_inicial_data"], ate, ate)).fetchone()
    return Decimal(conta["saldo_inicial"]) + Decimal(r["s"])
