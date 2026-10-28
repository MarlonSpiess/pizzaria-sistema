"""BI: painel do dia, DRE por competência, lucratividade, indicadores de produção e alertas. Só leitura; salários e resultado só com rh.salarios."""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from api.config import LOJA_ID
from api.database import agora, get_db
from api.routers import contas as contas_r
from api.routers import estoque as estoque_r
from api.routers import imobilizado as imob_r
from api.security import PERMISSOES, requer
from api.services import contas as contas_svc
from api.services import custos as custos_svc
from api.services.dinheiro import fmt
from api.services.parametros import vigentes

router = APIRouter(prefix="/bi", tags=["bi"])
ZERO = Decimal("0")
Q2 = Decimal("0.01")
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


def _mes(m: Optional[str]) -> date:
    if m is None:
        return agora().date().replace(day=1)
    try:
        a, b = m.split("-")
        d = date(int(a), int(b), 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Mês no formato AAAA-MM.") from None
    if not 2000 <= d.year <= 2100:
        raise HTTPException(status_code=400, detail="Mês fora do intervalo.")
    return d


def _data(d: Optional[date]) -> date:
    d = d or agora().date()
    if not 2000 <= d.year <= 2100:
        raise HTTPException(status_code=400, detail="Data fora do intervalo.")
    return d


def _pode_salarios(sessao) -> bool:
    return "rh.salarios" in PERMISSOES.get(sessao["perfil"], set())


def _soma_mes(m: date, n: int) -> date:
    t = m.year * 12 + m.month - 1 + n
    return date(t // 12, t % 12 + 1, 1)


def _resumo_dia(conn, dia: date) -> dict:
    r = conn.execute("SELECT COUNT(*) FILTER (WHERE situacao <> 'cancelado') AS pedidos, COUNT(*) FILTER (WHERE situacao = 'cancelado') AS cancelados, "
                     "COALESCE(sum(total) FILTER (WHERE situacao <> 'cancelado'), 0) AS vendas FROM pedido WHERE loja_id = %s AND data = %s", (LOJA_ID, dia)).fetchone()
    return {"pedidos": r["pedidos"], "cancelados": r["cancelados"], "vendas": r["vendas"], "ticket_medio": (r["vendas"] / r["pedidos"]).quantize(Q2) if r["pedidos"] else None}


def _alertas(conn, sessao) -> list[dict]:
    par = vigentes(conn, LOJA_ID)
    on = lambda k: par[k]["valor"] != "nao"  # noqa: E731
    hoje = agora().date()
    saida = []
    meta = par["cmv_meta_pct"]["valor"]
    if on("bi_alerta_cmv") and meta is not None:
        c = custos_svc.cmv_mes(conn, LOJA_ID, hoje.replace(day=1))
        if c["vendas"] > 0:
            pct = (c["cmv_real"] / c["vendas"] * 100).quantize(Q2)
            if pct > Decimal(meta):
                saida.append({"tipo": "cmv", "gravidade": "alta", "texto": f"CMV do mês em {fmt(pct)}%, acima da meta de {fmt(Decimal(meta))}%."})
    if on("bi_alerta_estoque"):
        a = estoque_r.alertas(sessao, conn)
        if a["repor"]:
            saida.append({"tipo": "estoque", "gravidade": "media", "texto": f"{len(a['repor'])} item(ns) abaixo do mínimo."})
        venc = [v for v in a["validade"] if v["vencido"]]
        if venc:
            saida.append({"tipo": "validade", "gravidade": "alta", "texto": f"{len(venc)} lote(s) vencido(s) com saldo."})
    if on("bi_alerta_caixa"):
        n = conn.execute("SELECT COUNT(*) AS n FROM contagem_caixa c JOIN caixa_dia d ON d.id = c.caixa_id WHERE d.loja_id = %s AND d.data >= %s AND c.diferenca <> 0",
                         (LOJA_ID, hoje - timedelta(days=7))).fetchone()["n"]
        if n:
            saida.append({"tipo": "caixa", "gravidade": "media", "texto": f"{n} contagem(ns) de caixa com diferença nos últimos 7 dias."})
    if on("bi_alerta_atraso"):
        n = conn.execute("SELECT COUNT(*) AS n FROM pedido WHERE loja_id = %s AND data = %s AND situacao IN ('recebido','em producao') AND entrega_calculada < %s", (LOJA_ID, hoje, agora())).fetchone()["n"]
        if n:
            saida.append({"tipo": "atraso", "gravidade": "alta", "texto": f"{n} pedido(s) passaram do horário de entrega calculado."})
    if on("bi_alerta_manutencao"):
        a = imob_r.alertas(sessao, conn)
        if a["bens_criticos_parados"]:
            saida.append({"tipo": "manutencao", "gravidade": "alta", "texto": f"{len(a['bens_criticos_parados'])} bem(ns) crítico(s) parado(s)."})
    if "contas.ver" in PERMISSOES.get(sessao["perfil"], set()) and _pode_salarios(sessao):
        f = contas_r.fluxo(30, sessao, conn)
        if Decimal(f["menor_saldo"]) < 0:
            saida.append({"tipo": "fluxo", "gravidade": "alta", "texto": f"O saldo previsto fica negativo em até 30 dias (menor: R$ {f['menor_saldo']})."})
    return saida


@router.get("/painel")
def painel(data: Optional[date] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    dia = _data(data)
    hoje, anterior = _resumo_dia(conn, dia), _resumo_dia(conn, dia - timedelta(days=7))
    ped = conn.execute("SELECT COALESCE(avg(extract(epoch FROM entrega_real - criado_em) / 60) FILTER (WHERE entrega_real IS NOT NULL), 0) AS minutos, "
                       "COUNT(*) FILTER (WHERE entrega_real IS NOT NULL AND entrega_calculada IS NOT NULL AND entrega_real > entrega_calculada) AS atrasados "
                       "FROM pedido WHERE loja_id = %s AND data = %s AND situacao <> 'cancelado'", (LOJA_ID, dia)).fetchone()
    perdas = conn.execute("SELECT COALESCE(sum(quantidade), 0) AS n FROM perda WHERE loja_id = %s AND (criado_em AT TIME ZONE 'America/Sao_Paulo')::date = %s", (LOJA_ID, dia)).fetchone()["n"]
    dif = conn.execute("SELECT COALESCE(sum(c.diferenca), 0) AS v FROM contagem_caixa c JOIN caixa_dia d ON d.id = c.caixa_id WHERE d.loja_id = %s AND d.data = %s", (LOJA_ID, dia)).fetchone()["v"]
    mes = dia.replace(day=1)
    cmv = custos_svc.cmv_mes(conn, LOJA_ID, mes)
    cmv_pct = (cmv["cmv_real"] / cmv["vendas"] * 100).quantize(Q2) if cmv["vendas"] > 0 else None
    saldo = None
    if "contas.ver" in PERMISSOES.get(sessao["perfil"], set()):
        saldo = contas_r.fluxo(1, sessao, conn)["saldo_atual"]
    var = ((hoje["vendas"] - anterior["vendas"]) / anterior["vendas"] * 100).quantize(Q2) if anterior["vendas"] > 0 else None
    return {"data": dia, "vendas": fmt(hoje["vendas"]), "vendas_semana_anterior": fmt(anterior["vendas"]), "variacao_pct": fmt(var), "pedidos": hoje["pedidos"],
            "cancelados": hoje["cancelados"], "ticket_medio": fmt(hoje["ticket_medio"]), "tempo_medio_min": int(ped["minutos"]), "entregues_com_atraso": ped["atrasados"],
            "perdas": int(perdas), "diferenca_caixa": fmt(dif), "cmv_mes": fmt(cmv["cmv_real"]), "cmv_pct": fmt(cmv_pct), "saldo_contas": saldo,
            "destaques": ["vendas", "cmv_mes", "saldo_contas"], "alertas": _alertas(conn, sessao)}


@router.get("/alertas")
def alertas(sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    return _alertas(conn, sessao)


def _dre(conn, sessao, mes: date) -> dict:
    r = custos_svc.resultado_mes(conn, LOJA_ID, mes)
    ver = _pode_salarios(sessao)
    fx = r["fixos_detalhe"]
    ebitda_base = r["margem_contribuicao"] - (r["custos_fixos"] - fx["depreciacao"])
    out = {"mes": mes, "receita_bruta": r["receita_bruta"], "descontos": r["descontos"], "receita": r["receita"], "cmv": r["cmv"], "taxas_cartao": r["taxas_cartao"], "taxas_canal": r["taxas_canal"],
           "entregas": r["entregas"], "outras_variaveis": r["outras_variaveis"], "margem_contribuicao": r["margem_contribuicao"], "fixas": fx["fixas"], "outras_fixas": fx["outras"],
           "depreciacao": fx["depreciacao"], "tributos": r["tributos"], "pessoal": fx["pessoal"] if ver else None,
           "ebitda": ebitda_base if ver else None, "resultado_operacional": r["resultado_operacional"] if ver else None,
           "ponto_equilibrio": r["ponto_equilibrio"] if ver else None, "cmv_fechado": r["cmv_fechado"]}
    return {k: (fmt(v) if isinstance(v, Decimal) else v) for k, v in out.items()}


@router.get("/dre")
def dre(mes: Optional[str] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    """DRE gerencial por competência. Sem rh.salarios, as linhas que revelam a folha (pessoal, EBITDA, resultado) saem em branco."""
    return _dre(conn, sessao, _mes(mes))


@router.get("/dre/serie")
def dre_serie(meses: int = 13, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    if not 1 <= meses <= 36:
        raise HTTPException(status_code=400, detail="Informe de 1 a 36 meses.")
    atual = agora().date().replace(day=1)
    return [_dre(conn, sessao, _soma_mes(atual, -i)) for i in range(meses - 1, -1, -1)]


@router.get("/dre.csv")
def dre_csv(mes: Optional[str] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    d = _dre(conn, sessao, _mes(mes))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["linha", "valor"])
    for k, v in d.items():
        if k not in ("mes", "cmv_fechado") and v is not None:
            w.writerow([k, str(v).replace(".", ",")])
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=dre_{d['mes']}.csv"})


@router.get("/lucratividade")
def lucratividade(mes: Optional[str] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    """Receita, custo da ficha e margem por sabor, categoria, canal e dia da semana. Custo só onde há ficha e custo médio."""
    m = _mes(mes)
    prox = custos_svc.limites_mes(m)[0]
    linhas = conn.execute(
        "SELECT i.tipo, i.tamanho, i.produto_id, i.sabor2_id, p.nome, COALESCE(c.nome, i.tipo) AS categoria, d.canal, extract(isodow FROM d.data)::int AS dia, "
        "sum(i.preco_unit * i.quantidade) AS receita, sum(i.quantidade) AS qtd FROM item_pedido i JOIN pedido d ON d.id = i.pedido_id JOIN produto p ON p.id = i.produto_id "
        "LEFT JOIN categoria_pizza c ON c.id = p.categoria_id WHERE d.loja_id = %s AND d.situacao <> 'cancelado' AND d.data >= %s AND d.data < %s "
        "GROUP BY i.tipo, i.tamanho, i.produto_id, i.sabor2_id, p.nome, c.nome, d.canal, 8", (LOJA_ID, m, prox)).fetchall()
    cache, sabor, cat, canal, dia = {}, {}, {}, {}, {}

    def acumula(mapa, chave, receita, custo, qtd):
        e = mapa.setdefault(chave, {"receita": ZERO, "custo": ZERO, "quantidade": 0})
        e["receita"] += receita
        e["custo"] += custo
        e["quantidade"] += qtd

    for r in linhas:
        k = (r["tipo"], r["tamanho"], r["produto_id"], r["sabor2_id"])
        if k not in cache:
            cache[k] = custos_svc.custo_unidade(conn, LOJA_ID, *k)["total"]
        custo = cache[k] * r["qtd"]
        acumula(sabor, r["nome"], r["receita"], custo, r["qtd"])
        acumula(cat, r["categoria"], r["receita"], custo, r["qtd"])
        acumula(canal, r["canal"], r["receita"], custo, r["qtd"])
        acumula(dia, DIAS[r["dia"] - 1], r["receita"], custo, r["qtd"])

    def saida(mapa):
        lst = [{"nome": k, "quantidade": v["quantidade"], "receita": fmt(v["receita"]), "custo": fmt(v["custo"]), "margem": fmt(v["receita"] - v["custo"]),
                "margem_pct": fmt(((v["receita"] - v["custo"]) / v["receita"] * 100).quantize(Q2)) if v["receita"] > 0 else None} for k, v in mapa.items()]
        return sorted(lst, key=lambda x: -Decimal(x["receita"]))
    return {"mes": m, "por_sabor": saida(sabor), "por_categoria": saida(cat), "por_canal": saida(canal), "por_dia_semana": saida(dia)}


@router.get("/producao")
def producao(mes: Optional[str] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    m = _mes(mes)
    prox, ini, fim = custos_svc.limites_mes(m)
    etapas = conn.execute(
        "WITH e AS (SELECT pizza_id, situacao, criado_em, lead(criado_em) OVER (PARTITION BY pizza_id ORDER BY id) AS depois FROM evento_producao WHERE criado_em >= %s AND criado_em < %s) "
        "SELECT situacao, COUNT(*) AS n, avg(extract(epoch FROM depois - criado_em) / 60) AS minutos FROM e WHERE depois IS NOT NULL GROUP BY situacao ORDER BY situacao", (ini, fim)).fetchall()
    retro = conn.execute("SELECT m.nome, COUNT(*) AS n FROM retrocesso r JOIN motivo_retrocesso m ON m.id = r.motivo_id WHERE r.criado_em >= %s AND r.criado_em < %s GROUP BY m.nome ORDER BY n DESC", (ini, fim)).fetchall()
    perdas = conn.execute("SELECT m.nome, sum(p.quantidade) AS n FROM perda p JOIN motivo_perda m ON m.id = p.motivo_id WHERE p.loja_id = %s AND p.criado_em >= %s AND p.criado_em < %s GROUP BY m.nome ORDER BY n DESC", (LOJA_ID, ini, fim)).fetchall()
    tot = conn.execute("SELECT COUNT(*) FILTER (WHERE situacao = 'acabada') AS feitas, COUNT(*) FILTER (WHERE original_id IS NOT NULL) AS refacoes FROM pizza_producao WHERE loja_id = %s AND criado_em >= %s AND criado_em < %s", (LOJA_ID, ini, fim)).fetchone()
    return {"mes": m, "pizzas_acabadas": tot["feitas"], "refacoes": tot["refacoes"],
            "tempo_por_etapa": [{"etapa": e["situacao"], "ocorrencias": e["n"], "minutos_medios": round(float(e["minutos"] or 0), 1)} for e in etapas],
            "retrocessos_por_motivo": [{"motivo": r["nome"], "quantidade": r["n"]} for r in retro], "perdas_por_motivo": [{"motivo": r["nome"], "quantidade": int(r["n"])} for r in perdas]}


@router.get("/vendas-por-forma.csv")
def vendas_por_forma_csv(mes: Optional[str] = None, sessao=Depends(requer("bi.ver")), conn=Depends(get_db)):
    m = _mes(mes)
    prox = custos_svc.limites_mes(m)[0]
    rs = conn.execute("SELECT p.forma, sum(p.valor - p.troco) AS v FROM pagamento p JOIN pedido d ON d.id = p.pedido_id WHERE d.loja_id = %s AND d.situacao <> 'cancelado' AND d.data >= %s AND d.data < %s GROUP BY p.forma ORDER BY p.forma",
                      (LOJA_ID, m, prox)).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["forma", "valor"])
    for r in rs:
        w.writerow([r["forma"], fmt(r["v"]).replace(".", ",")])
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=vendas_por_forma_{m}.csv"})
