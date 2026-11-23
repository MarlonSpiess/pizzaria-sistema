"""
Checklists (melhoria M4): início, acompanhamento e fim do dia, com registro por função.
- Modelos têm versões; a execução aponta para a versão que usou.
- Respostas são só de inserção: corrigir é gravar outra resposta (a mais recente vale).
- Quem responde: o perfil responsável do item (nulo = qualquer função) e a gerência.
- Nada trava a operação por padrão; "loja aberta" só é recusada se o parâmetro checklist_bloqueia_loja_aberta for sim.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import psycopg.errors
from fastapi import HTTPException

from api.database import agora, auditar
from api.security import PERMISSOES
from api.services.checklists_padrao import PADRAO
from api.services.parametros import CATALOGO, vigentes

GERENCIA = ("administrador", "proprietario", "gerente", "subgerente")
DIAS_RECORRENCIA = {"diario": 1, "semanal": 7, "mensal": 30, "semestral": 182}  # mensal e semestral aproximados
PONTOS_PERMISSAO = {"leitura_de_volta": "vendas.criar", "conferencia_final": "entregas.despachar", "causa_atraso": "vendas.gerir"}


def _dec(txt) -> Decimal:
    try:
        return Decimal(str(txt).replace(",", "."))
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Número inválido.")


# ------------------------------------------------------------------ modelos
def instalar_padrao(conn, sessao, loja_id: int, _repetir: bool = True) -> list[str]:
    """Instala os modelos padrão que a loja ainda não tem. Idempotente; se outra instalação ganhar a corrida, refaz uma vez e instala só o que faltar."""
    try:
        return _instalar_padrao(conn, sessao, loja_id)
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        if _repetir:
            return instalar_padrao(conn, sessao, loja_id, _repetir=False)
        raise HTTPException(status_code=409, detail="Os modelos estão sendo instalados por outra pessoa. Tente de novo.")


def _instalar_padrao(conn, sessao, loja_id: int) -> list[str]:
    novos = []
    for m in PADRAO:
        if conn.execute("SELECT 1 FROM checklist_modelo WHERE loja_id = %s AND codigo = %s", (loja_id, m["codigo"])).fetchone():
            continue
        mid = conn.execute(
            "INSERT INTO checklist_modelo (loja_id, codigo, nome, tipo, criado_em, criado_por) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (loja_id, m["codigo"], m["nome"], m["tipo"], agora(), sessao["usuario_id"])).fetchone()["id"]
        _criar_versao(conn, sessao, mid, 1, m["itens"])
        auditar(conn, sessao, "instalar_modelo_padrao", "checklist_modelo", mid, depois={"codigo": m["codigo"], "itens": len(m["itens"])})
        novos.append(m["codigo"])
    conn.commit()
    return novos


def _criar_versao(conn, sessao, modelo_id: int, numero: int, itens: list[dict]) -> int:
    vid = conn.execute("INSERT INTO checklist_versao (modelo_id, numero, vigente, publicada_em, publicada_por) VALUES (%s, %s, true, %s, %s) RETURNING id",
                       (modelo_id, numero, agora(), sessao["usuario_id"])).fetchone()["id"]
    for ordem, i in enumerate(itens):
        for chave in (i.get("limite_min_param"), i.get("limite_max_param")):
            if chave and (chave not in CATALOGO or CATALOGO[chave][0] not in ("temperatura", "decimal_pos", "inteiro_pos", "pct", "dinheiro")):
                raise HTTPException(status_code=400, detail=f"Item {i['codigo']}: o parâmetro '{chave}' não existe ou não é numérico.")
        if (i["tipo_resposta"] == "automatico") != bool(i.get("fonte_auto")):
            raise HTTPException(status_code=400, detail=f"Item {i['codigo']}: fonte automática só para itens automáticos, e todo item automático precisa de fonte.")
        lmin = _dec(i["limite_min"]) if i.get("limite_min") not in (None, "") else None
        lmax = _dec(i["limite_max"]) if i.get("limite_max") not in (None, "") else None
        if lmin is not None and lmax is not None and lmin > lmax:
            raise HTTPException(status_code=400, detail=f"Item {i['codigo']}: limite mínimo maior que o máximo.")
        conn.execute(
            "INSERT INTO checklist_item (versao_id, setor, ordem, codigo, texto, criterio, perfil_responsavel, tipo_resposta, fonte_auto, unidade, "
            "limite_min, limite_max, limite_min_param, limite_max_param, obrigatorio, recorrencia, origem) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (vid, i["setor"], ordem, i["codigo"], i["texto"], i.get("criterio"), i.get("perfil_responsavel"), i["tipo_resposta"], i.get("fonte_auto"),
             i.get("unidade"), lmin, lmax, i.get("limite_min_param"), i.get("limite_max_param"), i.get("obrigatorio", True),
             i.get("recorrencia", "todo_turno"), i.get("origem")))
    return vid


def nova_versao(conn, sessao, loja_id: int, codigo: str, itens: list[dict]) -> dict:
    """Publica uma nova versão; a anterior deixa de ser a vigente. Execuções antigas continuam apontando para a versão que usaram."""
    m = conn.execute("SELECT id FROM checklist_modelo WHERE loja_id = %s AND codigo = %s FOR UPDATE", (loja_id, codigo)).fetchone()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado.")
    ult = conn.execute("SELECT coalesce(max(numero), 0) AS n FROM checklist_versao WHERE modelo_id = %s", (m["id"],)).fetchone()["n"]
    codigos = [i["codigo"] for i in itens]
    if len(set(codigos)) != len(codigos):
        raise HTTPException(status_code=400, detail="Há códigos de item repetidos.")
    conn.execute("UPDATE checklist_versao SET vigente = false WHERE modelo_id = %s AND vigente", (m["id"],))
    vid = _criar_versao(conn, sessao, m["id"], ult + 1, itens)
    auditar(conn, sessao, "publicar_versao", "checklist_modelo", m["id"], depois={"versao": ult + 1, "itens": len(itens)})
    conn.commit()
    return {"modelo": codigo, "versao": ult + 1, "versao_id": vid, "itens": len(itens)}


def listar_modelos(conn, loja_id: int) -> list[dict]:
    return conn.execute(
        "SELECT m.codigo, m.nome, m.tipo, m.ativo, v.numero AS versao, v.publicada_em, "
        "(SELECT count(*) FROM checklist_item i WHERE i.versao_id = v.id) AS itens "
        "FROM checklist_modelo m LEFT JOIN checklist_versao v ON v.modelo_id = m.id AND v.vigente WHERE m.loja_id = %s ORDER BY m.id", (loja_id,)).fetchall()


def _modelo_vigente(conn, loja_id: int, codigo: str) -> dict:
    r = conn.execute(
        "SELECT m.id AS modelo_id, m.codigo, m.nome, m.tipo, v.id AS versao_id, v.numero FROM checklist_modelo m "
        "JOIN checklist_versao v ON v.modelo_id = m.id AND v.vigente WHERE m.loja_id = %s AND m.codigo = %s AND m.ativo", (loja_id, codigo)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Checklist não encontrado ou sem versão vigente. Instale os modelos padrão em Admin > Checklists.")
    return r


# ------------------------------------------------------------------ itens e respostas
def _pode_item(perfil: str, item: dict) -> bool:
    return perfil in GERENCIA or item["perfil_responsavel"] is None or item["perfil_responsavel"] == perfil


def _limites(item: dict, par: dict) -> tuple[Decimal | None, Decimal | None]:
    lmin, lmax = item["limite_min"], item["limite_max"]
    if item["limite_min_param"] and par.get(item["limite_min_param"], {}).get("valor") is not None:
        lmin = Decimal(par[item["limite_min_param"]]["valor"])
    if item["limite_max_param"] and par.get(item["limite_max_param"], {}).get("valor") is not None:
        lmax = Decimal(par[item["limite_max_param"]]["valor"])
    return lmin, lmax


def _vencido(conn, modelo_id: int, item: dict, data: date) -> bool:
    """Item periódico só aparece quando venceu: sem resposta conforme anterior ou intervalo cumprido."""
    dias = DIAS_RECORRENCIA.get(item["recorrencia"])
    if not dias:
        return True
    # só vale resposta de execução anterior à avaliada (data menor, ou mesma data e id menor): reabrir uma execução antiga não muda o que ela mostra
    # vale só a resposta vigente (a última) de cada execução: conforme corrigido para não conforme não conta
    r = conn.execute(
        "SELECT max(u.data) AS ultima FROM (SELECT DISTINCT ON (r.execucao_id, r.item_id) r.resultado, e2.data "
        "FROM checklist_resposta r JOIN checklist_item i ON i.id = r.item_id "
        "JOIN checklist_versao v ON v.id = i.versao_id JOIN checklist_execucao e2 ON e2.id = r.execucao_id "
        "WHERE v.modelo_id = %s AND i.codigo = %s AND (e2.data < %s OR (e2.data = %s AND e2.id < %s)) "
        "ORDER BY r.execucao_id, r.item_id, r.id DESC) u WHERE u.resultado = 'conforme'",
        (modelo_id, item["codigo"], data, data, item["execucao_id"])).fetchone()
    return not r["ultima"] or r["ultima"] + timedelta(days=dias) <= data


def _auto(conn, fonte: str, loja_id: int, data: date) -> tuple[str, str]:
    """Leituras que o sistema já faz: devolve (resultado, texto). Cada fato continua registrado uma vez, no módulo dele."""
    if fonte == "caixa_aberto":
        r = conn.execute("SELECT situacao FROM caixa_dia WHERE loja_id = %s AND data = %s", (loja_id, data)).fetchone()
        ok = bool(r) and r["situacao"] == "aberto"
        return ("conforme" if ok else "nao_conforme"), ("Caixa de hoje aberto." if ok else "Caixa de hoje não está aberto.")
    if fonte == "loja_aberta":
        r = conn.execute("SELECT loja_aberta FROM loja WHERE id = %s", (loja_id,)).fetchone()
        ok = bool(r and r["loja_aberta"])
        return ("conforme" if ok else "nao_conforme"), ("Loja aberta." if ok else "Loja marcada como fechada.")
    if fonte == "backup_do_dia":
        r = conn.execute("SELECT max(iniciado_em) AS quando FROM backup_registro WHERE loja_id = %s AND sucesso", (loja_id,)).fetchone()
        ok = bool(r and r["quando"] and r["quando"] >= agora() - timedelta(hours=24))
        return ("conforme" if ok else "nao_conforme"), ("Backup concluído nas últimas 24 horas." if ok else "Sem backup concluído nas últimas 24 horas.")
    raise HTTPException(status_code=400, detail="Fonte automática desconhecida.")


def _execucao(conn, loja_id: int, exec_id: int, travar: bool = False) -> dict:
    """travar=True segura a linha da execução até o commit: responder, concluir e resolver pendência não se atropelam."""
    e = conn.execute(
        "SELECT e.*, v.modelo_id, v.numero AS versao, m.codigo AS modelo, m.nome AS modelo_nome, m.tipo FROM checklist_execucao e "
        "JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo m ON m.id = v.modelo_id WHERE e.id = %s AND e.loja_id = %s"
        + (" FOR UPDATE OF e" if travar else ""), (exec_id, loja_id)).fetchone()
    if not e:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return e


def _itens_visiveis(conn, e: dict) -> list[dict]:
    itens = conn.execute("SELECT i.*, %s::bigint AS execucao_id FROM checklist_item i WHERE i.versao_id = %s ORDER BY i.ordem", (e["id"], e["versao_id"])).fetchall()
    return [i for i in itens if _vencido(conn, e["modelo_id"], i, e["data"])]


def _vigentes(conn, exec_id: int) -> dict[int, dict]:
    linhas = conn.execute("SELECT DISTINCT ON (r.item_id) r.*, u.nome AS respondida_por_nome FROM checklist_resposta r LEFT JOIN usuario u ON u.id = r.respondida_por "
                          "WHERE r.execucao_id = %s ORDER BY r.item_id, r.id DESC", (exec_id,)).fetchall()
    return {r["item_id"]: r for r in linhas}


def _resumo(conn, loja_id: int, e: dict, perfil: str | None = None) -> dict:
    """perfil=None conta todos os itens (gerência e relatórios); com perfil, só os itens que essa função enxerga."""
    itens = _itens_visiveis(conn, e)
    if perfil is not None:
        itens = [i for i in itens if _pode_item(perfil, i)]
    ids = {i["id"] for i in itens}
    resp = _vigentes(conn, e["id"])
    obrig = [i for i in itens if i["obrigatorio"] and i["tipo_resposta"] != "automatico"]
    return {
        "total_itens": len(itens), "obrigatorios": len(obrig),
        "respondidos": sum(1 for i in obrig if i["id"] in resp),
        "nao_conformes": sum(1 for r in resp.values() if r["resultado"] == "nao_conforme" and r["item_id"] in ids),
        "pendencias_abertas": conn.execute(
            "SELECT count(*) AS n FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE r.execucao_id = %s AND p.resolvida_em IS NULL",
            (e["id"],)).fetchone()["n"],
    }


def _linha_execucao(conn, loja_id: int, e: dict, perfil: str | None = None) -> dict:
    return {"id": e["id"], "modelo": e["modelo"], "nome": e["modelo_nome"], "tipo": e["tipo"], "versao": e["versao"], "data": e["data"], "turno": e["turno"],
            "situacao": e["situacao"], "iniciada_em": e["iniciada_em"], "concluida_em": e["concluida_em"], **_resumo(conn, loja_id, e, perfil)}


def hoje_do_perfil(conn, sessao, loja_id: int, data: date) -> dict:
    perfil = sessao["perfil"]
    modelos = conn.execute(
        "SELECT m.codigo, m.nome, m.tipo, v.id AS versao_id, v.numero FROM checklist_modelo m JOIN checklist_versao v ON v.modelo_id = m.id AND v.vigente "
        "WHERE m.loja_id = %s AND m.ativo ORDER BY m.id", (loja_id,)).fetchall()
    saida = []
    for m in modelos:
        itens = conn.execute("SELECT perfil_responsavel FROM checklist_item WHERE versao_id = %s", (m["versao_id"],)).fetchall()
        if not any(_pode_item(perfil, i) for i in itens):
            continue  # a função não tem item neste checklist
        execs = conn.execute(
            "SELECT e.*, v.modelo_id, v.numero AS versao, mm.codigo AS modelo, mm.nome AS modelo_nome, mm.tipo FROM checklist_execucao e "
            "JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo mm ON mm.id = v.modelo_id "
            "WHERE e.loja_id = %s AND e.data = %s AND mm.codigo = %s ORDER BY e.id", (loja_id, data, m["codigo"])).fetchall()
        saida.append({"codigo": m["codigo"], "nome": m["nome"], "tipo": m["tipo"], "versao": m["numero"],
                      "execucoes": [_linha_execucao(conn, loja_id, e, perfil) for e in execs]})
    return {"data": data, "modelos": saida, "gerencia": perfil in GERENCIA}


def iniciar(conn, sessao, loja_id: int, codigo: str, turno: str | None, data: date) -> dict:
    """Uma execução por modelo, dia e turno (idempotente). Acompanhamento sem turno: devolve a rodada aberta ou abre a próxima."""
    m = _modelo_vigente(conn, loja_id, codigo)
    # trava o modelo: dois tablets (ou uma nova versão publicada) não criam duas execuções do mesmo modelo, dia e turno
    conn.execute("SELECT id FROM checklist_modelo WHERE id = %s FOR UPDATE", (m["modelo_id"],))
    if not any(_pode_item(sessao["perfil"], i) for i in conn.execute("SELECT perfil_responsavel FROM checklist_item WHERE versao_id = %s", (m["versao_id"],)).fetchall()):
        raise HTTPException(status_code=403, detail="Este checklist não tem itens para a sua função.")
    existentes = conn.execute(
        "SELECT e.id, e.turno, e.situacao FROM checklist_execucao e JOIN checklist_versao v ON v.id = e.versao_id "
        "WHERE e.loja_id = %s AND e.data = %s AND v.modelo_id = %s ORDER BY e.id", (loja_id, data, m["modelo_id"])).fetchall()
    if m["tipo"] == "acompanhamento" and turno is None:
        abertas = [x for x in existentes if x["situacao"] == "aberta"]
        if abertas:
            return {"id": abertas[-1]["id"], "criada": False}
        turno = f"rodada {len(existentes) + 1}"
    turno = turno or "dia"
    for x in existentes:
        if x["turno"] == turno:
            return {"id": x["id"], "criada": False}
    try:
        eid = conn.execute(
            "INSERT INTO checklist_execucao (loja_id, versao_id, data, turno, iniciada_em, iniciada_por) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (loja_id, m["versao_id"], data, turno, agora(), sessao["usuario_id"])).fetchone()["id"]
    except psycopg.errors.UniqueViolation:  # outro tablet iniciou no mesmo instante: devolve a execução que ganhou
        conn.rollback()
        x = conn.execute("SELECT e.id FROM checklist_execucao e JOIN checklist_versao v ON v.id = e.versao_id WHERE e.loja_id = %s AND e.data = %s AND v.modelo_id = %s AND e.turno = %s",
                         (loja_id, data, m["modelo_id"], turno)).fetchone()
        if x:
            return {"id": x["id"], "criada": False}
        raise HTTPException(status_code=409, detail="Não foi possível iniciar agora. Tente de novo.")
    auditar(conn, sessao, "iniciar_checklist", "checklist_execucao", eid, depois={"modelo": codigo, "data": str(data), "turno": turno})
    conn.commit()
    return {"id": eid, "criada": True}


def detalhe(conn, sessao, loja_id: int, exec_id: int) -> dict:
    e = _execucao(conn, loja_id, exec_id)
    perfil = sessao["perfil"]
    par = vigentes(conn, loja_id)
    resp = _vigentes(conn, exec_id)
    itens = []
    for i in _itens_visiveis(conn, e):
        if not _pode_item(perfil, i):
            continue
        lmin, lmax = _limites(i, par)
        r = resp.get(i["id"])
        item = {"id": i["id"], "setor": i["setor"], "codigo": i["codigo"], "texto": i["texto"], "criterio": i["criterio"], "tipo_resposta": i["tipo_resposta"],
                "unidade": i["unidade"], "limite_min": lmin, "limite_max": lmax, "obrigatorio": i["obrigatorio"], "perfil_responsavel": i["perfil_responsavel"],
                "recorrencia": i["recorrencia"], "origem": i["origem"], "resposta": None, "automatico": None}
        if r:
            item["resposta"] = {"resultado": r["resultado"], "valor_numerico": r["valor_numerico"], "valor_texto": r["valor_texto"],
                                "acao_corretiva": r["acao_corretiva"], "fora_do_limite": r["fora_do_limite"], "automatica": r["automatica"],
                                "respondida_em": r["respondida_em"], "respondida_por": r["respondida_por"], "respondida_por_nome": r["respondida_por_nome"]}
        if i["tipo_resposta"] == "automatico" and e["situacao"] == "aberta":
            res, txt = _auto(conn, i["fonte_auto"], loja_id, e["data"])
            item["automatico"] = {"resultado": res, "texto": txt}
        itens.append(item)
    return {"execucao": _linha_execucao(conn, loja_id, e, perfil), "itens": itens}


def responder(conn, sessao, loja_id: int, exec_id: int, item_id: int, d) -> dict:
    e = _execucao(conn, loja_id, exec_id, travar=True)
    concluida = e["situacao"] != "aberta"
    if concluida and "checklist.resolver" not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=409, detail="Esta execução já foi concluída; só a gerência corrige, informando o motivo.")
    i = conn.execute("SELECT * FROM checklist_item WHERE id = %s AND versao_id = %s", (item_id, e["versao_id"])).fetchone()
    if not i:
        raise HTTPException(status_code=404, detail="Item não pertence a este checklist.")
    if not _pode_item(sessao["perfil"], i):
        raise HTTPException(status_code=403, detail="Este item é de outra função.")
    if i["tipo_resposta"] == "automatico":
        raise HTTPException(status_code=400, detail="Item automático: o sistema confere sozinho.")
    if not _vencido(conn, e["modelo_id"], dict(i, execucao_id=exec_id), e["data"]):
        raise HTTPException(status_code=409, detail="Este item periódico ainda não venceu.")

    resultado, valor, fora = d.resultado, None, False
    acao = d.acao_corretiva
    if d.resultado == "nao_se_aplica":
        if not d.valor_texto:
            raise HTTPException(status_code=400, detail="Informe o motivo de 'não se aplica'.")
    elif i["tipo_resposta"] == "numero":
        if d.valor_numerico is None:
            raise HTTPException(status_code=400, detail="Informe o valor medido.")
        valor = _dec(d.valor_numerico)
        lmin, lmax = _limites(i, vigentes(conn, loja_id))
        fora = (lmin is not None and valor < lmin) or (lmax is not None and valor > lmax)
        # fora do limite é sempre não conforme; dentro do limite (ou sem limite) vale o "não conforme" explícito de quem mediu
        resultado = "nao_conforme" if fora or d.resultado == "nao_conforme" else "conforme"
        if resultado == "nao_conforme" and not acao:
            raise HTTPException(status_code=400, detail="Valor fora do limite: informe a ação corretiva." if fora else "Informe a ação corretiva.")
    else:
        if d.resultado is None:
            raise HTTPException(status_code=400, detail="Informe conforme, não conforme ou não se aplica.")
        if d.resultado == "nao_conforme" and not acao:
            raise HTTPException(status_code=400, detail="Informe a ação corretiva.")
    anterior = conn.execute("SELECT id, resultado FROM checklist_resposta WHERE execucao_id = %s AND item_id = %s ORDER BY id DESC LIMIT 1", (exec_id, item_id)).fetchone()
    # Corrigir é gravar outra resposta COM motivo: ao sair de "não conforme" e ao corrigir execução já concluída, a ação ou o motivo é obrigatório.
    corrigindo = bool(anterior) and anterior["resultado"] == "nao_conforme" and resultado != "nao_conforme"
    exige_motivo = corrigindo or concluida
    if exige_motivo and resultado != "nao_conforme" and not (acao or (d.resultado == "nao_se_aplica" and d.valor_texto)):
        raise HTTPException(status_code=400, detail="Informe o que foi feito para corrigir (campo de ação corretiva).")
    rid = conn.execute(
        "INSERT INTO checklist_resposta (execucao_id, item_id, resultado, valor_numerico, valor_texto, acao_corretiva, fora_do_limite, respondida_em, respondida_por, substitui_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (exec_id, item_id, resultado, valor, d.valor_texto if d.resultado == "nao_se_aplica" else None, acao if (resultado == "nao_conforme" or exige_motivo) else None,
         fora, agora(), sessao["usuario_id"], anterior["id"] if anterior else None)).fetchone()["id"]
    if anterior:  # a resposta nova substitui a anterior: a pendência antiga sempre fecha (e a nova nasce se continuar não conforme)
        conn.execute("UPDATE checklist_pendencia SET resolvida_em = %s, resolvida_por = %s, resolucao = %s WHERE resposta_id = %s AND resolvida_em IS NULL",
                     (agora(), sessao["usuario_id"], ("Corrigido: " + (acao or d.valor_texto or "")) if resultado != "nao_conforme" else "Substituída por nova resposta do mesmo item.", anterior["id"]))
    if resultado == "nao_conforme":
        conn.execute(
            "INSERT INTO checklist_pendencia (loja_id, resposta_id, descricao, perfil_responsavel, criada_em) VALUES (%s, %s, %s, %s, %s)",
            (loja_id, rid, f"{i['codigo']} {i['texto']}: {acao}", i["perfil_responsavel"], agora()))
    situacao = e["situacao"]
    if concluida:  # correção depois de concluir: a situação acompanha as pendências abertas
        abertas = conn.execute("SELECT count(*) AS n FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE r.execucao_id = %s AND p.resolvida_em IS NULL",
                               (exec_id,)).fetchone()["n"]
        situacao = "concluida_com_pendencia" if abertas else "concluida"
        conn.execute("UPDATE checklist_execucao SET situacao = %s WHERE id = %s", (situacao, exec_id))
    auditar(conn, sessao, "responder_checklist", "checklist_resposta", rid,
            depois={"execucao": exec_id, "item": i["codigo"], "resultado": resultado, "valor": None if valor is None else str(valor), "fora_do_limite": fora,
                    "correcao": bool(exige_motivo), "execucao_concluida": concluida})
    conn.commit()
    return {"id": rid, "resultado": resultado, "fora_do_limite": fora, "situacao": situacao}


def concluir(conn, sessao, loja_id: int, exec_id: int) -> dict:
    e = _execucao(conn, loja_id, exec_id, travar=True)
    if e["situacao"] != "aberta":
        raise HTTPException(status_code=409, detail="Esta execução já foi concluída.")
    itens = _itens_visiveis(conn, e)
    resp = _vigentes(conn, exec_id)
    faltam = [i["codigo"] for i in itens if i["obrigatorio"] and i["tipo_resposta"] != "automatico" and i["id"] not in resp]
    if faltam:
        raise HTTPException(status_code=409, detail=f"Faltam {len(faltam)} item(ns) obrigatório(s): " + ", ".join(faltam[:8]) + ("..." if len(faltam) > 8 else ""))
    for i in itens:  # grava o resultado das leituras automáticas no momento da conclusão
        if i["tipo_resposta"] != "automatico":
            continue
        res, txt = _auto(conn, i["fonte_auto"], loja_id, e["data"])
        rid = conn.execute(
            "INSERT INTO checklist_resposta (execucao_id, item_id, resultado, valor_texto, automatica, respondida_em, respondida_por, substitui_id) "
            "VALUES (%s, %s, %s, %s, true, %s, %s, %s) RETURNING id",
            (exec_id, i["id"], res, txt, agora(), sessao["usuario_id"], resp[i["id"]]["id"] if i["id"] in resp else None)).fetchone()["id"]
        if res == "nao_conforme":
            conn.execute("INSERT INTO checklist_pendencia (loja_id, resposta_id, descricao, perfil_responsavel, criada_em) VALUES (%s, %s, %s, %s, %s)",
                         (loja_id, rid, f"{i['codigo']} {i['texto']}: {txt}", None, agora()))
    abertas = conn.execute(
        "SELECT count(*) AS n FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE r.execucao_id = %s AND p.resolvida_em IS NULL",
        (exec_id,)).fetchone()["n"]
    situacao = "concluida_com_pendencia" if abertas else "concluida"
    conn.execute("UPDATE checklist_execucao SET situacao = %s, concluida_em = %s, concluida_por = %s WHERE id = %s", (situacao, agora(), sessao["usuario_id"], exec_id))
    auditar(conn, sessao, "concluir_checklist", "checklist_execucao", exec_id, depois={"situacao": situacao, "pendencias_abertas": abertas})
    conn.commit()
    return {"id": exec_id, "situacao": situacao, "pendencias_abertas": abertas}


# ------------------------------------------------------------------ pendências e aderência
def pendencias(conn, loja_id: int, so_abertas: bool = True) -> list[dict]:
    return conn.execute(
        "SELECT p.id, p.descricao, p.perfil_responsavel, p.criada_em, p.resolvida_em, p.resolucao, e.id AS execucao_id, e.data, m.codigo AS modelo, m.nome AS modelo_nome "
        "FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id JOIN checklist_execucao e ON e.id = r.execucao_id "
        "JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo m ON m.id = v.modelo_id WHERE p.loja_id = %s"
        + (" AND p.resolvida_em IS NULL" if so_abertas else "") + " ORDER BY p.criada_em DESC LIMIT 200", (loja_id,)).fetchall()


def resolver_pendencia(conn, sessao, loja_id: int, pid: int, resolucao: str) -> dict:
    base = conn.execute("SELECT r.execucao_id FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE p.id = %s AND p.loja_id = %s", (pid, loja_id)).fetchone()
    if not base:
        raise HTTPException(status_code=404, detail="Pendência não encontrada.")
    conn.execute("SELECT id FROM checklist_execucao WHERE id = %s FOR UPDATE", (base["execucao_id"],))  # mesma ordem de trava de responder e concluir
    p = conn.execute("SELECT p.*, r.execucao_id FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE p.id = %s AND p.loja_id = %s FOR UPDATE OF p",
                     (pid, loja_id)).fetchone()
    if p["resolvida_em"]:
        raise HTTPException(status_code=409, detail="Esta pendência já foi resolvida.")
    conn.execute("UPDATE checklist_pendencia SET resolvida_em = %s, resolvida_por = %s, resolucao = %s WHERE id = %s", (agora(), sessao["usuario_id"], resolucao, pid))
    restam = conn.execute("SELECT count(*) AS n FROM checklist_pendencia p JOIN checklist_resposta r ON r.id = p.resposta_id WHERE r.execucao_id = %s AND p.resolvida_em IS NULL",
                          (p["execucao_id"],)).fetchone()["n"]
    if not restam:
        conn.execute("UPDATE checklist_execucao SET situacao = 'concluida' WHERE id = %s AND situacao = 'concluida_com_pendencia'", (p["execucao_id"],))
    auditar(conn, sessao, "resolver_pendencia", "checklist_pendencia", pid, depois={"resolucao": resolucao})
    conn.commit()
    return {"id": pid, "resolvida": True}


def aderencia(conn, loja_id: int, de: date, ate: date) -> dict:
    """Itens obrigatórios feitos, não conformidades e 'não se aplica' por modelo no período. Só lê."""
    modelos = conn.execute("SELECT DISTINCT m.codigo, m.nome FROM checklist_execucao e JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo m ON m.id = v.modelo_id "
                           "WHERE e.loja_id = %s AND e.data BETWEEN %s AND %s ORDER BY m.codigo", (loja_id, de, ate)).fetchall()
    saida = []
    for m in modelos:
        execs = conn.execute(
            "SELECT e.*, v.modelo_id, v.numero AS versao, mm.codigo AS modelo, mm.nome AS modelo_nome, mm.tipo FROM checklist_execucao e JOIN checklist_versao v ON v.id = e.versao_id "
            "JOIN checklist_modelo mm ON mm.id = v.modelo_id WHERE e.loja_id = %s AND e.data BETWEEN %s AND %s AND mm.codigo = %s", (loja_id, de, ate, m["codigo"])).fetchall()
        tot = feitos = nc = 0
        for e in execs:
            r = _resumo(conn, loja_id, e)
            tot += r["obrigatorios"]; feitos += r["respondidos"]; nc += r["nao_conformes"]
        nas = conn.execute(
            "SELECT i.codigo, i.texto, count(*) AS vezes FROM (SELECT DISTINCT ON (r.execucao_id, r.item_id) r.* FROM checklist_resposta r JOIN checklist_execucao e ON e.id = r.execucao_id "
            "JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo mm ON mm.id = v.modelo_id WHERE e.loja_id = %s AND e.data BETWEEN %s AND %s AND mm.codigo = %s "
            "ORDER BY r.execucao_id, r.item_id, r.id DESC) rr JOIN checklist_item i ON i.id = rr.item_id WHERE rr.resultado = 'nao_se_aplica' "
            "GROUP BY i.codigo, i.texto ORDER BY vezes DESC LIMIT 5", (loja_id, de, ate, m["codigo"])).fetchall()
        saida.append({"modelo": m["codigo"], "nome": m["nome"], "execucoes": len(execs),
                      "concluidas": sum(1 for e in execs if e["situacao"] != "aberta"),
                      "itens_obrigatorios": tot, "itens_feitos": feitos, "aderencia_pct": round(100 * feitos / tot, 1) if tot else None,
                      "nao_conformes": nc, "mais_nao_se_aplica": nas})
    pend = conn.execute("SELECT count(*) FILTER (WHERE resolvida_em IS NULL) AS abertas, count(*) FILTER (WHERE resolvida_em IS NOT NULL) AS resolvidas FROM checklist_pendencia "
                        "WHERE loja_id = %s AND criada_em::date BETWEEN %s AND %s", (loja_id, de, ate)).fetchone()
    return {"de": de, "ate": ate, "modelos": saida, "pendencias_abertas": pend["abertas"], "pendencias_resolvidas": pend["resolvidas"]}


# ------------------------------------------------------------------ ligação com a loja aberta e pontos de controle do pedido
def inicio_pendente(conn, loja_id: int, data: date) -> bool:
    """Verdadeiro só se a loja tem o checklist de início vigente e ele não foi concluído hoje. Sem modelo instalado, não cobra nada."""
    tem = conn.execute("SELECT 1 FROM checklist_modelo m JOIN checklist_versao v ON v.modelo_id = m.id AND v.vigente WHERE m.loja_id = %s AND m.tipo = 'inicio_dia' AND m.ativo",
                       (loja_id,)).fetchone()
    if not tem:
        return False
    feito = conn.execute(
        "SELECT 1 FROM checklist_execucao e JOIN checklist_versao v ON v.id = e.versao_id JOIN checklist_modelo m ON m.id = v.modelo_id "
        "WHERE e.loja_id = %s AND e.data = %s AND m.tipo = 'inicio_dia' AND m.ativo AND e.situacao IN ('concluida','concluida_com_pendencia')", (loja_id, data)).fetchone()
    return not feito


def registrar_controle(conn, sessao, loja_id: int, pedido_id: int, ponto: str, ok: bool, texto: str | None) -> dict:
    if PONTOS_PERMISSAO[ponto] not in PERMISSOES.get(sessao["perfil"], set()):
        raise HTTPException(status_code=403, detail="Perfil insuficiente para este ponto de controle.")
    ped = conn.execute("SELECT situacao FROM pedido WHERE id = %s AND loja_id = %s", (pedido_id, loja_id)).fetchone()
    if not ped:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if ped["situacao"] == "cancelado" and ponto != "causa_atraso":
        raise HTTPException(status_code=409, detail="Pedido cancelado não recebe este ponto de controle.")
    if ponto == "causa_atraso" and not texto:
        raise HTTPException(status_code=400, detail="Descreva a causa do atraso.")
    cid = conn.execute("INSERT INTO pedido_controle (loja_id, pedido_id, ponto, ok, texto, feito_por, feito_em) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                       (loja_id, pedido_id, ponto, ok, texto, sessao["usuario_id"], agora())).fetchone()["id"]
    auditar(conn, sessao, "controle_pedido", "pedido", pedido_id, depois={"ponto": ponto, "ok": ok})
    conn.commit()
    return {"id": cid}


def controles_do_pedido(conn, loja_id: int, pedido_id: int) -> list[dict]:
    return conn.execute("SELECT DISTINCT ON (ponto) ponto, ok, texto, feito_por, feito_em FROM pedido_controle WHERE loja_id = %s AND pedido_id = %s ORDER BY ponto, id DESC",
                        (loja_id, pedido_id)).fetchall()
