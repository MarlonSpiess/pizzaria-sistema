"""Valor esperado do caixa por forma de pagamento e relatório. Tudo em Decimal, calculado dos registros, nunca digitado.
O caixa cobre da data em que abriu até o fechamento: se a loja vende depois da meia-noite, o mesmo caixa segue aberto."""
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

ZERO = Decimal("0.00")
FORMAS = ("dinheiro", "pix", "credito", "debito")
FIM = date(9999, 12, 31)


def _soma(conn, sql, params) -> Decimal:
    return conn.execute(sql, params).fetchone()["s"] or ZERO


def faixa(conn, loja_id: int, caixa: dict) -> tuple:
    """Datas cobertas pelo caixa: da abertura até o dia anterior à abertura do caixa seguinte (ou sem fim, se é o último)."""
    prox = conn.execute("SELECT min(data) AS d FROM caixa_dia WHERE loja_id = %s AND data > %s", (loja_id, caixa["data"])).fetchone()["d"]
    return caixa["data"], prox or FIM


def ultimo_caixa(conn, loja_id: int, trava: str | None = None) -> dict | None:
    sufixo = {"share": " FOR SHARE", "update": " FOR UPDATE"}.get(trava, "")
    return conn.execute("SELECT * FROM caixa_dia WHERE loja_id = %s ORDER BY data DESC LIMIT 1" + sufixo, (loja_id,)).fetchone()


def esperado(conn, loja_id: int, fx: tuple, fundo: Decimal) -> dict:
    """Esperado por forma. O dinheiro soma o fundo e os suprimentos e tira sangrias, o que ainda está com entregadores e o pago a eles."""
    de, ate = fx
    saida = {}
    for f in FORMAS:
        recebido = _soma(conn, "SELECT sum(p.valor - p.troco) AS s FROM pagamento p JOIN pedido ped ON ped.id = p.pedido_id "
                               "WHERE ped.loja_id = %s AND ped.data >= %s AND ped.data < %s AND p.forma = %s", (loja_id, de, ate, f))
        estornos = _soma(conn, "SELECT sum(valor) AS s FROM estorno WHERE loja_id = %s AND data >= %s AND data < %s AND forma = %s", (loja_id, de, ate, f))
        saida[f] = recebido - estornos
    suprim = _soma(conn, "SELECT sum(valor) AS s FROM movimento_caixa WHERE loja_id = %s AND data >= %s AND data < %s AND tipo = 'suprimento'", (loja_id, de, ate))
    sangria = _soma(conn, "SELECT sum(valor) AS s FROM movimento_caixa WHERE loja_id = %s AND data >= %s AND data < %s AND tipo = 'sangria'", (loja_id, de, ate))
    com_entregador = _soma(conn, "SELECT sum(p.valor - p.troco) AS s FROM pagamento p JOIN pedido ped ON ped.id = p.pedido_id "
                                 "JOIN entrega e ON e.pedido_id = ped.id WHERE ped.loja_id = %s AND ped.data >= %s AND ped.data < %s AND p.forma = 'dinheiro' "
                                 "AND e.acerto_id IS NULL AND ped.situacao <> 'cancelado'", (loja_id, de, ate))
    pago_entregadores = _soma(conn, "SELECT sum(total_devido) AS s FROM acerto_entregador WHERE loja_id = %s AND data >= %s AND data < %s", (loja_id, de, ate))
    saida["dinheiro"] += fundo + suprim - sangria - com_entregador - pago_entregadores
    return saida


def formas_com_movimento(conn, loja_id: int, fx: tuple) -> set:
    """Formas que tiveram venda ou estorno no período: entram na contagem mesmo que tenham saído dos parâmetros depois."""
    de, ate = fx
    r = conn.execute("SELECT DISTINCT p.forma FROM pagamento p JOIN pedido ped ON ped.id = p.pedido_id WHERE ped.loja_id = %s AND ped.data >= %s AND ped.data < %s",
                     (loja_id, de, ate)).fetchall()
    e = conn.execute("SELECT DISTINCT forma FROM estorno WHERE loja_id = %s AND data >= %s AND data < %s", (loja_id, de, ate)).fetchall()
    return {x["forma"] for x in r} | {x["forma"] for x in e} | {"dinheiro"}


