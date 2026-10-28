"""RH gerencial: funcionários, contratos, escala, ponto, banco de horas, ausências, documentos e folha. Salário só para quem tem rh.salarios."""
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (AtivoIn, AusenciaIn, BancoHorasIn, BeneficioIn, ContratoIn, DesligarIn, DocumentoRhIn, EscalaTipoIn, FolhaLancarIn, FolhaResumoIn, FuncaoRhIn, FuncionarioIn,
                         FuncionarioUpdate, PontoIn, TurnoIn)
from api.security import PERMISSOES, requer
from api.services import contas as contas_svc
from api.services.dinheiro import fmt, parse_reais
from api.services.parametros import vigentes

router = APIRouter(prefix="/rh", tags=["rh"])
ZERO = Decimal("0.00")
FUNCOES_PADRAO = ["Massa", "Pizzaiolo", "Acabamento", "Atendimento", "Gerência", "Limpeza"]
ESCALAS_PADRAO = [("6x1", 6, 1, "44"), ("5x2", 5, 2, "40")]  # ponto de partida; a legislação pode mudar, por isso é cadastro
COM_ENCARGOS = ("clt", "intermitente")


def _ex(conn, e):
    conn.rollback()
    raise traduzir_erro(e) from e


def _pode_salarios(sessao) -> bool:
    return "rh.salarios" in PERMISSOES.get(sessao["perfil"], set())


