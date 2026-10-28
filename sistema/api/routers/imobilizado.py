"""Imobilizado: bens, depreciação, baixa, conferência, plano de manutenção, leituras e ordens de serviço."""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (AtivoIn, BaixaBemIn, BemIn, BemUpdate, CategoriaBemIn, ConferenciaBemIn, LeituraIn, LimiteLeituraIn, OsFecharIn, OsIn, OsIniciarIn, OsPecaIn, PlanoIn)
from api.security import requer
from api.services import contas as contas_svc
from api.services import estoque as est
from api.services import imobilizado as svc
from api.services.dinheiro import fmt, parse_reais
from api.services.parametros import vigentes

router = APIRouter(prefix="/imobilizado", tags=["imobilizado"])
ZERO = Decimal("0.00")
CATEGORIAS_PADRAO = [("Máquinas e equipamentos", "10", False), ("Móveis e utensílios", "20", False), ("Veículos", "25", True), ("Equipamentos de informática", "20", False), ("Instalações", "10", False)]
CAMPOS_DEPRECIACAO = ("inicio_uso", "metodo", "vida_util_meses", "valor_residual")


def _ex(conn, e):
    conn.rollback()
    raise traduzir_erro(e) from e


# ---------------------------------------------------------------- categorias
@router.get("/categorias")
def categorias(sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    return [c | {"taxa_fiscal_pct": fmt(c["taxa_fiscal_pct"])} for c in conn.execute("SELECT id, nome, taxa_fiscal_pct, veiculo, ativo FROM categoria_bem WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()]


@router.post("/categorias", status_code=201)
def criar_categoria(d: CategoriaBemIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO categoria_bem (loja_id, nome, taxa_fiscal_pct, veiculo) VALUES (%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.nome, d.taxa_fiscal_pct, d.veiculo)).fetchone()
        auditar(conn, sessao, "criar", "categoria_bem", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.post("/categorias/iniciar-padrao", status_code=201)
def categorias_padrao(sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    """Taxas fiscais de referência (IN RFB 1.700/2017, Anexo III): conferir com o contador."""
    if conn.execute("SELECT 1 FROM categoria_bem WHERE loja_id = %s LIMIT 1", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=409, detail="As categorias já foram criadas.")
    for n, t, v in CATEGORIAS_PADRAO:
        conn.execute("INSERT INTO categoria_bem (loja_id, nome, taxa_fiscal_pct, veiculo) VALUES (%s,%s,%s,%s)", (LOJA_ID, n, t, v))
    auditar(conn, sessao, "iniciar-padrao", "categoria_bem", None, depois={"quantidade": len(CATEGORIAS_PADRAO)})
    conn.commit()
    return {"criadas": len(CATEGORIAS_PADRAO)}


@router.patch("/categorias/{cid}")
def ativar_categoria(cid: int, d: AtivoIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    if not conn.execute("UPDATE categoria_bem SET ativo = %s WHERE id = %s AND loja_id = %s RETURNING id", (d.ativo, cid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    auditar(conn, sessao, "ativar" if d.ativo else "inativar", "categoria_bem", cid)
    conn.commit()
    return {"id": cid, "ativo": d.ativo}


# ---------------------------------------------------------------- bens
def _bem_out(conn, b: dict, detalhe=False) -> dict:
    acumulada = conn.execute("SELECT COALESCE(sum(valor), 0) AS s FROM depreciacao_bem WHERE bem_id = %s", (b["id"],)).fetchone()["s"]
    out = {k: b[k] for k in ("id", "codigo", "nome", "categoria", "data_aquisicao", "inicio_uso", "fornecedor", "numero_nota", "local_texto", "responsavel", "numero_serie", "placa", "quilometragem",
                              "critico", "metodo", "vida_util_meses", "garantia_ate", "seguro_ate", "apolice", "situacao", "veiculo")}
    out |= {"valor_aquisicao": fmt(b["valor_aquisicao"]), "valor_residual": fmt(b["valor_residual"]), "depreciacao_acumulada": fmt(acumulada), "valor_contabil": fmt(Decimal(b["valor_aquisicao"]) - acumulada),
            "taxa_fiscal_pct": fmt(b["taxa_fiscal_pct"]), "vida_meses": svc.vida_meses(b, b["taxa_fiscal_pct"])}
    if detalhe:
        out["baixa"] = conn.execute("SELECT tipo, data, valor, motivo FROM baixa_bem WHERE bem_id = %s", (b["id"],)).fetchone()
        if out["baixa"]:
            out["baixa"]["valor"] = fmt(out["baixa"]["valor"])
    return out


_SQL_BEM = ("SELECT b.*, c.nome AS categoria, c.taxa_fiscal_pct, c.veiculo, f.nome AS fornecedor FROM bem b JOIN categoria_bem c ON c.id = b.categoria_id "
            "LEFT JOIN fornecedor f ON f.id = b.fornecedor_id WHERE b.loja_id = %s")


@router.get("/bens")
def bens(situacao: Optional[str] = None, sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    try:
        svc.gerar_depreciacao(conn, LOJA_ID)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    sql, p = _SQL_BEM, [LOJA_ID]
    if situacao in ("ativo", "baixado"):
        sql, p = sql + " AND b.situacao = %s", p + [situacao]
    return [_bem_out(conn, b) for b in conn.execute(sql + " ORDER BY b.nome", p).fetchall()]


@router.get("/bens/{bid}")
def bem(bid: int, sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    svc.gerar_depreciacao(conn, LOJA_ID)
    conn.commit()
    b = conn.execute(_SQL_BEM + " AND b.id = %s", (LOJA_ID, bid)).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="Bem não encontrado.")
    out = _bem_out(conn, b, True)
    out["planos"] = _planos(conn, bid)
    out["limites"] = [l | {"minimo": est.txt(l["minimo"]), "maximo": est.txt(l["maximo"])} for l in conn.execute("SELECT grandeza, unidade, minimo, maximo FROM limite_leitura WHERE bem_id = %s ORDER BY grandeza", (bid,)).fetchall()]
    out["leituras"] = [l | {"valor": est.txt(l["valor"])} for l in conn.execute("SELECT grandeza, valor, data, fora_do_normal FROM leitura_bem WHERE bem_id = %s ORDER BY id DESC LIMIT 20", (bid,)).fetchall()]
    out["ordens"] = [o | {"custo_total": fmt(o["custo_total"])} for o in conn.execute("SELECT id, numero, tipo, situacao, descricao, custo_total FROM ordem_servico WHERE bem_id = %s ORDER BY id DESC LIMIT 20", (bid,)).fetchall()]
    return out


@router.post("/bens", status_code=201)
def criar_bem(d: BemIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    valor, residual = parse_reais(d.valor_aquisicao), parse_reais(d.valor_residual)
    minimo = vigentes(conn, LOJA_ID)["bem_valor_minimo"]["valor"]
    if minimo is not None and valor < Decimal(minimo):
        raise HTTPException(status_code=400, detail=f"Abaixo de R$ {fmt(Decimal(minimo))} não é bem do imobilizado: cadastre como material de uso e consumo em Estoques.")
    if residual >= valor:
        raise HTTPException(status_code=400, detail="O valor residual precisa ser menor que o valor do bem.")
    if d.metodo == "vida_util" and not d.vida_util_meses:
        raise HTTPException(status_code=400, detail="Informe a vida útil em meses.")
    if not conn.execute("SELECT 1 FROM categoria_bem WHERE id = %s AND loja_id = %s AND ativo", (d.categoria_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    if d.fornecedor_id and not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s", (d.fornecedor_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    if d.inicio_uso and d.inicio_uso < d.data_aquisicao:
        raise HTTPException(status_code=400, detail="O início de uso não pode ser antes da compra.")
    try:
        r = conn.execute("INSERT INTO bem (loja_id, codigo, nome, categoria_id, valor_aquisicao, data_aquisicao, inicio_uso, fornecedor_id, numero_nota, local_texto, responsavel, numero_serie, placa, quilometragem, "
                         "critico, metodo, vida_util_meses, valor_residual, garantia_ate, seguro_ate, apolice, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.codigo, d.nome, d.categoria_id, valor, d.data_aquisicao, d.inicio_uso, d.fornecedor_id, d.numero_nota, d.local_texto, d.responsavel, d.numero_serie, d.placa, d.quilometragem,
                          d.critico, d.metodo, d.vida_util_meses, residual, d.garantia_ate, d.seguro_ate, d.apolice, agora(), sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "criar", "bem", r["id"], depois={"codigo": d.codigo, "valor": fmt(valor)})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/bens/{bid}")
def alterar_bem(bid: int, d: BemUpdate, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    b = conn.execute("SELECT * FROM bem WHERE id = %s AND loja_id = %s FOR UPDATE", (bid, LOJA_ID)).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="Bem não encontrado.")
    if b["situacao"] == "baixado":
        raise HTTPException(status_code=409, detail="Bem baixado não muda.")
    if "valor_residual" in campos:
        campos["valor_residual"] = parse_reais(campos["valor_residual"])
        if campos["valor_residual"] >= b["valor_aquisicao"]:
            raise HTTPException(status_code=400, detail="O valor residual precisa ser menor que o valor do bem.")
    for c in CAMPOS_DEPRECIACAO:  # valor igual ao atual não é mudança
        if c in campos and campos[c] == b[c] if c != "valor_residual" else False:
            campos.pop(c)
    if not campos:
        return {"id": bid}
    if any(c in campos for c in CAMPOS_DEPRECIACAO) and conn.execute("SELECT 1 FROM depreciacao_bem WHERE bem_id = %s LIMIT 1", (bid,)).fetchone():
        raise HTTPException(status_code=409, detail="A depreciação deste bem já começou: início de uso, método, vida útil e valor residual não mudam mais.")
    if campos.get("inicio_uso") and campos["inicio_uso"] < b["data_aquisicao"]:
        raise HTTPException(status_code=400, detail="O início de uso não pode ser antes da compra.")
    if (campos.get("metodo") or b["metodo"]) == "vida_util" and not (campos.get("vida_util_meses") or b["vida_util_meses"]):
        raise HTTPException(status_code=400, detail="Informe a vida útil em meses.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    try:
        conn.execute(f"UPDATE bem SET {sets} WHERE id = %s", (*campos.values(), bid))
        auditar(conn, sessao, "alterar", "bem", bid, depois={k: str(v) for k, v in campos.items()})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": bid}


@router.post("/bens/{bid}/baixa", status_code=201)
def baixar_bem(bid: int, d: BaixaBemIn, sessao=Depends(requer("imobilizado.aprovar")), conn=Depends(get_db)):
    """A baixa é aprovada pelo administrador ou proprietário. O bem para de depreciar depois do mês da baixa."""
    b = conn.execute("SELECT * FROM bem WHERE id = %s AND loja_id = %s FOR UPDATE", (bid, LOJA_ID)).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="Bem não encontrado.")
    if b["situacao"] == "baixado":
        raise HTTPException(status_code=409, detail="Bem já baixado.")
    if d.data < b["data_aquisicao"] or d.data > agora().date():
        raise HTTPException(status_code=400, detail="Data da baixa fora do intervalo (da compra até hoje).")
    ult = conn.execute("SELECT max(competencia) AS m FROM depreciacao_bem WHERE bem_id = %s", (bid,)).fetchone()["m"]
    if ult and d.data.replace(day=1) < ult:
        raise HTTPException(status_code=409, detail="A data da baixa não pode ser anterior ao último mês já depreciado.")
    if conn.execute("SELECT 1 FROM ordem_servico WHERE bem_id = %s AND situacao IN ('aberta','em_execucao') LIMIT 1", (bid,)).fetchone():
        raise HTTPException(status_code=409, detail="Feche ou cancele as ordens de serviço do bem antes da baixa.")
    try:
        conn.execute("INSERT INTO baixa_bem (bem_id, tipo, data, valor, motivo, aprovado_por, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s)", (bid, d.tipo, d.data, parse_reais(d.valor), d.motivo, sessao["usuario_id"], agora()))
        conn.execute("UPDATE bem SET situacao = 'baixado' WHERE id = %s", (bid,))
        auditar(conn, sessao, "baixar", "bem", bid, depois={"tipo": d.tipo, "valor": d.valor, "motivo": d.motivo})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": bid, "situacao": "baixado"}


@router.post("/bens/{bid}/conferencias", status_code=201)
def conferir(bid: int, d: ConferenciaBemIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM bem WHERE id = %s AND loja_id = %s AND situacao = 'ativo'", (bid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Bem não encontrado ou baixado.")
    try:
        r = conn.execute("INSERT INTO conferencia_bem (bem_id, data, encontrado, local_encontrado, observacao, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (bid, agora().date(), d.encontrado, d.local_encontrado, d.observacao, sessao["usuario_id"], agora())).fetchone()
        if d.encontrado and d.local_encontrado:
            conn.execute("UPDATE bem SET local_texto = %s WHERE id = %s", (d.local_encontrado, bid))
        auditar(conn, sessao, "conferir", "bem", bid, depois={"encontrado": d.encontrado})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.get("/inventario")
def inventario(sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    """Inventário anual: cada bem ativo com a última conferência. Pendente quando nunca conferido há mais de 365 dias da compra, ou sem conferência no último ano."""
    hoje = agora().date()
    saida = []
    for b in conn.execute("SELECT b.id, b.codigo, b.nome, b.local_texto, b.data_aquisicao, (SELECT max(data) FROM conferencia_bem c WHERE c.bem_id = b.id) AS ultima, "
                          "(SELECT encontrado FROM conferencia_bem c WHERE c.bem_id = b.id ORDER BY id DESC LIMIT 1) AS encontrado FROM bem b WHERE b.loja_id = %s AND b.situacao = 'ativo' ORDER BY b.nome", (LOJA_ID,)).fetchall():
        ref = b["ultima"] or b["data_aquisicao"]
        saida.append(b | {"pendente": (hoje - ref).days > 365 or b["encontrado"] is False})
    return saida


# ---------------------------------------------------------------- plano, leituras
def _planos(conn, bid=None):
    sql = ("SELECT p.id, p.bem_id, b.nome AS bem, p.tarefa, p.periodicidade_dias, p.antecedencia_dias, p.ultima_em, p.base_em, p.ativo FROM plano_manutencao p JOIN bem b ON b.id = p.bem_id WHERE b.loja_id = %s AND b.situacao = 'ativo'")
    p = [LOJA_ID]
    if bid:
        sql, p = sql + " AND p.bem_id = %s", p + [bid]
    hoje = agora().date()
    out = []
    for x in conn.execute(sql + " ORDER BY p.id", p).fetchall():
        v = svc.proximo_vencimento(x)
        x["proximo"] = v
        x["situacao"] = "vencido" if v < hoje else "a vencer" if v - timedelta(days=x["antecedencia_dias"]) <= hoje else "em dia"
        out.append(x)
    return out


@router.post("/bens/{bid}/planos", status_code=201)
def criar_plano(bid: int, d: PlanoIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM bem WHERE id = %s AND loja_id = %s AND situacao = 'ativo'", (bid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Bem não encontrado ou baixado.")
    try:
        r = conn.execute("INSERT INTO plano_manutencao (bem_id, tarefa, periodicidade_dias, antecedencia_dias, base_em, criado_em) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                         (bid, d.tarefa, d.periodicidade_dias, d.antecedencia_dias, d.base_em or agora().date(), agora())).fetchone()
        auditar(conn, sessao, "criar", "plano_manutencao", r["id"], depois={"bem_id": bid, "tarefa": d.tarefa})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.get("/planos")
def planos(sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    return _planos(conn)


@router.patch("/planos/{pid}")
def ativar_plano(pid: int, d: AtivoIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    if not conn.execute("UPDATE plano_manutencao SET ativo = %s WHERE id = %s AND bem_id IN (SELECT id FROM bem WHERE loja_id = %s) RETURNING id", (d.ativo, pid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    auditar(conn, sessao, "ativar" if d.ativo else "inativar", "plano_manutencao", pid)
    conn.commit()
    return {"id": pid, "ativo": d.ativo}


@router.put("/bens/{bid}/limites")
def definir_limite(bid: int, d: LimiteLeituraIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    if d.minimo is None and d.maximo is None:
        raise HTTPException(status_code=400, detail="Informe o mínimo, o máximo ou os dois.")
    if d.minimo is not None and d.maximo is not None and Decimal(d.minimo) > Decimal(d.maximo):
        raise HTTPException(status_code=400, detail="O mínimo não pode passar do máximo.")
    if not conn.execute("SELECT 1 FROM bem WHERE id = %s AND loja_id = %s AND situacao = 'ativo'", (bid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Bem não encontrado ou baixado.")
    try:
        conn.execute("INSERT INTO limite_leitura (bem_id, grandeza, unidade, minimo, maximo) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (bem_id, grandeza) DO UPDATE SET unidade = EXCLUDED.unidade, minimo = EXCLUDED.minimo, maximo = EXCLUDED.maximo",
                     (bid, d.grandeza, d.unidade, d.minimo, d.maximo))
        auditar(conn, sessao, "limite", "bem", bid, depois={"grandeza": d.grandeza, "minimo": d.minimo, "maximo": d.maximo})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"bem_id": bid, "grandeza": d.grandeza}


@router.post("/bens/{bid}/leituras", status_code=201)
def leitura(bid: int, d: LeituraIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    """Leitura digitada na inspeção. Fora do limite cadastrado aparece nos alertas."""
    if not conn.execute("SELECT 1 FROM bem WHERE id = %s AND loja_id = %s AND situacao = 'ativo'", (bid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Bem não encontrado ou baixado.")
    v = Decimal(d.valor)
    lim = conn.execute("SELECT minimo, maximo FROM limite_leitura WHERE bem_id = %s AND grandeza = %s", (bid, d.grandeza)).fetchone()
    fora = bool(lim and ((lim["minimo"] is not None and v < lim["minimo"]) or (lim["maximo"] is not None and v > lim["maximo"])))
    data = d.data or agora().date()
    if data > agora().date():
        raise HTTPException(status_code=400, detail="A leitura não pode ter data futura.")
    try:
        r = conn.execute("INSERT INTO leitura_bem (bem_id, grandeza, valor, data, fora_do_normal, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (bid, d.grandeza, v, data, fora, sessao["usuario_id"], agora())).fetchone()
        auditar(conn, sessao, "leitura", "bem", bid, depois={"grandeza": d.grandeza, "valor": d.valor, "fora": fora})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"], "fora_do_normal": fora}


# ---------------------------------------------------------------- alertas
@router.get("/alertas")
def alertas(sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    hoje = agora().date()
    prazo = hoje + timedelta(days=30)
    pl = [p for p in _planos(conn) if p["ativo"] and p["situacao"] != "em dia"]
    venc = [b | {"o_que": o} for o, col in (("garantia", "garantia_ate"), ("seguro", "seguro_ate")) for b in conn.execute(
        f"SELECT id, nome, {col} AS data FROM bem WHERE loja_id = %s AND situacao = 'ativo' AND {col} IS NOT NULL AND {col} <= %s ORDER BY {col}", (LOJA_ID, prazo)).fetchall()]
    fora = conn.execute("SELECT DISTINCT ON (l.bem_id, l.grandeza) b.id AS bem_id, b.nome AS bem, l.grandeza, l.valor, l.data, l.fora_do_normal FROM leitura_bem l JOIN bem b ON b.id = l.bem_id "
                        "WHERE b.loja_id = %s AND b.situacao = 'ativo' ORDER BY l.bem_id, l.grandeza, l.id DESC", (LOJA_ID,)).fetchall()
    parados = conn.execute("SELECT o.id AS os_id, o.numero, b.nome AS bem, o.parada_inicio FROM ordem_servico o JOIN bem b ON b.id = o.bem_id WHERE o.loja_id = %s AND b.critico AND o.parada_inicio IS NOT NULL "
                           "AND o.parada_fim IS NULL AND o.situacao IN ('aberta','em_execucao')", (LOJA_ID,)).fetchall()
    aprov = conn.execute("SELECT id, numero, custo_total FROM ordem_servico WHERE loja_id = %s AND situacao = 'em_execucao' AND precisa_aprovacao AND aprovado_por IS NULL", (LOJA_ID,)).fetchall()
    return {"planos": pl, "garantias_e_seguros": [v | {"vencido": v["data"] < hoje} for v in venc],
            "leituras_fora": [f | {"valor": est.txt(f["valor"])} for f in fora if f["fora_do_normal"]], "bens_criticos_parados": parados,
            "ordens_aguardando_aprovacao": [a | {"custo_total": fmt(a["custo_total"])} for a in aprov], "inventario_pendente": sum(1 for i in inventario(sessao, conn) if i["pendente"])}


# ---------------------------------------------------------------- ordens de serviço
def _os_out(conn, o: dict) -> dict:
    pecas = conn.execute("SELECT p.id, i.nome AS item, p.quantidade, p.custo_unit FROM os_peca p JOIN item i ON i.id = p.item_id WHERE p.os_id = %s ORDER BY p.id", (o["id"],)).fetchall()
    parada = None
    if o["parada_inicio"]:
        fim = o["parada_fim"] or agora()
        parada = int((fim - o["parada_inicio"]).total_seconds() // 60)
    return {k: o[k] for k in ("id", "numero", "bem_id", "bem", "tipo", "situacao", "descricao", "causa", "servico_feito", "executor_tipo", "executor_nome", "fornecedor_id", "precisa_aprovacao", "aprovado_por", "aberta_em",
                              "fechada_em", "parada_inicio", "parada_fim")} | {"mao_obra": fmt(o["mao_obra"]), "custo_pecas": fmt(o["custo_pecas"]), "custo_total": fmt(o["custo_total"]), "parada_minutos": parada,
                                                                              "pecas": [p | {"quantidade": est.txt(p["quantidade"]), "custo_unit": est.txt(p["custo_unit"])} for p in pecas]}


_SQL_OS = "SELECT o.*, b.nome AS bem FROM ordem_servico o JOIN bem b ON b.id = o.bem_id WHERE o.loja_id = %s"


def _os(conn, oid, travar=False):
    o = conn.execute(_SQL_OS + " AND o.id = %s" + (" FOR UPDATE OF o" if travar else ""), (LOJA_ID, oid)).fetchone()
    if not o:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada.")
    return o


@router.get("/os")
def listar_os(situacao: Optional[str] = None, sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    sql, p = _SQL_OS, [LOJA_ID]
    if situacao in ("aberta", "em_execucao", "fechada", "cancelada"):
        sql, p = sql + " AND o.situacao = %s", p + [situacao]
    return [_os_out(conn, o) for o in conn.execute(sql + " ORDER BY o.id DESC LIMIT 200", p).fetchall()]


@router.get("/os/{oid}")
def ver_os(oid: int, sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    return _os_out(conn, _os(conn, oid))


@router.post("/os", status_code=201)
def abrir_os(d: OsIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    b = conn.execute("SELECT id, critico FROM bem WHERE id = %s AND loja_id = %s AND situacao = 'ativo' FOR UPDATE", (d.bem_id, LOJA_ID)).fetchone()
    if not b:
        raise HTTPException(status_code=404, detail="Bem não encontrado ou baixado.")
    if d.plano_id and not conn.execute("SELECT 1 FROM plano_manutencao WHERE id = %s AND bem_id = %s", (d.plano_id, d.bem_id)).fetchone():
        raise HTTPException(status_code=404, detail="Plano não encontrado neste bem.")
    quando = agora()
    try:
        r = conn.execute("INSERT INTO ordem_servico (loja_id, bem_id, tipo, plano_id, descricao, parada_inicio, aberta_em, aberta_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.bem_id, d.tipo, d.plano_id, d.descricao, quando if d.parou else None, quando, sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "abrir", "ordem_servico", r["id"], depois={"bem_id": d.bem_id, "tipo": d.tipo})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return _os_out(conn, _os(conn, r["id"]))


@router.post("/os/{oid}/iniciar")
def iniciar_os(oid: int, d: OsIniciarIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    o = _os(conn, oid, True)
    if o["situacao"] != "aberta":
        raise HTTPException(status_code=409, detail="A ordem já foi iniciada ou encerrada.")
    if d.executor_tipo == "terceiro" and not d.fornecedor_id and not d.executor_nome:
        raise HTTPException(status_code=400, detail="Informe o fornecedor ou o nome do terceiro.")
    if d.executor_tipo == "funcionario" and not d.executor_nome:
        raise HTTPException(status_code=400, detail="Informe o funcionário.")
    if d.fornecedor_id and not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s", (d.fornecedor_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    try:
        conn.execute("UPDATE ordem_servico SET situacao = 'em_execucao', executor_tipo = %s, executor_nome = %s, fornecedor_id = %s WHERE id = %s", (d.executor_tipo, d.executor_nome, d.fornecedor_id, oid))
        auditar(conn, sessao, "iniciar", "ordem_servico", oid)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return _os_out(conn, _os(conn, oid))


@router.post("/os/{oid}/pecas", status_code=201)
def peca(oid: int, d: OsPecaIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    """A peça sai do estoque (material de consumo) pelo custo médio e soma no custo da ordem."""
    o = _os(conn, oid, True)
    if o["situacao"] not in ("aberta", "em_execucao"):
        raise HTTPException(status_code=409, detail="A ordem está encerrada.")
    it = conn.execute("SELECT id, classe FROM item WHERE id = %s AND loja_id = %s AND ativo", (d.item_id, LOJA_ID)).fetchone()
    if not it or it["classe"] != "consumo":
        raise HTTPException(status_code=404, detail="Peça não encontrada: use um item da classe material de consumo.")
    quando, qtd = agora(), Decimal(d.quantidade)
    try:
        est.saida(conn, LOJA_ID, d.item_id, qtd, "consumo_interno", sessao["usuario_id"], quando, f"Manutenção, ordem {o['numero']}", ("ordem_servico", oid))
        custo = est.custo_atual(conn, d.item_id)
        conn.execute("INSERT INTO os_peca (os_id, item_id, quantidade, custo_unit, criado_em) VALUES (%s,%s,%s,%s,%s)", (oid, d.item_id, qtd, custo, quando))
        conn.execute("UPDATE ordem_servico SET custo_pecas = custo_pecas + %s WHERE id = %s", ((qtd * (custo or 0)).quantize(Decimal("0.01")), oid))
        auditar(conn, sessao, "peca", "ordem_servico", oid, depois={"item_id": d.item_id, "quantidade": d.quantidade})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    except HTTPException:
        conn.rollback()
        raise
    return _os_out(conn, _os(conn, oid))


@router.post("/os/{oid}/aprovar")
def aprovar_os(oid: int, sessao=Depends(requer("imobilizado.aprovar")), conn=Depends(get_db)):
    o = _os(conn, oid, True)
    if o["situacao"] != "em_execucao":
        raise HTTPException(status_code=409, detail="Só se aprova ordem em execução.")
    if o["aprovado_por"]:
        raise HTTPException(status_code=409, detail="A ordem já foi aprovada.")
    if o["aberta_por"] == sessao["usuario_id"]:
        raise HTTPException(status_code=403, detail="Quem abriu a ordem não pode aprová-la.")
    try:
        conn.execute("UPDATE ordem_servico SET aprovado_por = %s, aprovado_valor = custo_total WHERE id = %s", (sessao["usuario_id"], oid))
        auditar(conn, sessao, "aprovar", "ordem_servico", oid)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return _os_out(conn, _os(conn, oid))


@router.post("/os/{oid}/fechar")
def fechar_os(oid: int, d: OsFecharIn, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    o = _os(conn, oid, True)
    if o["situacao"] != "em_execucao":
        raise HTTPException(status_code=409, detail="Inicie a ordem antes de fechar.")
    mao = parse_reais(d.mao_obra)
    total = mao + o["custo_pecas"]
    lim = vigentes(conn, LOJA_ID)["manutencao_valor_aprovacao"]["valor"]
    precisa = lim is not None and total > Decimal(lim)
    if precisa and (not o["aprovado_por"] or total > Decimal(o["aprovado_valor"] or 0)):  # a aprovação vale só até o valor aprovado
        conn.execute("UPDATE ordem_servico SET precisa_aprovacao = true, aprovado_por = NULL, aprovado_valor = NULL, mao_obra = %s, custo_total = %s WHERE id = %s", (mao, total, oid))
        conn.commit()
        raise HTTPException(status_code=409, detail=f"O custo de R$ {fmt(total)} passa de R$ {fmt(Decimal(lim))}: o administrador ou proprietário precisa aprovar antes de fechar.")
    if d.tipo_despesa_id and not conn.execute("SELECT 1 FROM tipo_despesa WHERE id = %s AND loja_id = %s AND ativo", (d.tipo_despesa_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Tipo de despesa não encontrado.")
    if mao > 0 and o["executor_tipo"] == "terceiro" and not d.tipo_despesa_id and not conn.execute("SELECT 1 FROM tipo_despesa WHERE loja_id = %s AND lower(nome) = 'manutenção' AND ativo", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=400, detail="Informe o tipo de despesa da mão de obra (ou cadastre o tipo 'Manutenção').")
    quando = agora()
    try:
        conn.execute("UPDATE ordem_servico SET situacao = 'fechada', servico_feito = %s, causa = %s, mao_obra = %s, custo_total = %s, precisa_aprovacao = %s, parada_fim = CASE WHEN parada_inicio IS NOT NULL THEN %s END, "
                     "fechada_em = %s, fechada_por = %s WHERE id = %s", (d.servico_feito, d.causa, mao, total, precisa, quando, quando, sessao["usuario_id"], oid))
        if o["plano_id"]:
            conn.execute("UPDATE plano_manutencao SET ultima_em = %s WHERE id = %s", (quando.date(), o["plano_id"]))
        if mao > 0:  # mão de obra é conta a pagar (terceiro) ou custo do funcionário, que já está na folha: só o terceiro gera título
            if o["executor_tipo"] == "terceiro":
                tipo = d.tipo_despesa_id or (conn.execute("SELECT id FROM tipo_despesa WHERE loja_id = %s AND lower(nome) = 'manutenção' AND ativo", (LOJA_ID,)).fetchone() or {}).get("id")
                contas_svc._novo(conn, loja_id=LOJA_ID, sentido="pagar", descricao=f"Manutenção, ordem {o['numero']} ({o['bem']})", fornecedor_id=o["fornecedor_id"], tipo_despesa_id=tipo, valor=mao,
                                 vencimento=d.vencimento or quando.date(), competencia=quando.date().replace(day=1), origem_tipo="manutencao", origem_id=oid, bem_id=o["bem_id"], criado_em=quando, criado_por=sessao["usuario_id"])
        auditar(conn, sessao, "fechar", "ordem_servico", oid, depois={"custo_total": fmt(total)})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return _os_out(conn, _os(conn, oid))


@router.post("/os/{oid}/cancelar")
def cancelar_os(oid: int, sessao=Depends(requer("imobilizado.operar")), conn=Depends(get_db)):
    o = _os(conn, oid, True)
    if o["situacao"] not in ("aberta", "em_execucao"):
        raise HTTPException(status_code=409, detail="A ordem já está encerrada.")
    if conn.execute("SELECT 1 FROM os_peca WHERE os_id = %s LIMIT 1", (oid,)).fetchone():
        raise HTTPException(status_code=409, detail="Já saíram peças do estoque: feche a ordem em vez de cancelar.")
    try:
        conn.execute("UPDATE ordem_servico SET situacao = 'cancelada', parada_fim = CASE WHEN parada_inicio IS NOT NULL THEN %s END WHERE id = %s", (agora(), oid))
        auditar(conn, sessao, "cancelar", "ordem_servico", oid)
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": oid, "situacao": "cancelada"}


@router.get("/custos-manutencao")
def custos_manutencao(mes: Optional[str] = None, sessao=Depends(requer("imobilizado.ver")), conn=Depends(get_db)):
    """Custo de manutenção e tempo parado por bem e por tipo, das ordens fechadas no mês."""
    hoje = agora().date()
    try:
        a, b = (mes or hoje.strftime("%Y-%m")).split("-")
        ini = hoje.replace(year=int(a), month=int(b), day=1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Mês no formato AAAA-MM.") from None
    prox = ini.replace(year=ini.year + (ini.month == 12), month=ini.month % 12 + 1)
    por_bem = conn.execute("SELECT b.id AS bem_id, b.nome AS bem, count(*) AS ordens, sum(o.custo_total) AS custo, COALESCE(sum(EXTRACT(EPOCH FROM (o.parada_fim - o.parada_inicio)) / 60), 0)::int AS parada_minutos "
                           "FROM ordem_servico o JOIN bem b ON b.id = o.bem_id WHERE o.loja_id = %s AND o.situacao = 'fechada' AND o.fechada_em::date >= %s AND o.fechada_em::date < %s GROUP BY b.id, b.nome ORDER BY custo DESC",
                           (LOJA_ID, ini, prox)).fetchall()
    por_tipo = conn.execute("SELECT tipo, count(*) AS ordens, sum(custo_total) AS custo FROM ordem_servico WHERE loja_id = %s AND situacao = 'fechada' AND fechada_em::date >= %s AND fechada_em::date < %s GROUP BY tipo ORDER BY tipo",
                            (LOJA_ID, ini, prox)).fetchall()
    return {"mes": ini.strftime("%Y-%m"), "por_bem": [x | {"custo": fmt(x["custo"])} for x in por_bem], "por_tipo": [x | {"custo": fmt(x["custo"])} for x in por_tipo]}
