"""Compras: fornecedores, lista de necessidades, cotação, lista definitiva, pedido de compra e recebimento com entrada da nota."""
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, traduzir_erro
from api.schemas import (CotacaoIn, DefinirIn, FornecedorIn, FornecedorUpdate, ItemQtd, ListaGerarIn, ListaItemUpdate, PedidoCompraIn, RecebimentoIn)
from api.security import requer
from api.services import compras as svc
from api.services import estoque as est
from api.services.dinheiro import fmt, parse_reais
from api.services.parametros import vigentes

router = APIRouter(prefix="/compras", tags=["compras"])
Q2 = Decimal("0.01")


def _txt(v):
    return est.txt(v)


# ---------------------------------------------------------------- fornecedores
@router.get("/fornecedores")
def fornecedores(ativo: Optional[bool] = None, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    sql, params = "SELECT id, nome, contato, telefone, prazo_dias, forma_pagamento, observacao, ativo FROM fornecedor WHERE loja_id = %s", [LOJA_ID]
    if ativo is not None:
        sql, params = sql + " AND ativo = %s", params + [ativo]
    return conn.execute(sql + " ORDER BY nome", params).fetchall()


@router.post("/fornecedores", status_code=201)
def criar_fornecedor(d: FornecedorIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    try:
        r = conn.execute("INSERT INTO fornecedor (loja_id, nome, contato, telefone, prazo_dias, forma_pagamento, observacao, criado_em, criado_por) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, nome, contato, telefone, prazo_dias, forma_pagamento, observacao, ativo",
                         (LOJA_ID, d.nome, d.contato, d.telefone, d.prazo_dias, d.forma_pagamento, d.observacao, agora(), sessao["usuario_id"])).fetchone()
        auditar(conn, sessao, "criar", "fornecedor", r["id"], depois={"nome": d.nome})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


@router.patch("/fornecedores/{fid}")
def alterar_fornecedor(fid: int, d: FornecedorUpdate, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para alterar.")
    if not conn.execute("SELECT 1 FROM fornecedor WHERE id = %s AND loja_id = %s", (fid, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    sets = ", ".join(f"{c} = %s" for c in campos)
    try:
        r = conn.execute(f"UPDATE fornecedor SET {sets} WHERE id = %s RETURNING id, nome, contato, telefone, prazo_dias, forma_pagamento, observacao, ativo", (*campos.values(), fid)).fetchone()
        auditar(conn, sessao, "alterar", "fornecedor", fid, depois=campos)
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return r


def _fornecedor_ativo(conn, fid: int) -> dict:
    f = conn.execute("SELECT id, nome, prazo_dias, forma_pagamento, ativo FROM fornecedor WHERE id = %s AND loja_id = %s", (fid, LOJA_ID)).fetchone()
    if not f or not f["ativo"]:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado ou inativo.")
    return f


@router.get("/precos/{item_id}")
def precos(item_id: int, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    """Histórico de preço pago do item, por fornecedor."""
    est.config_item(conn, LOJA_ID, item_id)
    return [r | {"preco_unit": _txt(r["preco_unit"]), "quantidade": _txt(r["quantidade"])} for r in conn.execute(
        "SELECT p.data, f.nome AS fornecedor, p.preco_unit, p.quantidade FROM preco_compra p LEFT JOIN fornecedor f ON f.id = p.fornecedor_id "
        "WHERE p.item_id = %s ORDER BY p.id DESC LIMIT 100", (item_id,)).fetchall()]


# ---------------------------------------------------------------- lista de necessidades
def _lista(conn, lid: int, travar=False) -> dict:
    r = conn.execute("SELECT * FROM lista_compra WHERE id = %s AND loja_id = %s" + (" FOR UPDATE" if travar else ""), (lid, LOJA_ID)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Lista de compras não encontrada.")
    return r


def _exigir_edicao(l: dict) -> None:
    if l["situacao"] not in ("rascunho", "cotando"):
        raise HTTPException(status_code=409, detail=f"A lista está {l['situacao']}: os itens não mudam mais.")


@router.get("/necessidades")
def previa(sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    """Pré-visualização do que o sistema sugere comprar agora, sem criar lista."""
    out = []
    for s in svc.sugestoes(conn, LOJA_ID, agora().date()):
        c = est.config_item(conn, LOJA_ID, s["item_id"])
        out.append({**s, "item": c["nome"], "unidade": c["unidade"], "quantidade": _txt(s["quantidade"]), "saldo": _txt(s["saldo"])})
    return out


@router.post("/listas", status_code=201)
def criar_lista(d: ListaGerarIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    quando = agora()
    linhas = {}
    if d.incluir_sugeridos:
        for s in svc.sugestoes(conn, LOJA_ID, quando.date()):
            linhas[s["item_id"]] = (s["quantidade"], s["quantidade"], s["origem"])
    for x in d.itens:
        if not conn.execute("SELECT 1 FROM item WHERE id = %s AND loja_id = %s AND ativo", (x.item_id, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Há item inexistente ou inativo na lista.")
        sug = linhas.get(x.item_id)
        linhas[x.item_id] = (Decimal(x.quantidade), sug[1] if sug else None, sug[2] if sug else "manual")
    if not linhas:
        raise HTTPException(status_code=400, detail="Nada para comprar: não há itens abaixo do mínimo e nenhum item foi acrescentado.")
    try:
        l = conn.execute("INSERT INTO lista_compra (loja_id, observacao, criado_por, criado_em) VALUES (%s,%s,%s,%s) RETURNING id", (LOJA_ID, d.observacao, sessao["usuario_id"], quando)).fetchone()
        for item_id, (qtd, sug, origem) in linhas.items():
            conn.execute("INSERT INTO lista_compra_item (lista_id, item_id, quantidade, sugerida, origem) VALUES (%s,%s,%s,%s,%s)", (l["id"], item_id, qtd, sug, origem))
        auditar(conn, sessao, "criar", "lista_compra", l["id"], depois={"itens": len(linhas)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, l["id"])


@router.get("/listas")
def listas(sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    return [r | {"total": fmt(r["total"])} for r in conn.execute(
        "SELECT l.id, l.situacao, l.criado_em, l.total, (SELECT count(*) FROM lista_compra_item i WHERE i.lista_id = l.id AND NOT i.removido) AS itens "
        "FROM lista_compra l WHERE l.loja_id = %s ORDER BY l.id DESC LIMIT 50", (LOJA_ID,)).fetchall()]


def _detalhe(conn, lid: int) -> dict:
    l = _lista(conn, lid)
    itens = []
    for i in conn.execute("SELECT i.id, i.item_id, it.nome AS item, it.unidade, i.quantidade, i.sugerida, i.origem, i.removido, i.motivo FROM lista_compra_item i "
                          "JOIN item it ON it.id = i.item_id WHERE i.lista_id = %s ORDER BY it.nome", (lid,)).fetchall():
        c = est.config_item(conn, LOJA_ID, i["item_id"])
        cot = conn.execute("SELECT DISTINCT ON (c.fornecedor_id) c.fornecedor_id, f.nome AS fornecedor, c.preco_embalagem, c.preco_unit, c.prazo_dias, c.condicao, c.criado_em "
                           "FROM cotacao_resposta c JOIN fornecedor f ON f.id = c.fornecedor_id WHERE c.lista_item_id = %s ORDER BY c.fornecedor_id, c.id DESC", (i["id"],)).fetchall()
        cot = sorted(cot, key=lambda x: x["preco_unit"])
        itens.append({**{k: i[k] for k in ("id", "item_id", "item", "unidade", "origem", "removido", "motivo")}, "quantidade": _txt(i["quantidade"]), "sugerida": _txt(i["sugerida"]),
                      "saldo": _txt(est.saldo_item(conn, i["item_id"])), "unidade_compra": c["unidade_compra"], "fator_compra": _txt(c["fator_compra"]),
                      "fornecedor_habitual_id": c["fornecedor_habitual_id"],
                      "cotacoes": [x | {"preco_embalagem": _txt(x["preco_embalagem"]), "preco_unit": _txt(x["preco_unit"])} for x in cot],
                      "ultimos_precos": [{"preco_unit": _txt(p["preco_unit"]), "data": p["data"], "fornecedor": p["fornecedor"]} for p in svc.ultimos_precos(conn, i["item_id"])]})
    esc = conn.execute("SELECT e.id, e.lista_item_id, e.fornecedor_id, f.nome AS fornecedor, e.quantidade, e.preco_unit, e.origem_preco, e.valor FROM lista_compra_escolha e "
                       "JOIN fornecedor f ON f.id = e.fornecedor_id WHERE e.lista_id = %s ORDER BY e.id", (lid,)).fetchall()
    pedidos = conn.execute("SELECT id, fornecedor_id, total FROM pedido_compra WHERE lista_id = %s ORDER BY id", (lid,)).fetchall()
    return {**{k: l[k] for k in ("id", "situacao", "observacao", "criado_em", "definida_em", "aprovada_em", "definida_por", "aprovada_por")}, "total": fmt(l["total"]), "itens": itens,
            "escolhas": [e | {"quantidade": _txt(e["quantidade"]), "preco_unit": _txt(e["preco_unit"]), "valor": fmt(e["valor"])} for e in esc],
            "pedidos": [p | {"total": fmt(p["total"])} for p in pedidos]}


@router.get("/listas/{lid}")
def ver_lista(lid: int, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    return _detalhe(conn, lid)


@router.post("/listas/{lid}/itens", status_code=201)
def acrescentar(lid: int, d: ItemQtd, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    """Item avulso: só item já cadastrado (o gerente cadastra o novo antes)."""
    _exigir_edicao(_lista(conn, lid, travar=True))
    if not conn.execute("SELECT 1 FROM item WHERE id = %s AND loja_id = %s AND ativo", (d.item_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Item não encontrado ou inativo.")
    try:
        conn.execute("INSERT INTO lista_compra_item (lista_id, item_id, quantidade, origem) VALUES (%s,%s,%s,'manual')", (lid, d.item_id, Decimal(d.quantidade)))
        auditar(conn, sessao, "acrescentar", "lista_compra", lid, depois={"item_id": d.item_id, "quantidade": d.quantidade})
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Este item já está na lista: ajuste a quantidade.")
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, lid)


@router.patch("/listas/{lid}/itens/{liid}")
def ajustar(lid: int, liid: int, d: ListaItemUpdate, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    """Ajusta quantidade ou remove. O que o sistema sugeriu só sai ou muda com motivo."""
    _exigir_edicao(_lista(conn, lid, travar=True))
    i = conn.execute("SELECT * FROM lista_compra_item WHERE id = %s AND lista_id = %s", (liid, lid)).fetchone()
    if not i:
        raise HTTPException(status_code=404, detail="Item da lista não encontrado.")
    campos = d.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=400, detail="Nada para alterar.")
    muda = ("quantidade" in campos and Decimal(campos["quantidade"]) != i["quantidade"]) or campos.get("removido") is True
    if muda and i["origem"] != "manual" and not campos.get("motivo"):
        raise HTTPException(status_code=400, detail="Informe o motivo de mudar ou tirar um item sugerido pelo sistema.")
    novo = {"quantidade": Decimal(campos["quantidade"]) if "quantidade" in campos else i["quantidade"], "removido": campos.get("removido", i["removido"]),
            "motivo": campos.get("motivo", i["motivo"])}
    try:
        conn.execute("UPDATE lista_compra_item SET quantidade = %s, removido = %s, motivo = %s WHERE id = %s", (novo["quantidade"], novo["removido"], novo["motivo"], liid))
        conn.execute("DELETE FROM lista_compra_escolha WHERE lista_id = %s AND lista_item_id = %s", (lid, liid))
        auditar(conn, sessao, "ajustar", "lista_compra", lid, antes={"quantidade": str(i["quantidade"]), "removido": i["removido"]}, depois={"quantidade": str(novo["quantidade"]), "removido": novo["removido"], "motivo": novo["motivo"]})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, lid)


@router.get("/listas/{lid}/por-fornecedor")
def por_fornecedor(lid: int, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    """Texto pronto para copiar ou imprimir e pedir preço (WhatsApp, telefone). A cotação é registrada à mão."""
    l = _detalhe(conn, lid)
    linhas = [f"- {i['item']}: {i['quantidade']} {i['unidade']}" + (f" (compra em {i['unidade_compra']}, {i['fator_compra']} por {i['unidade_compra']})" if i["unidade_compra"] else "")
              for i in l["itens"] if not i["removido"]]
    return {"lista_id": lid, "texto": "Pedido de cotação\n" + "\n".join(linhas), "itens": len(linhas)}


@router.post("/listas/{lid}/cotacoes", status_code=201)
def cotar(lid: int, d: CotacaoIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    l = _lista(conn, lid, travar=True)
    _exigir_edicao(l)
    i = conn.execute("SELECT item_id, removido FROM lista_compra_item WHERE id = %s AND lista_id = %s", (d.lista_item_id, lid)).fetchone()
    if not i or i["removido"]:
        raise HTTPException(status_code=404, detail="Item da lista não encontrado.")
    _fornecedor_ativo(conn, d.fornecedor_id)
    fator, unit = svc.converter_preco(conn, LOJA_ID, i["item_id"], Decimal(d.preco))
    try:
        conn.execute("INSERT INTO cotacao_resposta (lista_item_id, fornecedor_id, preco_embalagem, fator, preco_unit, prazo_dias, condicao, usuario_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (d.lista_item_id, d.fornecedor_id, Decimal(d.preco), fator, unit, d.prazo_dias, d.condicao, sessao["usuario_id"], agora()))
        if l["situacao"] == "rascunho":
            conn.execute("UPDATE lista_compra SET situacao = 'cotando' WHERE id = %s", (lid,))
        auditar(conn, sessao, "cotar", "lista_compra", lid, depois={"item_id": i["item_id"], "fornecedor_id": d.fornecedor_id, "preco": d.preco})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, lid)


@router.get("/listas/{lid}/mapa")
def mapa(lid: int, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    """Por item: o que cada fornecedor cotou, o mais barato, o último preço pago e os 3 últimos (tendência)."""
    out = []
    for i in _detalhe(conn, lid)["itens"]:
        if i["removido"]:
            continue
        mais_barato = i["cotacoes"][0] if i["cotacoes"] else None
        out.append({"lista_item_id": i["id"], "item": i["item"], "unidade": i["unidade"], "quantidade": i["quantidade"], "cotacoes": i["cotacoes"],
                    "mais_barato": mais_barato["fornecedor_id"] if mais_barato else None, "ultimos_precos": i["ultimos_precos"]})
    return out


def _limite_aprovacao(conn):
    v = vigentes(conn, LOJA_ID)["compra_valor_aprovacao"]["valor"]
    return Decimal(v) if v is not None else None


def _gerar_pedidos(conn, l: dict, quando, usuario_id) -> list[int]:
    ids = []
    for f in conn.execute("SELECT DISTINCT fornecedor_id FROM lista_compra_escolha WHERE lista_id = %s ORDER BY fornecedor_id", (l["id"],)).fetchall():
        forn = conn.execute("SELECT prazo_dias, forma_pagamento FROM fornecedor WHERE id = %s", (f["fornecedor_id"],)).fetchone()
        itens = conn.execute("SELECT i.item_id, sum(e.quantidade) AS q, sum(e.valor) AS v FROM lista_compra_escolha e JOIN lista_compra_item i ON i.id = e.lista_item_id "
                             "WHERE e.lista_id = %s AND e.fornecedor_id = %s GROUP BY i.item_id", (l["id"], f["fornecedor_id"])).fetchall()
        total = sum((x["v"] for x in itens), Decimal("0.00"))
        p = conn.execute("INSERT INTO pedido_compra (loja_id, lista_id, fornecedor_id, prazo_dias, forma_pagamento, total, criado_por, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, l["id"], f["fornecedor_id"], forn["prazo_dias"], forn["forma_pagamento"], total, usuario_id, quando)).fetchone()
        for x in itens:
            conn.execute("INSERT INTO pedido_compra_item (pedido_id, item_id, quantidade, preco_unit) VALUES (%s,%s,%s,%s)", (p["id"], x["item_id"], x["q"], (x["v"] / x["q"]).quantize(Decimal("0.000001"))))
        ids.append(p["id"])
    return ids


@router.post("/listas/{lid}/definir")
def definir(lid: int, d: DefinirIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    """Escolhe o fornecedor de cada item (pode dividir um item entre fornecedores). Abaixo do valor de aprovação, o próprio comprador aprova."""
    l = _lista(conn, lid, travar=True)
    _exigir_edicao(l)
    itens = {i["id"]: i for i in conn.execute("SELECT * FROM lista_compra_item WHERE lista_id = %s AND NOT removido", (lid,)).fetchall()}
    por_item: dict = {}
    linhas = []
    for e in d.escolhas:
        i = itens.get(e.lista_item_id)
        if not i:
            raise HTTPException(status_code=400, detail="Há escolha para item que não está na lista.")
        _fornecedor_ativo(conn, e.fornecedor_id)
        qtd = Decimal(e.quantidade)
        por_item[i["id"]] = por_item.get(i["id"], Decimal(0)) + qtd
        if e.preco is not None:
            _, unit = svc.converter_preco(conn, LOJA_ID, i["item_id"], Decimal(e.preco))
            origem = "manual"
        else:
            cot = conn.execute("SELECT preco_unit FROM cotacao_resposta WHERE lista_item_id = %s AND fornecedor_id = %s ORDER BY id DESC LIMIT 1", (i["id"], e.fornecedor_id)).fetchone()
            if cot:
                unit, origem = cot["preco_unit"], "cotacao"
            elif est.config_item(conn, LOJA_ID, i["item_id"])["fornecedor_habitual_id"] == e.fornecedor_id and svc.ultimo_preco(conn, i["item_id"], e.fornecedor_id):
                unit, origem = svc.ultimo_preco(conn, i["item_id"], e.fornecedor_id), "habitual"
            else:
                raise HTTPException(status_code=400, detail=f"Sem preço para {est.config_item(conn, LOJA_ID, i['item_id'])['nome']} neste fornecedor: cote ou informe o preço.")
        linhas.append((i, e.fornecedor_id, qtd, unit, origem))
    for iid, i in itens.items():
        if por_item.get(iid) != i["quantidade"]:
            raise HTTPException(status_code=400, detail=f"A soma das quantidades de {est.config_item(conn, LOJA_ID, i['item_id'])['nome']} precisa ser {_txt(i['quantidade'])}.")
    quando = agora()
    total = sum(((q * u).quantize(Q2) for _, _, q, u, _ in linhas), Decimal("0.00"))
    limite = _limite_aprovacao(conn)
    auto = limite is None or total <= limite
    try:
        conn.execute("DELETE FROM lista_compra_escolha WHERE lista_id = %s", (lid,))
        for i, forn, q, u, o in linhas:
            conn.execute("INSERT INTO lista_compra_escolha (lista_id, lista_item_id, fornecedor_id, quantidade, preco_unit, origem_preco, valor) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                         (lid, i["id"], forn, q, u, o, (q * u).quantize(Q2)))
        conn.execute("UPDATE lista_compra SET situacao = 'definida', total = %s, definida_por = %s, definida_em = %s WHERE id = %s", (total, sessao["usuario_id"], quando, lid))
        if auto:
            conn.execute("UPDATE lista_compra SET situacao = 'aprovada', aprovada_por = %s, aprovada_em = %s WHERE id = %s", (sessao["usuario_id"], quando, lid))
            _gerar_pedidos(conn, _lista(conn, lid), quando, sessao["usuario_id"])
        auditar(conn, sessao, "definir", "lista_compra", lid, depois={"total": fmt(total), "aprovada_direto": auto})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, lid)


@router.post("/listas/{lid}/aprovar")
def aprovar(lid: int, sessao=Depends(requer("compras.aprovar")), conn=Depends(get_db)):
    """Lista acima do valor de aprovação: outra pessoa, que não montou a lista, aprova e os pedidos saem."""
    l = _lista(conn, lid, travar=True)
    if l["situacao"] != "definida":
        raise HTTPException(status_code=409, detail="Só lista definida espera aprovação.")
    if l["definida_por"] == sessao["usuario_id"]:
        raise HTTPException(status_code=403, detail="Quem montou a lista não aprova a própria compra acima do limite.")
    quando = agora()
    try:
        conn.execute("UPDATE lista_compra SET situacao = 'aprovada', aprovada_por = %s, aprovada_em = %s WHERE id = %s", (sessao["usuario_id"], quando, lid))
        ids = _gerar_pedidos(conn, _lista(conn, lid), quando, sessao["usuario_id"])
        auditar(conn, sessao, "aprovar", "lista_compra", lid, depois={"pedidos": ids})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _detalhe(conn, lid)


@router.post("/listas/{lid}/cancelar")
def cancelar_lista(lid: int, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    l = _lista(conn, lid, travar=True)
    if l["situacao"] in ("aprovada", "cancelada"):
        raise HTTPException(status_code=409, detail=f"Lista {l['situacao']} não pode ser cancelada.")
    conn.execute("UPDATE lista_compra SET situacao = 'cancelada' WHERE id = %s", (lid,))
    auditar(conn, sessao, "cancelar", "lista_compra", lid)
    conn.commit()
    return _detalhe(conn, lid)


# ---------------------------------------------------------------- pedidos de compra
def _pedido_out(conn, pid: int) -> dict:
    p = conn.execute("SELECT p.id, p.lista_id, p.fornecedor_id, f.nome AS fornecedor, p.situacao, p.prazo_dias, p.forma_pagamento, p.previsao_entrega, p.total, p.observacao, p.criado_em "
                     "FROM pedido_compra p JOIN fornecedor f ON f.id = p.fornecedor_id WHERE p.id = %s AND p.loja_id = %s", (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido de compra não encontrado.")
    itens = conn.execute("SELECT i.item_id, it.nome AS item, it.unidade, i.quantidade, i.preco_unit, "
                         "COALESCE((SELECT sum(r.quantidade) FROM recebimento_item r JOIN recebimento rc ON rc.id = r.recebimento_id WHERE rc.pedido_id = i.pedido_id AND r.item_id = i.item_id), 0) AS recebido "
                         "FROM pedido_compra_item i JOIN item it ON it.id = i.item_id WHERE i.pedido_id = %s ORDER BY it.nome", (pid,)).fetchall()
    return {**p, "total": fmt(p["total"]), "itens": [i | {"quantidade": _txt(i["quantidade"]), "preco_unit": _txt(i["preco_unit"]), "recebido": _txt(i["recebido"])} for i in itens]}


@router.get("/pedidos")
def pedidos(situacao: Optional[str] = None, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    sql, params = ("SELECT p.id, f.nome AS fornecedor, p.situacao, p.total, p.criado_em FROM pedido_compra p JOIN fornecedor f ON f.id = p.fornecedor_id WHERE p.loja_id = %s"), [LOJA_ID]
    if situacao:
        sql, params = sql + " AND p.situacao = %s", params + [situacao]
    return [r | {"total": fmt(r["total"])} for r in conn.execute(sql + " ORDER BY p.id DESC LIMIT 100", params).fetchall()]


@router.get("/pedidos/{pid}")
def ver_pedido(pid: int, sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    return _pedido_out(conn, pid)


@router.post("/pedidos", status_code=201)
def criar_pedido(d: PedidoCompraIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    """Pedido digitado direto, sem lista. Acima do valor de aprovação, só quem tem poder de aprovar emite (todos os compradores têm, por ora)."""
    forn = _fornecedor_ativo(conn, d.fornecedor_id)
    linhas = []
    for x in d.itens:
        if not conn.execute("SELECT 1 FROM item WHERE id = %s AND loja_id = %s AND ativo", (x.item_id, LOJA_ID)).fetchone():
            raise HTTPException(status_code=404, detail="Há item inexistente ou inativo no pedido.")
        _, unit = svc.converter_preco(conn, LOJA_ID, x.item_id, Decimal(x.preco))
        linhas.append((x.item_id, Decimal(x.quantidade), unit))
    total = sum(((q * u).quantize(Q2) for _, q, u in linhas), Decimal("0.00"))
    try:
        p = conn.execute("INSERT INTO pedido_compra (loja_id, fornecedor_id, prazo_dias, forma_pagamento, previsao_entrega, total, observacao, criado_por, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.fornecedor_id, d.prazo_dias if d.prazo_dias is not None else forn["prazo_dias"], d.forma_pagamento or forn["forma_pagamento"], d.previsao_entrega,
                          total, d.observacao, sessao["usuario_id"], agora())).fetchone()
        for item_id, q, u in linhas:
            conn.execute("INSERT INTO pedido_compra_item (pedido_id, item_id, quantidade, preco_unit) VALUES (%s,%s,%s,%s)", (p["id"], item_id, q, u))
        auditar(conn, sessao, "criar", "pedido_compra", p["id"], depois={"total": fmt(total)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return _pedido_out(conn, p["id"])


@router.post("/pedidos/{pid}/cancelar")
def cancelar_pedido(pid: int, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    p = conn.execute("SELECT situacao FROM pedido_compra WHERE id = %s AND loja_id = %s FOR UPDATE", (pid, LOJA_ID)).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido de compra não encontrado.")
    if p["situacao"] != "emitido":
        raise HTTPException(status_code=409, detail=f"Pedido {p['situacao']} não pode ser cancelado.")
    conn.execute("UPDATE pedido_compra SET situacao = 'cancelado' WHERE id = %s", (pid,))
    auditar(conn, sessao, "cancelar", "pedido_compra", pid)
    conn.commit()
    return _pedido_out(conn, pid)


# ---------------------------------------------------------------- recebimento e entrada da nota
@router.get("/recebimentos")
def recebimentos(sessao=Depends(requer("compras.ver")), conn=Depends(get_db)):
    return [r | {"total_nota": fmt(r["total_nota"])} for r in conn.execute(
        "SELECT r.id, f.nome AS fornecedor, r.numero_nota, r.data_nota, r.total_nota, r.vencimento, r.pedido_id, r.movimento_caixa_id, c.nome AS conferente "
        "FROM recebimento r JOIN fornecedor f ON f.id = r.fornecedor_id LEFT JOIN usuario c ON c.id = r.conferente_id WHERE r.loja_id = %s ORDER BY r.id DESC LIMIT 100", (LOJA_ID,)).fetchall()]


@router.post("/recebimentos", status_code=201)
def receber(d: RecebimentoIn, sessao=Depends(requer("compras.operar")), conn=Depends(get_db)):
    """Confere a entrega contra o pedido, dá entrada no estoque (lote e custo médio), guarda o preço pago e deixa a nota pronta para Contas a Pagar."""
    quando = agora()
    pedido, itens_pedido, forn_id = None, {}, d.fornecedor_id
    if d.pedido_id is not None:
        pedido = conn.execute("SELECT * FROM pedido_compra WHERE id = %s AND loja_id = %s FOR UPDATE", (d.pedido_id, LOJA_ID)).fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido de compra não encontrado.")
        if pedido["situacao"] not in ("emitido", "parcial"):
            raise HTTPException(status_code=409, detail=f"Pedido {pedido['situacao']}: não recebe mais entrega.")
        forn_id = pedido["fornecedor_id"]
        itens_pedido = {r["item_id"]: r for r in _pedido_out(conn, d.pedido_id)["itens"]}
    if forn_id is None:
        raise HTTPException(status_code=400, detail="Informe o fornecedor (ou o pedido).")
    forn = _fornecedor_ativo(conn, forn_id)
    if d.conferente_id is not None and not conn.execute("SELECT 1 FROM usuario WHERE id = %s AND loja_id = %s AND ativo", (d.conferente_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Conferente não encontrado.")
    linhas, total_itens = [], Decimal("0.00")
    for x in d.itens:
        c = est.config_item(conn, LOJA_ID, x.item_id)
        if not c["ativo"]:
            raise HTTPException(status_code=400, detail=f"{c['nome']} está inativo.")
        qtd = Decimal(x.quantidade)
        fator, unit = svc.converter_preco(conn, LOJA_ID, x.item_id, Decimal(x.preco))
        pedida = None
        if pedido:
            ip = itens_pedido.get(x.item_id)
            if not ip:
                raise HTTPException(status_code=400, detail=f"{c['nome']} não está neste pedido.")
            pedida = Decimal(ip["quantidade"]) - Decimal(ip["recebido"])
            if (qtd != pedida or abs(unit - Decimal(ip["preco_unit"])) > Decimal("0.001")) and not x.diferenca_motivo:
                raise HTTPException(status_code=400, detail=f"{c['nome']}: quantidade ou preço diferente do pedido, informe o motivo da diferença.")
        valor = (qtd * unit).quantize(Q2)
        total_itens += valor
        linhas.append((c, qtd, unit, valor, pedida, x))
    frete = parse_reais(d.frete) if d.frete is not None else Decimal("0.00")
    desconto = parse_reais(d.desconto) if d.desconto is not None else Decimal("0.00")
    total = total_itens + frete - desconto
    if total < 0:
        raise HTTPException(status_code=400, detail="O desconto não pode passar do valor da nota.")
    forma = d.forma_pagamento or (pedido["forma_pagamento"] if pedido else None) or forn["forma_pagamento"]
    prazo = pedido["prazo_dias"] if pedido and pedido["prazo_dias"] is not None else forn["prazo_dias"]
    venc = d.vencimento or (d.data_nota + timedelta(days=prazo) if prazo is not None else None)
    if d.movimento_caixa_id is not None:  # compra urgente paga com o dinheiro do caixa
        s = conn.execute("SELECT tipo, valor FROM movimento_caixa WHERE id = %s AND loja_id = %s", (d.movimento_caixa_id, LOJA_ID)).fetchone()
        if not s or s["tipo"] != "sangria":
            raise HTTPException(status_code=404, detail="Sangria não encontrada.")
        if s["valor"] != total:
            raise HTTPException(status_code=400, detail=f"A sangria é de R$ {fmt(s['valor'])} e a nota de R$ {fmt(total)}: os valores precisam ser iguais.")
        forma, venc = "dinheiro", d.data_nota
    try:
        r = conn.execute("INSERT INTO recebimento (loja_id, pedido_id, fornecedor_id, numero_nota, data_nota, conferente_id, frete, desconto, total_nota, forma_pagamento, vencimento, movimento_caixa_id, observacao, criado_por, criado_em) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                         (LOJA_ID, d.pedido_id, forn_id, d.numero_nota, d.data_nota, d.conferente_id or sessao["usuario_id"], frete, desconto, total, forma, venc,
                          d.movimento_caixa_id, d.observacao, sessao["usuario_id"], quando)).fetchone()
        for c, qtd, unit, valor, pedida, x in sorted(linhas, key=lambda t: t[0]["id"]):  # ordem fixa nos locks de item
            mov = est.entrada(conn, LOJA_ID, c["id"], qtd, unit, "entrada_compra", sessao["usuario_id"], quando, origem=("recebimento", r["id"]),
                              lote_codigo=x.lote_codigo, validade=x.validade, fornecedor_origem="compra")
            conn.execute("INSERT INTO recebimento_item (recebimento_id, item_id, quantidade_pedida, quantidade, preco_unit, valor, lote_codigo, validade, diferenca_motivo, movimento_estoque_id) "
                         "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (r["id"], c["id"], pedida, qtd, unit, valor, x.lote_codigo, x.validade, x.diferenca_motivo, mov))
            conn.execute("INSERT INTO preco_compra (loja_id, item_id, fornecedor_id, preco_unit, quantidade, data, recebimento_id, criado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                         (LOJA_ID, c["id"], forn_id, unit, qtd, d.data_nota, r["id"], quando))
        if pedido:
            ped = _pedido_out(conn, d.pedido_id)
            completo = all(Decimal(i["recebido"]) >= Decimal(i["quantidade"]) for i in ped["itens"])
            conn.execute("UPDATE pedido_compra SET situacao = %s WHERE id = %s", ("recebido" if completo else "parcial", d.pedido_id))
        auditar(conn, sessao, "receber", "recebimento", r["id"], depois={"fornecedor_id": forn_id, "total": fmt(total), "itens": len(linhas)})
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        raise traduzir_erro(e) from e
    return {"id": r["id"], "total_nota": fmt(total), "vencimento": venc, "forma_pagamento": forma}
