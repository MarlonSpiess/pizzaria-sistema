"""Contas a pagar e receber, contas bancárias, conciliação do extrato e fluxo de caixa."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (AtivoIn, BaixaIn, CancelarTituloIn, CanalRepasseIn, ConciliarIn, ContaBancariaIn, ExtratoIn, RecorrenteIn, TipoDespesaIn, TituloIn)
from api.security import PERMISSOES, requer
from api.services import contas as svc
from api.services.dinheiro import fmt, parse_reais
from api.services.parametros import vigentes

router = APIRouter(prefix="/contas", tags=["contas"])
ZERO = Decimal("0.00")
TIPOS_PADRAO = [("Aluguel", "fixa"), ("Energia", "fixa"), ("Gás", "fixa"), ("Água", "fixa"), ("Internet e telefone", "fixa"), ("Folha de pagamento", "pessoal"),
                ("Impostos", "tributo"), ("Empréstimos e financiamentos", "financiamento"), ("Manutenção", "variavel"), ("Marketing", "variavel"),
                ("Pequenas despesas do caixa", "variavel"), ("Retirada de sócio", "retirada")]


def _ex(conn, e):
    conn.rollback()
    raise traduzir_erro(e) from e


# ---------------------------------------------------------------- cadastros
@router.get("/contas-bancarias")
def contas_bancarias(sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    return [c | {"saldo_inicial": fmt(c["saldo_inicial"]), "saldo": fmt(svc.saldo_conta(conn, c))} for c in conn.execute(
        "SELECT * FROM conta_bancaria WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()]


@router.post("/contas-bancarias", status_code=201)
def criar_conta(d: ContaBancariaIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO conta_bancaria (loja_id, nome, banco, agencia, numero, tipo, saldo_inicial, saldo_inicial_data) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.nome, d.banco, d.agencia, d.numero, d.tipo, parse_reais(d.saldo_inicial), d.saldo_inicial_data)).fetchone()
        auditar(conn, sessao, "criar", "conta_bancaria", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/contas-bancarias/{cid}")
def ativar_conta(cid: int, d: AtivoIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    return _ativar(conn, sessao, "conta_bancaria", cid, d.ativo)


def _ativar(conn, sessao, tabela, rid, ativo):
    r = conn.execute(f"UPDATE {tabela} SET ativo = %s WHERE id = %s AND loja_id = %s RETURNING id", (ativo, rid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")
    auditar(conn, sessao, "ativar" if ativo else "inativar", tabela, rid)
    conn.commit()
    return {"id": rid, "ativo": ativo}


@router.get("/tipos-despesa")
def tipos(sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    return conn.execute("SELECT id, nome, natureza, ativo FROM tipo_despesa WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()


@router.post("/tipos-despesa", status_code=201)
def criar_tipo(d: TipoDespesaIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO tipo_despesa (loja_id, nome, natureza) VALUES (%s,%s,%s) RETURNING id", (LOJA_ID, d.nome, d.natureza)).fetchone()
        auditar(conn, sessao, "criar", "tipo_despesa", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.post("/tipos-despesa/iniciar-padrao", status_code=201)
def tipos_padrao(sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    if conn.execute("SELECT 1 FROM tipo_despesa WHERE loja_id = %s LIMIT 1", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=409, detail="Os tipos de despesa já foram criados.")
    for nome, nat in TIPOS_PADRAO:
        conn.execute("INSERT INTO tipo_despesa (loja_id, nome, natureza) VALUES (%s,%s,%s)", (LOJA_ID, nome, nat))
    auditar(conn, sessao, "iniciar-padrao", "tipo_despesa", None, depois={"quantidade": len(TIPOS_PADRAO)})
    conn.commit()
    return {"criados": len(TIPOS_PADRAO)}


@router.patch("/tipos-despesa/{tid}")
def ativar_tipo(tid: int, d: AtivoIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    return _ativar(conn, sessao, "tipo_despesa", tid, d.ativo)


@router.get("/canais")
def canais(sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    return [c | {"taxa_pct": fmt(c["taxa_pct"])} for c in conn.execute("SELECT id, canal, taxa_pct, prazo_dias, ativo FROM canal_repasse WHERE loja_id = %s ORDER BY canal", (LOJA_ID,)).fetchall()]


@router.post("/canais", status_code=201)
def criar_canal(d: CanalRepasseIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO canal_repasse (loja_id, canal, taxa_pct, prazo_dias) VALUES (%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.canal, d.taxa_pct, d.prazo_dias)).fetchone()
        auditar(conn, sessao, "criar", "canal_repasse", r["id"], depois={"canal": d.canal})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/canais/{cid}")
def ativar_canal(cid: int, d: AtivoIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    return _ativar(conn, sessao, "canal_repasse", cid, d.ativo)


@router.get("/recorrentes")
def recorrentes(sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    return [r | {"valor": fmt(r["valor"])} for r in conn.execute(
        "SELECT r.id, r.descricao, r.valor, r.dia_vencimento, r.inicio, r.fim, r.ativo, t.nome AS tipo, f.nome AS fornecedor FROM recorrente r "
        "JOIN tipo_despesa t ON t.id = r.tipo_despesa_id LEFT JOIN fornecedor f ON f.id = r.fornecedor_id WHERE r.loja_id = %s ORDER BY r.descricao", (LOJA_ID,)).fetchall()]


@router.post("/recorrentes", status_code=201)
def criar_recorrente(d: RecorrenteIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM tipo_despesa WHERE id = %s AND loja_id = %s AND ativo", (d.tipo_despesa_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Tipo de despesa não encontrado.")
    if d.fornecedor_id and not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s", (d.fornecedor_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    if d.fim and d.fim < d.inicio:
        raise HTTPException(status_code=400, detail="O fim não pode ser antes do início.")
    try:
        r = conn.execute("INSERT INTO recorrente (loja_id, descricao, tipo_despesa_id, fornecedor_id, valor, dia_vencimento, inicio, fim, criado_em, criado_por) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.descricao, d.tipo_despesa_id, d.fornecedor_id, parse_reais(d.valor), d.dia_vencimento,
                                                                                 d.inicio, d.fim, agora(), sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "criar", "recorrente", r["id"], depois={"descricao": d.descricao, "valor": d.valor})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/recorrentes/{rid}")
def ativar_recorrente(rid: int, d: AtivoIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    return _ativar(conn, sessao, "recorrente", rid, d.ativo)


# ---------------------------------------------------------------- títulos
def _titulo_out(t: dict, hoje: date) -> dict:
    pago = Decimal(t.get("pago") or 0)
    saldo = Decimal(t["valor"]) - pago
    aberto = t["situacao"] in ("aberto", "parcial") and t["aprovado"]
    out = {k: t[k] for k in ("id", "sentido", "descricao", "fornecedor", "tipo_despesa", "canal", "vencimento", "competencia", "origem_tipo", "parcela_num", "parcela_total",
                             "comprovante", "aprovado", "situacao", "cancelado_motivo")}
    out |= {"valor": fmt(t["valor"]), "pago": fmt(pago), "saldo": fmt(saldo), "taxa_pct": fmt(t["taxa_pct"]), "atrasado": bool(aberto and t["vencimento"] < hoje),
            "dias_atraso": (hoje - t["vencimento"]).days if aberto and t["vencimento"] < hoje else 0}
    if t["sentido"] == "receber" and t.get("desconto_total") is not None and pago > 0:
        out["taxa_real_pct"] = fmt(Decimal(t["desconto_total"]) / pago * 100)
    return out


_SQL_TITULO = ("SELECT t.*, f.nome AS fornecedor, d.nome AS tipo_despesa, (SELECT COALESCE(sum(valor),0) FROM baixa_titulo WHERE titulo_id = t.id) AS pago, "
               "(SELECT COALESCE(sum(desconto),0) FROM baixa_titulo WHERE titulo_id = t.id) AS desconto_total FROM titulo t "
               "LEFT JOIN fornecedor f ON f.id = t.fornecedor_id LEFT JOIN tipo_despesa d ON d.id = t.tipo_despesa_id")


@router.post("/sincronizar")
def sincronizar(sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    """Traz para cá as notas, despesas do caixa, acertos de entregador, vendas a receber e recorrências ainda não lançadas."""
    try:
        n = svc.sincronizar(conn, LOJA_ID)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return n


@router.get("/titulos")
def titulos(sentido: Optional[str] = None, situacao: Optional[str] = None, de: Optional[date] = None, ate: Optional[date] = None, atrasados: bool = False,
            sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    """Lista os títulos. A sincronização roda antes, para a tela nunca mostrar defasagem."""
    try:
        svc.sincronizar(conn, LOJA_ID)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    if sentido not in (None, "pagar", "receber") or situacao not in (None, "aberto", "parcial", "baixado", "cancelado", "pendente"):
        raise HTTPException(status_code=400, detail="Filtro inválido.")
    sql, p = _SQL_TITULO + " WHERE t.loja_id = %s", [LOJA_ID]
    if sentido:
        sql, p = sql + " AND t.sentido = %s", p + [sentido]
    if situacao == "pendente":
        sql += " AND NOT t.aprovado AND t.situacao <> 'cancelado'"
    elif situacao:
        sql, p = sql + " AND t.situacao = %s", p + [situacao]
    if de:
        sql, p = sql + " AND t.vencimento >= %s", p + [de]
    if ate:
        sql, p = sql + " AND t.vencimento <= %s", p + [ate]
    if "rh.salarios" not in PERMISSOES.get(sessao["perfil"], set()):
        sql += " AND t.origem_tipo <> 'folha'"
    hoje = agora().date()
    if atrasados:
        sql, p = sql + " AND t.situacao IN ('aberto','parcial') AND t.aprovado AND t.vencimento < %s", p + [hoje]
    if situacao is None:  # os em aberto vêm sempre; dos já resolvidos, só os 200 mais recentes
        ab = conn.execute(sql + " AND (t.situacao IN ('aberto','parcial') OR (NOT t.aprovado AND t.situacao <> 'cancelado')) ORDER BY t.vencimento, t.id LIMIT 3000", p).fetchall()
        fe = conn.execute(sql + " AND t.situacao IN ('baixado','cancelado') ORDER BY t.vencimento DESC, t.id DESC LIMIT 200", p).fetchall()
        return [_titulo_out(t, hoje) for t in sorted(ab + fe[::-1], key=lambda t: (t["vencimento"], t["id"]))]
    return [_titulo_out(t, hoje) for t in conn.execute(sql + " ORDER BY t.vencimento, t.id LIMIT 3000", p).fetchall()]


@router.post("/titulos", status_code=201)
def criar_titulo(d: TituloIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    valor = parse_reais(d.valor)
    if d.fornecedor_id and not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s", (d.fornecedor_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    if d.tipo_despesa_id and not conn.execute("SELECT 1 FROM tipo_despesa WHERE id = %s AND loja_id = %s AND ativo", (d.tipo_despesa_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Tipo de despesa não encontrado.")
    if d.sentido == "pagar" and not d.tipo_despesa_id:
        raise HTTPException(status_code=400, detail="Informe o tipo de despesa.")
    aprovado = True
    if d.sentido == "pagar":
        lim = vigentes(conn, LOJA_ID)["conta_valor_aprovacao"]["valor"]
        if lim is not None:  # o limite vale para o total do lançamento e para o acumulado do dia de quem lança (fracionar não foge)
            hoje_ = agora().date()
            ja = conn.execute("SELECT COALESCE(sum(valor), 0) AS s FROM titulo WHERE loja_id = %s AND criado_por = %s AND sentido = 'pagar' AND origem_tipo IN ('manual','parcela') "
                              "AND situacao <> 'cancelado' AND criado_em::date = %s", (LOJA_ID, sessao["usuario_id"], hoje_)).fetchone()["s"]
            aprovado = ja + valor <= Decimal(lim)
        else:
            aprovado = True
    if d.vencimento.year > 2100 or d.vencimento < date(2000, 1, 1):
        raise HTTPException(status_code=400, detail="Vencimento fora do intervalo aceito.")
    parc = (valor / d.parcelas).quantize(svc.Q2)
    if parc < Decimal("0.01"):
        raise HTTPException(status_code=400, detail="O valor é pequeno demais para este número de parcelas.")
    ids, quando = [], agora()
    try:
        for i in range(d.parcelas):
            v = parc if i < d.parcelas - 1 else valor - parc * (d.parcelas - 1)  # a última absorve o centavo da divisão
            venc = svc._soma_meses(d.vencimento, i)
            r = conn.execute("INSERT INTO titulo (loja_id, sentido, descricao, fornecedor_id, tipo_despesa_id, canal, valor, vencimento, competencia, origem_tipo, parcela_num, parcela_total, "
                             "comprovante, aprovado, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                             (LOJA_ID, d.sentido, d.descricao, d.fornecedor_id, d.tipo_despesa_id, d.canal, v, venc, d.competencia, "parcela" if d.parcelas > 1 else "manual",
                              i + 1 if d.parcelas > 1 else None, d.parcelas if d.parcelas > 1 else None, d.comprovante, aprovado, quando, sessao["usuario_id"])).fetchone()
            ids.append(r["id"])
        if d.parcelas > 1:
            conn.execute("UPDATE titulo SET grupo_id = %s WHERE id = ANY(%s)", (ids[0], ids))
        auditar(conn, sessao, "criar", "titulo", ids[0], depois={"sentido": d.sentido, "valor": fmt(valor), "parcelas": d.parcelas, "aprovado": aprovado})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"ids": ids, "aprovado": aprovado}


def conta_data(conn, conta_id):
    return conn.execute("SELECT saldo_inicial_data FROM conta_bancaria WHERE id = %s", (conta_id,)).fetchone()["saldo_inicial_data"]


def _travar(conn, tid):
    t = conn.execute("SELECT * FROM titulo WHERE id = %s AND loja_id = %s FOR UPDATE", (tid, LOJA_ID)).fetchone()
    if not t:
        raise HTTPException(status_code=404, detail="Título não encontrado.")
    return t


@router.post("/titulos/{tid}/aprovar")
def aprovar(tid: int, sessao=Depends(requer("contas.aprovar")), conn=Depends(get_db)):
    t = _travar(conn, tid)
    if t["aprovado"]:
        raise HTTPException(status_code=409, detail="O título já está aprovado.")
    if t["situacao"] == "cancelado":
        raise HTTPException(status_code=409, detail="O título está cancelado.")
    if t["criado_por"] == sessao["usuario_id"]:
        raise HTTPException(status_code=403, detail="Quem lançou o título não pode aprová-lo.")
    ids = [x["id"] for x in conn.execute("SELECT id FROM titulo WHERE loja_id = %s AND NOT aprovado AND situacao <> 'cancelado' AND (id = %s OR (grupo_id IS NOT NULL AND grupo_id = %s)) FOR UPDATE",
                                         (LOJA_ID, tid, t["grupo_id"])).fetchall()]
    try:
        conn.execute("UPDATE titulo SET aprovado = true, aprovado_por = %s WHERE id = ANY(%s)", (sessao["usuario_id"], ids))
        auditar(conn, sessao, "aprovar", "titulo", tid, depois={"titulos": ids})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"aprovados": ids}


@router.post("/titulos/{tid}/cancelar")
def cancelar(tid: int, d: CancelarTituloIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    t = _travar(conn, tid)
    if t["origem_tipo"] not in ("manual", "parcela", "recorrencia"):
        raise HTTPException(status_code=409, detail="Título criado por outra área do sistema: corrija na origem.")
    if t["situacao"] != "aberto":
        raise HTTPException(status_code=409, detail="Só se cancela título sem nenhuma baixa.")
    try:
        conn.execute("UPDATE titulo SET situacao = 'cancelado', cancelado_motivo = %s WHERE id = %s", (d.motivo, tid))
        auditar(conn, sessao, "cancelar", "titulo", tid, depois={"motivo": d.motivo})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": tid, "situacao": "cancelado"}


@router.post("/titulos/{tid}/baixas", status_code=201)
def dar_baixa(tid: int, d: BaixaIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    t = _travar(conn, tid)
    if t["situacao"] in ("baixado", "cancelado"):
        raise HTTPException(status_code=409, detail=f"O título está {t['situacao']}.")
    if not t["aprovado"]:
        raise HTTPException(status_code=409, detail="O título aguarda aprovação.")
    conta = conn.execute("SELECT id, ativo FROM conta_bancaria WHERE id = %s AND loja_id = %s", (d.conta_id, LOJA_ID)).fetchone()
    if not conta or not conta["ativo"]:
        raise HTTPException(status_code=404, detail="Conta não encontrada ou inativa.")
    hoje = agora().date()
    data = d.data or hoje
    if data > hoje:
        raise HTTPException(status_code=400, detail="A baixa não pode ter data futura.")
    pago = conn.execute("SELECT COALESCE(sum(valor),0) AS s FROM baixa_titulo WHERE titulo_id = %s", (tid,)).fetchone()["s"]
    saldo = t["valor"] - pago
    valor = parse_reais(d.valor) if d.valor else saldo
    desconto, juros, multa = parse_reais(d.desconto), parse_reais(d.juros), parse_reais(d.multa)
    if valor > saldo:
        raise HTTPException(status_code=400, detail=f"A baixa passa do saldo do título (R$ {fmt(saldo)}).")
    if desconto > valor:
        raise HTTPException(status_code=400, detail="O desconto não pode passar do valor baixado.")
    if data < conta_data(conn, d.conta_id):
        raise HTTPException(status_code=400, detail="A baixa é anterior ao saldo inicial da conta.")
    if valor - desconto + juros + multa <= 0:
        raise HTTPException(status_code=400, detail="Baixa sem movimento de dinheiro: informe o desconto menor que o valor.")
    if (desconto + juros + multa) * 5 > valor and "contas.aprovar" not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=403, detail="Desconto, juros ou multa acima de 20% do valor: só o administrador ou o proprietário baixa assim.")
    try:
        r = svc.baixar(conn, tid, data, valor, d.forma, d.conta_id, sessao["usuario_id"], desconto, juros, multa)
        auditar(conn, sessao, "baixar", "titulo", tid, depois={"valor": fmt(valor), "desconto": fmt(desconto), "juros": fmt(juros), "multa": fmt(multa), "conta_id": d.conta_id})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"baixa_id": r["baixa_id"], "valor_movimento": fmt(r["valor_movimento"])}


# ---------------------------------------------------------------- extrato e conciliação
@router.post("/extrato", status_code=201)
def lancar_extrato(d: ExtratoIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM conta_bancaria WHERE id = %s AND loja_id = %s", (d.conta_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    neg = d.valor.startswith("-")
    v = Decimal(d.valor)
    try:
        r = conn.execute("INSERT INTO extrato_linha (conta_id, data, descricao, valor, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                         (d.conta_id, d.data, d.descricao, -abs(v) if neg else abs(v), sessao["usuario_id"], agora())).fetchone()
        auditar(conn, sessao, "criar", "extrato_linha", r["id"], depois={"conta_id": d.conta_id, "valor": d.valor})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.get("/conciliacao/{conta_id}")
def pendencias_conciliacao(conta_id: int, sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    """Linhas do extrato e baixas da conta que ainda não foram casadas."""
    if not conn.execute("SELECT 1 FROM conta_bancaria WHERE id = %s AND loja_id = %s", (conta_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    ext = conn.execute("SELECT id, data, descricao, valor FROM extrato_linha e WHERE conta_id = %s AND NOT EXISTS (SELECT 1 FROM conciliacao c WHERE c.extrato_id = e.id) ORDER BY data, id", (conta_id,)).fetchall()
    bx = conn.execute("SELECT b.id, b.data, t.descricao, t.sentido, b.forma, b.valor_movimento FROM baixa_titulo b JOIN titulo t ON t.id = b.titulo_id "
                      "WHERE b.conta_id = %s AND NOT EXISTS (SELECT 1 FROM conciliacao c WHERE c.baixa_id = b.id) ORDER BY b.data, b.id", (conta_id,)).fetchall()
    return {"extrato": [e | {"valor": fmt(e["valor"])} for e in ext],
            "baixas": [b | {"valor_movimento": fmt(b["valor_movimento"]), "valor_com_sinal": fmt(b["valor_movimento"] if b["sentido"] == "receber" else -b["valor_movimento"])} for b in bx]}


@router.post("/conciliacao", status_code=201)
def conciliar(d: ConciliarIn, sessao=Depends(requer("contas.operar")), conn=Depends(get_db)):
    e = conn.execute("SELECT e.* FROM extrato_linha e JOIN conta_bancaria c ON c.id = e.conta_id WHERE e.id = %s AND c.loja_id = %s", (d.extrato_id, LOJA_ID)).fetchone()
    b = conn.execute("SELECT b.*, t.sentido FROM baixa_titulo b JOIN titulo t ON t.id = b.titulo_id WHERE b.id = %s AND t.loja_id = %s", (d.baixa_id, LOJA_ID)).fetchone()
    if not e or not b:
        raise HTTPException(status_code=404, detail="Linha do extrato ou baixa não encontrada.")
    if e["conta_id"] != b["conta_id"]:
        raise HTTPException(status_code=400, detail="A linha do extrato e a baixa são de contas diferentes.")
    esperado = b["valor_movimento"] if b["sentido"] == "receber" else -b["valor_movimento"]
    if e["valor"] != esperado:
        raise HTTPException(status_code=400, detail=f"O extrato mostra R$ {fmt(e['valor'])} e a baixa R$ {fmt(esperado)}: ajuste a baixa (desconto, juros ou multa) antes de casar.")
    try:
        conn.execute("INSERT INTO conciliacao (extrato_id, baixa_id, usuario_id, criado_em) VALUES (%s,%s,%s,%s)", (d.extrato_id, d.baixa_id, sessao["usuario_id"], agora()))
        auditar(conn, sessao, "conciliar", "conciliacao", None, depois={"extrato_id": d.extrato_id, "baixa_id": d.baixa_id})
        conn.commit()
    except psycopg.Error as ex:
        _ex(conn, ex)
    return {"conciliado": True}


# ---------------------------------------------------------------- fluxo de caixa
@router.get("/fluxo")
def fluxo(dias: int = 30, sessao=Depends(requer("contas.ver")), conn=Depends(get_db)):
    """Saldo das contas hoje e projeção diária: títulos abertos entram no vencimento (atrasados, hoje). O dinheiro da gaveta fica no Fechamento de Caixa."""
    if not 1 <= dias <= 365:
        raise HTTPException(status_code=400, detail="Informe de 1 a 365 dias.")
    try:
        svc.sincronizar(conn, LOJA_ID)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    hoje = agora().date()
    contas = conn.execute("SELECT * FROM conta_bancaria WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()
    saldos = [{"id": c["id"], "nome": c["nome"], "saldo": fmt(svc.saldo_conta(conn, c)), "ativo": c["ativo"]} for c in contas]
    saldo = sum((svc.saldo_conta(conn, c) for c in contas), ZERO)
    prev = {}
    for t in conn.execute("SELECT t.sentido, t.vencimento, (t.valor - COALESCE((SELECT sum(valor) FROM baixa_titulo WHERE titulo_id = t.id), 0)) * (1 - CASE WHEN t.sentido = 'receber' THEN COALESCE(t.taxa_pct, 0) / 100 ELSE 0 END) AS saldo FROM titulo t "
                          "WHERE t.loja_id = %s AND t.situacao IN ('aberto','parcial') AND t.vencimento <= %s", (LOJA_ID, hoje + timedelta(days=dias))).fetchall():
        dia = max(t["vencimento"], hoje)
        e = prev.setdefault(dia, [ZERO, ZERO])
        e[0 if t["sentido"] == "receber" else 1] += t["saldo"]
    linhas, atual = [], saldo
    for i in range(dias + 1):
        dia = hoje + timedelta(days=i)
        ent, sai = prev.get(dia, [ZERO, ZERO])
        atual += ent - sai
        linhas.append({"data": dia, "entradas": fmt(ent), "saidas": fmt(sai), "saldo": fmt(atual), "destaque": i < 7, "negativo": atual < 0})
    real = conn.execute("SELECT b.data, COALESCE(sum(CASE WHEN t.sentido = 'receber' THEN b.valor_movimento END), 0) AS entradas, COALESCE(sum(CASE WHEN t.sentido = 'pagar' THEN b.valor_movimento END), 0) AS saidas "
                        "FROM baixa_titulo b JOIN titulo t ON t.id = b.titulo_id WHERE t.loja_id = %s AND b.conta_id IS NOT NULL AND b.data BETWEEN %s AND %s GROUP BY b.data ORDER BY b.data",
                        (LOJA_ID, hoje - timedelta(days=30), hoje)).fetchall()
    return {"hoje": hoje, "saldo_atual": fmt(saldo), "contas": saldos, "projecao": linhas, "menor_saldo": fmt(min(Decimal(x["saldo"]) for x in linhas)),
            "realizado_30d": [{"data": r["data"], "entradas": fmt(r["entradas"]), "saidas": fmt(r["saidas"])} for r in real]}