def relatorio(conn, loja_id: int, fx: tuple, caixa: dict | None, mostrar_esperado: bool) -> dict:
    """Totais do período do caixa. O esperado e as diferenças só aparecem depois da contagem (contagem cega)."""
    de, ate = fx
    por_forma = {f: _soma(conn, "SELECT sum(p.valor - p.troco) AS s FROM pagamento p JOIN pedido ped ON ped.id = p.pedido_id "
                                "WHERE ped.loja_id = %s AND ped.data >= %s AND ped.data < %s AND p.forma = %s", (loja_id, de, ate, f)) for f in FORMAS}
    mov = conn.execute("SELECT m.id, m.tipo, m.valor, m.motivo_nome AS motivo, m.vira_despesa, m.observacao, m.comprovante, m.criado_em "
                       "FROM movimento_caixa m WHERE m.loja_id = %s AND m.data >= %s AND m.data < %s ORDER BY m.id", (loja_id, de, ate)).fetchall()
    estornos = conn.execute("SELECT e.pedido_id, ped.id_dia, e.forma, e.valor, e.motivo FROM estorno e JOIN pedido ped ON ped.id = e.pedido_id "
                            "WHERE e.loja_id = %s AND e.data >= %s AND e.data < %s ORDER BY e.id", (loja_id, de, ate)).fetchall()
    ped = conn.execute("SELECT count(*) FILTER (WHERE situacao <> 'cancelado') AS pedidos, "
                       "COALESCE(sum(desconto) FILTER (WHERE situacao <> 'cancelado'), 0) AS descontos, "
                       "COALESCE(sum(acrescimo) FILTER (WHERE situacao <> 'cancelado'), 0) AS acrescimos, "
                       "COALESCE(sum(total) FILTER (WHERE situacao <> 'cancelado'), 0) AS vendas "
                       "FROM pedido WHERE loja_id = %s AND data >= %s AND data < %s", (loja_id, de, ate)).fetchone()
    cancel = conn.execute("SELECT count(*) AS n, COALESCE(sum(ped.total), 0) AS valor FROM cancelamento c JOIN pedido ped ON ped.id = c.pedido_id "
                          "WHERE ped.loja_id = %s AND c.criado_em::date >= %s AND c.criado_em::date < %s", (loja_id, de, ate)).fetchone()
    sem_cf = conn.execute("SELECT id, id_dia, total FROM pedido WHERE loja_id = %s AND data >= %s AND data < %s AND numero_cf IS NULL AND situacao <> 'cancelado' "
                          "ORDER BY data, id_dia", (loja_id, de, ate)).fetchall()
    acertos = conn.execute("SELECT a.id, e.nome AS entregador, a.pedidos, a.dinheiro_recebido, a.valor_entregas, a.diaria, a.total_devido, a.saldo_gaveta "
                           "FROM acerto_entregador a JOIN entregador e ON e.id = a.entregador_id WHERE a.loja_id = %s AND a.data >= %s AND a.data < %s ORDER BY a.id",
                           (loja_id, de, ate)).fetchall()
    r = {"data": de, "caixa": caixa, "recebido_por_forma": por_forma, "movimentos": mov, "estornos": estornos, "pedidos": ped["pedidos"],
         "vendas": ped["vendas"], "descontos": ped["descontos"], "acrescimos": ped["acrescimos"], "cancelamentos": cancel,
         "pedidos_sem_cf": sem_cf, "acertos": acertos}
    if mostrar_esperado and caixa:
        r["contagens"] = conn.execute("SELECT forma, contado, esperado, diferenca FROM contagem_caixa WHERE caixa_id = %s ORDER BY id", (caixa["id"],)).fetchall()
    return r


def exigir_aberto(conn, loja_id: int, trava: str = "share") -> dict:
    """O caixa em uso precisa existir e estar aberto (nem contado, nem fechado)."""
    c = ultimo_caixa(conn, loja_id, trava)
    if not c or c["situacao"] == "fechado":
        raise HTTPException(status_code=409, detail="O caixa não está aberto.")
    if c["situacao"] != "aberto":
        raise HTTPException(status_code=409, detail=f"O caixa já está {c['situacao']}: não aceita novos lançamentos.")
    return c


def exigir_nao_encerrado(conn, loja_id: int, hoje: date, exige_aberto: bool) -> None:
    """Vendas e cancelamentos: nunca depois da contagem; se o parâmetro mandar, só com o caixa aberto."""
    c = ultimo_caixa(conn, loja_id, "share")
    if c and c["situacao"] == "contado":
        raise HTTPException(status_code=409, detail="O caixa já está contado: não aceita novos lançamentos.")
    if c and c["situacao"] == "fechado" and c["data"] == hoje:
        raise HTTPException(status_code=409, detail="O caixa de hoje já está fechado: não aceita novos lançamentos.")
    if exige_aberto and (not c or c["situacao"] == "fechado"):
        raise HTTPException(status_code=409, detail="Abra o caixa do dia antes de vender.")


def tolerancia(par: dict) -> Decimal:
    v = par["tolerancia_diferenca_caixa"]["valor"]
    return Decimal(v) if v is not None else ZERO


def caixa_do_dia(conn, loja_id: int, data) -> dict | None:
    return conn.execute("SELECT * FROM caixa_dia WHERE loja_id = %s AND data = %s", (loja_id, data)).fetchone()