def _mes(m: Optional[str]) -> date:
    hoje = agora().date()
    try:
        a, b = (m or hoje.strftime("%Y-%m")).split("-")
        d = date(int(a), int(b), 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Mês no formato AAAA-MM.") from None
    if not 2000 <= d.year <= 2100:
        raise HTTPException(status_code=400, detail="Mês fora do intervalo.")
    return d


def _func(conn, fid, ativo=False):
    f = conn.execute("SELECT * FROM funcionario WHERE id = %s AND loja_id = %s", (fid, LOJA_ID)).fetchone()
    if not f:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    if ativo and not f["ativo"]:
        raise HTTPException(status_code=409, detail="Funcionário desligado.")
    return f


# ---------------------------------------------------------------- cadastros base
@router.get("/funcoes")
def funcoes(sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    return conn.execute("SELECT id, nome, ativo FROM funcao_rh WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()


@router.post("/funcoes", status_code=201)
def criar_funcao(d: FuncaoRhIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO funcao_rh (loja_id, nome) VALUES (%s,%s) RETURNING id", (LOJA_ID, d.nome)).fetchone()
        auditar(conn, sessao, "criar", "funcao_rh", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.post("/iniciar-padrao", status_code=201)
def iniciar_padrao(sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    """Funções e tipos de escala de partida. Tudo é cadastro e pode mudar."""
    if conn.execute("SELECT 1 FROM funcao_rh WHERE loja_id = %s LIMIT 1", (LOJA_ID,)).fetchone() or conn.execute("SELECT 1 FROM escala_tipo WHERE loja_id = %s LIMIT 1", (LOJA_ID,)).fetchone():
        raise HTTPException(status_code=409, detail="Os cadastros iniciais já existem.")
    for n in FUNCOES_PADRAO:
        conn.execute("INSERT INTO funcao_rh (loja_id, nome) VALUES (%s,%s)", (LOJA_ID, n))
    for n, dt, df, hs in ESCALAS_PADRAO:
        conn.execute("INSERT INTO escala_tipo (loja_id, nome, dias_trabalho, dias_folga, horas_semana) VALUES (%s,%s,%s,%s,%s)", (LOJA_ID, n, dt, df, hs))
    auditar(conn, sessao, "iniciar-padrao", "funcao_rh", None)
    conn.commit()
    return {"funcoes": len(FUNCOES_PADRAO), "escalas": len(ESCALAS_PADRAO)}


@router.patch("/funcoes/{fid}")
def ativar_funcao(fid: int, d: AtivoIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    if not conn.execute("UPDATE funcao_rh SET ativo = %s WHERE id = %s AND loja_id = %s RETURNING id", (d.ativo, fid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Função não encontrada.")
    auditar(conn, sessao, "ativar" if d.ativo else "inativar", "funcao_rh", fid)
    conn.commit()
    return {"id": fid, "ativo": d.ativo}


@router.get("/escalas")
def escalas(sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    return [e | {"horas_semana": fmt(e["horas_semana"])} for e in conn.execute("SELECT id, nome, dias_trabalho, dias_folga, horas_semana, ativo FROM escala_tipo WHERE loja_id = %s ORDER BY nome", (LOJA_ID,)).fetchall()]


@router.post("/escalas", status_code=201)
def criar_escala(d: EscalaTipoIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    if d.dias_trabalho + d.dias_folga > 7:
        raise HTTPException(status_code=400, detail="Dias de trabalho mais folga passam de 7.")
    try:
        r = conn.execute("INSERT INTO escala_tipo (loja_id, nome, dias_trabalho, dias_folga, horas_semana) VALUES (%s,%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.nome, d.dias_trabalho, d.dias_folga, d.horas_semana)).fetchone()
        auditar(conn, sessao, "criar", "escala_tipo", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/escalas/{eid}")
def ativar_escala(eid: int, d: AtivoIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    if not conn.execute("UPDATE escala_tipo SET ativo = %s WHERE id = %s AND loja_id = %s RETURNING id", (d.ativo, eid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Escala não encontrada.")
    auditar(conn, sessao, "ativar" if d.ativo else "inativar", "escala_tipo", eid)
    conn.commit()
    return {"id": eid, "ativo": d.ativo}


# ---------------------------------------------------------------- funcionários
def _func_out(conn, f: dict, com_salario: bool) -> dict:
    c = conn.execute("SELECT c.tipo, c.forma_pagamento, c.valor, c.vigente_desde, e.nome AS escala FROM contrato c LEFT JOIN escala_tipo e ON e.id = c.escala_id WHERE c.funcionario_id = %s AND c.vigente_ate IS NULL", (f["id"],)).fetchone()
    out = {k: f[k] for k in ("id", "nome", "telefone", "funcao", "usuario_id", "admissao", "desligamento", "preco_especial", "ativo")}
    out["contrato"] = None if not c else {"tipo": c["tipo"], "forma_pagamento": c["forma_pagamento"], "escala": c["escala"], "vigente_desde": c["vigente_desde"], **({"valor": fmt(c["valor"])} if com_salario else {})}
    return out


@router.get("/funcionarios")
def funcionarios(ativo: Optional[bool] = None, sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    sql, p = "SELECT f.*, fr.nome AS funcao FROM funcionario f JOIN funcao_rh fr ON fr.id = f.funcao_id WHERE f.loja_id = %s", [LOJA_ID]
    if ativo is not None:
        sql, p = sql + " AND f.ativo = %s", p + [ativo]
    return [_func_out(conn, f, _pode_salarios(sessao)) for f in conn.execute(sql + " ORDER BY f.nome", p).fetchall()]


@router.post("/funcionarios", status_code=201)
def criar_funcionario(d: FuncionarioIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM funcao_rh WHERE id = %s AND loja_id = %s AND ativo", (d.funcao_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Função não encontrada.")
    if d.usuario_id and not conn.execute("SELECT 1 FROM usuario WHERE id = %s AND loja_id = %s AND ativo", (d.usuario_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou inativo.")
    try:
        r = conn.execute("INSERT INTO funcionario (loja_id, nome, telefone, funcao_id, usuario_id, admissao, preco_especial, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.nome, d.telefone, d.funcao_id, d.usuario_id, d.admissao, d.preco_especial, agora(), sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "criar", "funcionario", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.patch("/funcionarios/{fid}")
def alterar_funcionario(fid: int, d: FuncionarioUpdate, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    _func(conn, fid, ativo=True)
    if campos.get("funcao_id") and not conn.execute("SELECT 1 FROM funcao_rh WHERE id = %s AND loja_id = %s AND ativo", (campos["funcao_id"], LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Função não encontrada.")
    if campos.get("usuario_id") and not conn.execute("SELECT 1 FROM usuario WHERE id = %s AND loja_id = %s AND ativo", (campos["usuario_id"], LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou inativo.")
    try:
        conn.execute(f"UPDATE funcionario SET {', '.join(f'{c} = %s' for c in campos)} WHERE id = %s", (*campos.values(), fid))
        auditar(conn, sessao, "alterar", "funcionario", fid, depois={k: str(v) for k, v in campos.items()})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": fid}


@router.post("/funcionarios/{fid}/desligar")
def desligar(fid: int, d: DesligarIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    """Desligar bloqueia o login pessoal e encerra o contrato."""
    f = conn.execute("SELECT * FROM funcionario WHERE id = %s AND loja_id = %s FOR UPDATE", (fid, LOJA_ID)).fetchone()
    if not f:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    if not f["ativo"]:
        raise HTTPException(status_code=409, detail="Funcionário já desligado.")
    if d.data < f["admissao"]:
        raise HTTPException(status_code=400, detail="O desligamento não pode ser antes da admissão.")
    if f["usuario_id"] and conn.execute("SELECT 1 FROM usuario WHERE id = %s AND perfil IN ('administrador','proprietario')", (f["usuario_id"],)).fetchone():
        raise HTTPException(status_code=409, detail="Este funcionário é o administrador ou proprietário do sistema: o login dele não é bloqueado pelo desligamento. Desvincule o usuário antes.")
    try:
        conn.execute("UPDATE funcionario SET ativo = false, desligamento = %s, desligamento_motivo = %s WHERE id = %s", (d.data, d.motivo, fid))
        conn.execute("UPDATE contrato SET vigente_ate = GREATEST(%s, vigente_desde) WHERE funcionario_id = %s AND vigente_ate IS NULL", (d.data, fid))
        if f["usuario_id"]:
            conn.execute("UPDATE usuario SET ativo = false WHERE id = %s", (f["usuario_id"],))
        auditar(conn, sessao, "desligar", "funcionario", fid, depois={"data": str(d.data), "motivo": d.motivo, "login_bloqueado": bool(f["usuario_id"])})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": fid, "ativo": False}


# ---------------------------------------------------------------- contrato e benefícios (salário só com rh.salarios)
@router.get("/funcionarios/{fid}/contratos")
def contratos(fid: int, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    _func(conn, fid)
    return [c | {"valor": fmt(c["valor"])} for c in conn.execute("SELECT c.id, c.tipo, c.forma_pagamento, c.valor, c.vigente_desde, c.vigente_ate, e.nome AS escala FROM contrato c LEFT JOIN escala_tipo e ON e.id = c.escala_id "
                                                                 "WHERE c.funcionario_id = %s ORDER BY c.vigente_desde DESC, c.id DESC", (fid,)).fetchall()]


@router.post("/funcionarios/{fid}/contratos", status_code=201)
def novo_contrato(fid: int, d: ContratoIn, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    """Contrato novo encerra o vigente na véspera do início."""
    f = _func(conn, fid, ativo=True)
    if d.vigente_desde < f["admissao"]:
        raise HTTPException(status_code=400, detail="O contrato não pode começar antes da admissão.")
    if d.escala_id and not conn.execute("SELECT 1 FROM escala_tipo WHERE id = %s AND loja_id = %s AND ativo", (d.escala_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Escala não encontrada.")
    vig = conn.execute("SELECT id, vigente_desde FROM contrato WHERE funcionario_id = %s AND vigente_ate IS NULL FOR UPDATE", (fid,)).fetchone()
    if vig and d.vigente_desde <= vig["vigente_desde"]:
        raise HTTPException(status_code=400, detail="O novo contrato precisa começar depois do contrato vigente.")
    try:
        if vig:
            conn.execute("UPDATE contrato SET vigente_ate = %s WHERE id = %s", (d.vigente_desde - timedelta(days=1), vig["id"]))
        r = conn.execute("INSERT INTO contrato (funcionario_id, tipo, escala_id, forma_pagamento, valor, vigente_desde, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (fid, d.tipo, d.escala_id, d.forma_pagamento, parse_reais(d.valor), d.vigente_desde, agora(), sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "contrato", "funcionario", fid, depois={"tipo": d.tipo, "forma": d.forma_pagamento, "valor": d.valor})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"id": r["id"]}


@router.get("/funcionarios/{fid}/beneficios")
def beneficios(fid: int, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    _func(conn, fid)
    return [b | {"valor_mensal": fmt(b["valor_mensal"])} for b in conn.execute("SELECT id, nome, valor_mensal, ativo FROM beneficio_funcionario WHERE funcionario_id = %s ORDER BY id", (fid,)).fetchall()]


@router.post("/funcionarios/{fid}/beneficios", status_code=201)
def criar_beneficio(fid: int, d: BeneficioIn, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    _func(conn, fid, ativo=True)
    r = conn.execute("INSERT INTO beneficio_funcionario (funcionario_id, nome, valor_mensal) VALUES (%s,%s,%s) RETURNING id", (fid, d.nome, parse_reais(d.valor_mensal))).fetchone()
    auditar(conn, sessao, "beneficio", "funcionario", fid, depois={"nome": d.nome, "valor": d.valor_mensal})
    conn.commit()
    return {"id": r["id"]}


@router.patch("/beneficios/{bid}")
def ativar_beneficio(bid: int, d: AtivoIn, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    if not conn.execute("UPDATE beneficio_funcionario SET ativo = %s WHERE id = %s AND funcionario_id IN (SELECT id FROM funcionario WHERE loja_id = %s) RETURNING id", (d.ativo, bid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Benefício não encontrado.")
    auditar(conn, sessao, "ativar" if d.ativo else "inativar", "beneficio_funcionario", bid)
    conn.commit()
    return {"id": bid, "ativo": d.ativo}


# ---------------------------------------------------------------- escala (turnos)
@router.get("/turnos")
def turnos(de: date, ate: date, sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    if ate < de or (ate - de).days > 62:
        raise HTTPException(status_code=400, detail="Período inválido (até 62 dias).")
    return [t | {"inicio": t["inicio"].strftime("%H:%M"), "fim": t["fim"].strftime("%H:%M")} for t in conn.execute(
        "SELECT t.id, t.data, t.inicio, t.fim, f.id AS funcionario_id, f.nome AS funcionario, fr.nome AS funcao FROM turno t JOIN funcionario f ON f.id = t.funcionario_id JOIN funcao_rh fr ON fr.id = t.funcao_id "
        "WHERE f.loja_id = %s AND t.data BETWEEN %s AND %s ORDER BY t.data, t.inicio, f.nome", (LOJA_ID, de, ate)).fetchall()]


def _em_ausencia(conn, fid, dia) -> Optional[str]:
    r = conn.execute("SELECT tipo FROM ausencia WHERE funcionario_id = %s AND tipo <> 'falta' AND %s BETWEEN inicio AND fim LIMIT 1", (fid, dia)).fetchone()
    return r["tipo"] if r else None


@router.put("/turnos")
def lancar_turno(d: TurnoIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    """Escala do dia: uma linha por pessoa e dia (lançar de novo troca o turno)."""
    f = _func(conn, d.funcionario_id, ativo=True)
    if not conn.execute("SELECT 1 FROM funcao_rh WHERE id = %s AND loja_id = %s AND ativo", (d.funcao_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Função não encontrada.")
    if d.fim <= d.inicio:
        raise HTTPException(status_code=400, detail="O fim do turno precisa ser depois do início.")
    if d.data < f["admissao"]:
        raise HTTPException(status_code=400, detail="Antes da admissão.")
    aus = _em_ausencia(conn, d.funcionario_id, d.data)
    if aus:
        raise HTTPException(status_code=409, detail=f"A pessoa está de {aus} neste dia.")
    try:
        conn.execute("INSERT INTO turno (funcionario_id, data, funcao_id, inicio, fim) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (funcionario_id, data) DO UPDATE SET funcao_id = EXCLUDED.funcao_id, inicio = EXCLUDED.inicio, fim = EXCLUDED.fim",
                     (d.funcionario_id, d.data, d.funcao_id, d.inicio, d.fim))
        auditar(conn, sessao, "turno", "funcionario", d.funcionario_id, depois={"data": str(d.data), "inicio": d.inicio, "fim": d.fim})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"funcionario_id": d.funcionario_id, "data": d.data}


@router.delete("/turnos/{tid}")
def remover_turno(tid: int, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    r = conn.execute("DELETE FROM turno WHERE id = %s AND funcionario_id IN (SELECT id FROM funcionario WHERE loja_id = %s) RETURNING funcionario_id, data", (tid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Turno não encontrado.")
    auditar(conn, sessao, "remover_turno", "funcionario", r["funcionario_id"], depois={"data": str(r["data"])})
    conn.commit()
    return {"removido": tid}


@router.get("/escalados")
def escalados(data: date, funcao: Optional[str] = None, sessao=Depends(requer("producao.ver")), conn=Depends(get_db)):
    """Quem está escalado no dia (sem ausência), por função. Produção usa para saber quantos pizzaiolos estão ativos."""
    sql = ("SELECT f.id, f.nome, fr.nome AS funcao, t.inicio, t.fim FROM turno t JOIN funcionario f ON f.id = t.funcionario_id JOIN funcao_rh fr ON fr.id = t.funcao_id "
           "WHERE f.loja_id = %s AND f.ativo AND t.data = %s AND NOT EXISTS (SELECT 1 FROM ausencia a WHERE a.funcionario_id = f.id AND a.tipo <> 'falta' AND t.data BETWEEN a.inicio AND a.fim)")
    p: list = [LOJA_ID, data]
    if funcao:
        sql, p = sql + " AND lower(fr.nome) = lower(%s)", p + [funcao]
    linhas = [r | {"inicio": r["inicio"].strftime("%H:%M"), "fim": r["fim"].strftime("%H:%M")} for r in conn.execute(sql + " ORDER BY t.inicio, f.nome", p).fetchall()]
    return {"data": data, "quantidade": len(linhas), "pessoas": linhas}


# ---------------------------------------------------------------- ponto e banco de horas
def _min(t: time) -> int:
    return t.hour * 60 + t.minute


@router.put("/ponto")
def lancar_ponto(d: PontoIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    """Ponto lançado pelo gerente no começo (o relógio biométrico entra depois). Lançar de novo corrige, com auditoria."""
    f = _func(conn, d.funcionario_id)
    if d.data > agora().date() or d.data < f["admissao"]:
        raise HTTPException(status_code=400, detail="Data fora do intervalo (da admissão até hoje).")
    if d.saida <= d.entrada:
        raise HTTPException(status_code=400, detail="A saída precisa ser depois da entrada.")
    antes = conn.execute("SELECT entrada, saida FROM ponto WHERE funcionario_id = %s AND data = %s", (d.funcionario_id, d.data)).fetchone()
    try:
        conn.execute("INSERT INTO ponto (funcionario_id, data, entrada, saida, lancado_por, criado_em) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (funcionario_id, data) DO UPDATE SET entrada = EXCLUDED.entrada, saida = EXCLUDED.saida, lancado_por = EXCLUDED.lancado_por, criado_em = EXCLUDED.criado_em",
                     (d.funcionario_id, d.data, d.entrada, d.saida, sessao["usuario_id"], agora()))
        auditar(conn, sessao, "ponto", "funcionario", d.funcionario_id, antes={"entrada": str(antes["entrada"]), "saida": str(antes["saida"])} if antes else None, depois={"data": str(d.data), "entrada": d.entrada, "saida": d.saida})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"funcionario_id": d.funcionario_id, "data": d.data}


def _jornada_dia(conn, fid, dia) -> int:
    c = conn.execute("SELECT e.horas_semana, e.dias_trabalho FROM contrato c JOIN escala_tipo e ON e.id = c.escala_id WHERE c.funcionario_id = %s AND c.vigente_desde <= %s AND (c.vigente_ate IS NULL OR c.vigente_ate >= %s) "
                     "ORDER BY c.vigente_desde DESC LIMIT 1", (fid, dia, dia)).fetchone()
    return int(c["horas_semana"] * 60 / c["dias_trabalho"]) if c else 0


@router.get("/ponto/saldo")
def saldo_ponto(funcionario_id: int, mes: Optional[str] = None, sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    """Por dia: trabalhado, previsto (jornada da escala nos dias de turno) e saldo; mais o saldo do banco de horas."""
    _func(conn, funcionario_id)
    ini = _mes(mes)
    fim = ini.replace(day=monthrange(ini.year, ini.month)[1])
    pontos = {p["data"]: p for p in conn.execute("SELECT data, entrada, saida FROM ponto WHERE funcionario_id = %s AND data BETWEEN %s AND %s", (funcionario_id, ini, fim)).fetchall()}
    turnos_ = {t["data"] for t in conn.execute("SELECT data FROM turno WHERE funcionario_id = %s AND data BETWEEN %s AND %s", (funcionario_id, ini, fim)).fetchall()}
    dias, total = [], 0
    for dia in sorted(set(pontos) | turnos_):
        trab = _min(pontos[dia]["saida"]) - _min(pontos[dia]["entrada"]) if dia in pontos else 0
        prev = _jornada_dia(conn, funcionario_id, dia) if dia in turnos_ else 0
        total += trab - prev
        dias.append({"data": dia, "trabalhado_min": trab, "previsto_min": prev, "saldo_min": trab - prev, "falta_ponto": dia in turnos_ and dia not in pontos and dia < agora().date()})
    banco = conn.execute("SELECT COALESCE(sum(minutos), 0) AS s FROM banco_horas WHERE funcionario_id = %s", (funcionario_id,)).fetchone()["s"]
    return {"mes": ini.strftime("%Y-%m"), "dias": dias, "saldo_mes_min": total, "banco_horas_min": int(banco)}


@router.post("/banco-horas", status_code=201)
def lancar_banco(d: BancoHorasIn, sessao=Depends(requer("rh.aprovar")), conn=Depends(get_db)):
    """Hora extra ou compensação aprovada. Acima do limite mensal dos parâmetros, só administrador ou proprietário."""
    _func(conn, d.funcionario_id, ativo=True)
    if d.data > agora().date():
        raise HTTPException(status_code=400, detail="Data futura.")
    if d.minutos > 0:
        lim = vigentes(conn, LOJA_ID)["rh_limite_extra_min_mes"]["valor"]
        if lim is not None and not _pode_salarios(sessao):
            ini = d.data.replace(day=1)
            ja = conn.execute("SELECT COALESCE(sum(minutos), 0) AS s FROM banco_horas WHERE funcionario_id = %s AND minutos > 0 AND data >= %s AND data < %s",
                              (d.funcionario_id, ini, ini.replace(year=ini.year + (ini.month == 12), month=ini.month % 12 + 1))).fetchone()["s"]
            if ja + d.minutos > int(lim):
                raise HTTPException(status_code=403, detail=f"As horas extras do mês passam de {lim} minutos: só o administrador ou proprietário aprova.")
    saldo = conn.execute("SELECT COALESCE(sum(minutos), 0) AS s FROM banco_horas WHERE funcionario_id = %s", (d.funcionario_id,)).fetchone()["s"]
    if d.minutos < 0 and saldo + d.minutos < 0:
        raise HTTPException(status_code=400, detail="A compensação passa do saldo do banco de horas.")
    r = conn.execute("INSERT INTO banco_horas (funcionario_id, data, minutos, motivo, aprovado_por, criado_em) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (d.funcionario_id, d.data, d.minutos, d.motivo, sessao["usuario_id"], agora())).fetchone()
    auditar(conn, sessao, "banco_horas", "funcionario", d.funcionario_id, depois={"minutos": d.minutos, "motivo": d.motivo})
    conn.commit()
    return {"id": r["id"], "saldo_min": int(saldo) + d.minutos}


# ---------------------------------------------------------------- ausências e documentos
@router.get("/ausencias")
def ausencias(funcionario_id: Optional[int] = None, sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    sql, p = ("SELECT a.id, a.tipo, a.inicio, a.fim, a.motivo, f.id AS funcionario_id, f.nome AS funcionario FROM ausencia a JOIN funcionario f ON f.id = a.funcionario_id WHERE f.loja_id = %s"), [LOJA_ID]
    if funcionario_id:
        sql, p = sql + " AND a.funcionario_id = %s", p + [funcionario_id]
    return conn.execute(sql + " ORDER BY a.inicio DESC LIMIT 200", p).fetchall()


@router.post("/ausencias", status_code=201)
def lancar_ausencia(d: AusenciaIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    f = _func(conn, d.funcionario_id, ativo=True)
    if d.fim < d.inicio or d.inicio < f["admissao"]:
        raise HTTPException(status_code=400, detail="Período inválido.")
    if (d.fim - d.inicio).days > 366:
        raise HTTPException(status_code=400, detail="Período longo demais.")
    if conn.execute("SELECT 1 FROM ausencia WHERE funcionario_id = %s AND tipo = %s AND inicio <= %s AND fim >= %s", (d.funcionario_id, d.tipo, d.fim, d.inicio)).fetchone():
        raise HTTPException(status_code=409, detail="Já existe um lançamento do mesmo tipo neste período.")
    r = conn.execute("INSERT INTO ausencia (funcionario_id, tipo, inicio, fim, motivo, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                     (d.funcionario_id, d.tipo, d.inicio, d.fim, d.motivo, agora(), sessao["usuario_id"])).fetchone()
    # turnos que caem no período saem da escala (férias, afastamento e atestado); falta não cancela turno
    if d.tipo != "falta":
        conn.execute("DELETE FROM turno WHERE funcionario_id = %s AND data BETWEEN %s AND %s", (d.funcionario_id, d.inicio, d.fim))
    auditar(conn, sessao, "ausencia", "funcionario", d.funcionario_id, depois={"tipo": d.tipo, "inicio": str(d.inicio), "fim": str(d.fim)})
    conn.commit()
    return {"id": r["id"]}


@router.post("/documentos", status_code=201)
def lancar_documento(d: DocumentoRhIn, sessao=Depends(requer("rh.operar")), conn=Depends(get_db)):
    _func(conn, d.funcionario_id, ativo=True)
    if d.emitido and d.validade < d.emitido:
        raise HTTPException(status_code=400, detail="A validade não pode ser antes da emissão.")
    r = conn.execute("INSERT INTO documento_rh (funcionario_id, nome, emitido, validade, observacao, criado_em) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (d.funcionario_id, d.nome, d.emitido, d.validade, d.observacao, agora())).fetchone()
    auditar(conn, sessao, "documento", "funcionario", d.funcionario_id, depois={"nome": d.nome, "validade": str(d.validade)})
    conn.commit()
    return {"id": r["id"]}


@router.get("/alertas")
def alertas(sessao=Depends(requer("rh.ver")), conn=Depends(get_db)):
    hoje = agora().date()
    docs = conn.execute("SELECT d.id, f.nome AS funcionario, d.nome, d.validade FROM documento_rh d JOIN funcionario f ON f.id = d.funcionario_id WHERE f.loja_id = %s AND f.ativo AND d.validade <= %s "
                        "AND d.validade = (SELECT max(validade) FROM documento_rh x WHERE x.funcionario_id = d.funcionario_id AND lower(x.nome) = lower(d.nome)) ORDER BY d.validade", (LOJA_ID, hoje + timedelta(days=30))).fetchall()
    ferias = []
    for f in conn.execute("SELECT f.id, f.nome, f.admissao, (SELECT max(fim) FROM ausencia a WHERE a.funcionario_id = f.id AND a.tipo = 'ferias') AS ultima FROM funcionario f WHERE f.loja_id = %s AND f.ativo "
                          "AND EXISTS (SELECT 1 FROM contrato c WHERE c.funcionario_id = f.id AND c.vigente_ate IS NULL AND c.tipo = 'clt')", (LOJA_ID,)).fetchall():
        ref = f["ultima"] or f["admissao"]
        if (hoje - ref).days > 330:  # 11 meses sem férias: o período concessivo está perto
            ferias.append({"funcionario": f["nome"], "desde": ref, "dias_sem_ferias": (hoje - ref).days})
    sem_contrato = conn.execute("SELECT f.id, f.nome FROM funcionario f WHERE f.loja_id = %s AND f.ativo AND NOT EXISTS (SELECT 1 FROM contrato c WHERE c.funcionario_id = f.id AND c.vigente_ate IS NULL)", (LOJA_ID,)).fetchall()
    return {"documentos": [d | {"vencido": d["validade"] < hoje} for d in docs], "ferias_vencendo": ferias, "sem_contrato": sem_contrato}


@router.get("/meus-dados")
def meus_dados(sessao=Depends(requer("rh.proprio")), conn=Depends(get_db)):
    """O funcionário vê só o que é dele: escala, ponto e banco de horas. Nada de salário."""
    f = conn.execute("SELECT f.id, f.nome, fr.nome AS funcao FROM funcionario f JOIN funcao_rh fr ON fr.id = f.funcao_id WHERE f.usuario_id = %s AND f.loja_id = %s AND f.ativo", (sessao["usuario_id"], LOJA_ID)).fetchone()
    if not f:
        raise HTTPException(status_code=404, detail="Seu login não está ligado a um cadastro de funcionário.")
    hoje = agora().date()
    return {"funcionario": f["nome"], "funcao": f["funcao"],
            "turnos": [t | {"inicio": t["inicio"].strftime("%H:%M"), "fim": t["fim"].strftime("%H:%M")} for t in conn.execute("SELECT data, inicio, fim FROM turno WHERE funcionario_id = %s AND data >= %s ORDER BY data LIMIT 31", (f["id"], hoje)).fetchall()],
            "ponto": [p | {"entrada": p["entrada"].strftime("%H:%M"), "saida": p["saida"].strftime("%H:%M")} for p in conn.execute("SELECT data, entrada, saida FROM ponto WHERE funcionario_id = %s ORDER BY data DESC LIMIT 31", (f["id"],)).fetchall()],
            "banco_horas_min": int(conn.execute("SELECT COALESCE(sum(minutos), 0) AS s FROM banco_horas WHERE funcionario_id = %s", (f["id"],)).fetchone()["s"]),
            "ausencias": conn.execute("SELECT tipo, inicio, fim FROM ausencia WHERE funcionario_id = %s AND fim >= %s ORDER BY inicio", (f["id"], hoje)).fetchall()}


# ---------------------------------------------------------------- folha gerencial
def _previa(conn, ini: date) -> dict:
    prox = ini.replace(year=ini.year + (ini.month == 12), month=ini.month % 12 + 1)
    enc_pct = vigentes(conn, LOJA_ID)["rh_encargos_pct"]["valor"]
    enc_pct = Decimal(enc_pct) if enc_pct is not None else ZERO
    linhas, tb, te, tbe = [], ZERO, ZERO, ZERO
    for f in conn.execute("SELECT id, nome FROM funcionario WHERE loja_id = %s AND admissao < %s AND (desligamento IS NULL OR desligamento >= %s) ORDER BY nome", (LOJA_ID, prox, ini)).fetchall():
        c = conn.execute("SELECT tipo, forma_pagamento, valor FROM contrato WHERE funcionario_id = %s AND vigente_desde < %s AND (vigente_ate IS NULL OR vigente_ate >= %s) ORDER BY vigente_desde DESC LIMIT 1", (f["id"], prox, ini)).fetchone()
        if not c:
            continue
        if c["forma_pagamento"] == "mensal":
            bruto = c["valor"]
        elif c["forma_pagamento"] == "diaria":
            dias = conn.execute("SELECT count(*) AS n FROM ponto WHERE funcionario_id = %s AND data >= %s AND data < %s", (f["id"], ini, prox)).fetchone()["n"]
            bruto = c["valor"] * dias
        else:
            mins = conn.execute("SELECT COALESCE(sum(EXTRACT(EPOCH FROM (saida - entrada)) / 60), 0) AS m FROM ponto WHERE funcionario_id = %s AND data >= %s AND data < %s", (f["id"], ini, prox)).fetchone()["m"]
            bruto = (c["valor"] * Decimal(mins) / 60).quantize(Decimal("0.01"))
        enc = (bruto * enc_pct / 100).quantize(Decimal("0.01")) if c["tipo"] in COM_ENCARGOS else ZERO
        ben = conn.execute("SELECT COALESCE(sum(valor_mensal), 0) AS s FROM beneficio_funcionario WHERE funcionario_id = %s AND ativo", (f["id"],)).fetchone()["s"]
        linhas.append({"funcionario_id": f["id"], "funcionario": f["nome"], "tipo": c["tipo"], "bruto": bruto, "encargos": enc, "beneficios": ben, "total": bruto + enc + ben})
        tb, te, tbe = tb + bruto, te + enc, tbe + ben
    return {"competencia": ini, "linhas": linhas, "bruto": tb, "encargos": te, "beneficios": tbe, "total": tb + te + tbe}


def _previa_out(p: dict) -> dict:
    return {"competencia": p["competencia"].strftime("%Y-%m"), "bruto": fmt(p["bruto"]), "encargos": fmt(p["encargos"]), "beneficios": fmt(p["beneficios"]), "total": fmt(p["total"]),
            "linhas": [{k: (fmt(v) if isinstance(v, Decimal) else v) for k, v in l.items()} for l in p["linhas"]]}


@router.get("/folha/previa")
def previa(mes: Optional[str] = None, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    """Custo gerencial de pessoal do mês: salário (ou diárias e horas pelo ponto), encargos estimados e benefícios. A folha legal é do contador."""
    return _previa_out(_previa(conn, _mes(mes)))


@router.post("/folha/resumo", status_code=201)
def resumo_contador(d: FolhaResumoIn, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    """Valores da folha entregues pelo contador, digitados. Quando existem, valem no lugar da prévia."""
    ini = _mes(d.competencia)
    _func(conn, d.funcionario_id)
    if conn.execute("SELECT 1 FROM titulo WHERE origem_tipo = 'folha' AND competencia = %s AND situacao <> 'cancelado'", (ini,)).fetchone():
        raise HTTPException(status_code=409, detail="A folha deste mês já foi lançada em Contas a Pagar.")
    try:
        conn.execute("INSERT INTO folha_resumo (loja_id, competencia, funcionario_id, bruto, encargos, beneficios, criado_em, criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                     (LOJA_ID, ini, d.funcionario_id, parse_reais(d.bruto), parse_reais(d.encargos), parse_reais(d.beneficios), agora(), sessao["usuario_id"]))
        auditar(conn, sessao, "folha_resumo", "funcionario", d.funcionario_id, depois={"competencia": d.competencia, "bruto": d.bruto})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"competencia": d.competencia}


@router.post("/folha/lancar", status_code=201)
def lancar_folha(d: FolhaLancarIn, sessao=Depends(requer("rh.salarios")), conn=Depends(get_db)):
    """Cria em Contas a Pagar um título gerencial da folha do mês: o resumo do contador, se houver; senão a prévia."""
    ini = _mes(d.competencia)
    tipo = conn.execute("SELECT id FROM tipo_despesa WHERE loja_id = %s AND ativo AND lower(nome) = 'folha de pagamento'", (LOJA_ID,)).fetchone()
    if not tipo:
        raise HTTPException(status_code=400, detail="Crie antes o tipo de despesa 'Folha de pagamento' em Contas.")
    r = conn.execute("SELECT COALESCE(sum(bruto + encargos + beneficios), 0) AS t, count(*) AS n FROM folha_resumo WHERE loja_id = %s AND competencia = %s", (LOJA_ID, ini)).fetchone()
    previa = _previa(conn, ini)
    if r["n"] and r["n"] < len(previa["linhas"]):
        raise HTTPException(status_code=409, detail=f"O resumo do contador cobre {r['n']} de {len(previa['linhas'])} pessoas: complete o resumo antes de lançar.")
    total, origem = (r["t"], "resumo do contador") if r["n"] else (previa["total"], "prévia gerencial")
    if total <= 0:
        raise HTTPException(status_code=400, detail="Não há valor de folha neste mês.")
    venc = d.vencimento or ini.replace(year=ini.year + (ini.month == 12), month=ini.month % 12 + 1, day=5)
    try:
        tid = contas_svc._novo(conn, loja_id=LOJA_ID, sentido="pagar", descricao=f"Folha {ini.strftime('%m/%Y')} ({origem})", tipo_despesa_id=tipo["id"], valor=total, vencimento=venc, competencia=ini,
                               origem_tipo="folha", origem_id=int(ini.strftime("%Y%m")), criado_em=agora(), criado_por=sessao["usuario_id"])
        if not tid:
            conn.rollback()
            raise HTTPException(status_code=409, detail="A folha deste mês já foi lançada.")
        auditar(conn, sessao, "lancar_folha", "titulo", tid, depois={"competencia": d.competencia, "total": fmt(total), "origem": origem})
        conn.commit()
    except psycopg.Error as e:
        _ex(conn, e)
    return {"titulo_id": tid, "total": fmt(total), "origem": origem}
