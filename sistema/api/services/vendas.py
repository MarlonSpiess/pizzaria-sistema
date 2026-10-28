"""
Regras de venda: preço dos itens, ajuste com limite por perfil, pagamento dividido com troco só em dinheiro
e autorização de gerente na hora. Tudo em Decimal; o router só orquestra.
"""
from decimal import Decimal

from fastapi import HTTPException, Request

from api.config import LOJA_ID
from api.security import (SENHA_DUMMY_HASH, exigir_login_liberado, ip_cliente, limpar_falhas_login, registrar_falha_login,
                          verificar_senha)
from api.services.dinheiro import CENTAVO, fmt, parse_reais
from api.services.parametros import vigentes
from api.services.preco import calcular_pizza

SITUACOES = ("recebido", "em producao", "acabado", "despachado ou retirado")
AUTORIZADORES = ("gerente", "subgerente", "proprietario", "administrador")
_LIMITE = {"atendente": "limite_desconto_atendente_pct", "subgerente": "limite_desconto_subgerente_pct",
           "gerente": "limite_desconto_gerente_pct"}
_RECUSADA = "Autorização recusada: confira usuário e senha de gerente e se o desconto cabe no limite dele."
_ROTULO_TIPO = {"calzone": "Calzone", "bebida": "Bebida", "acompanhamento": "Acompanhamento"}


def limite_desconto(conn, loja_id: int, perfil: str):
    """Percentual máximo de desconto do perfil. None = sem limite (administrador e proprietário).
    Limite não definido nos parâmetros vale 0: qualquer desconto exige autorização até Marlon definir."""
    if perfil in ("administrador", "proprietario"):
        return None
    chave = _LIMITE.get(perfil)
    if not chave:
        return Decimal(0)
    valor = vigentes(conn, loja_id)[chave]["valor"]
    return Decimal(valor) if valor is not None else Decimal(0)


def precificar_item(conn, loja_id: int, it) -> dict:
    """Valida o item contra o cardápio e devolve preço unitário, descrição e adicionais com o valor do momento."""
    if it.tipo == "pizza":
        calc = calcular_pizza(conn, loja_id, it.tamanho, it.produto_id, it.sabor2_id, it.adicional_ids)
        nomes = [conn.execute("SELECT nome FROM produto WHERE id = %s", (i,)).fetchone()["nome"]
                 for i in (it.produto_id, it.sabor2_id) if i is not None]
        adicionais = []
        for aid in it.adicional_ids:
            a = conn.execute(
                "SELECT a.id, a.nome, a.tipo, (SELECT valor FROM preco_adicional WHERE adicional_id = a.id AND tamanho = %s "
                "ORDER BY id DESC LIMIT 1) AS valor FROM adicional a WHERE a.id = %s", (it.tamanho, aid)).fetchone()
            adicionais.append(a)
        if sum(1 for a in adicionais if a["tipo"] == "borda") > 1:
            raise HTTPException(status_code=400, detail="Escolha só uma borda por pizza.")
        descricao = f"Pizza {it.tamanho.capitalize()}: " + " + ".join(nomes)
        return {"descricao": descricao, "tamanho": it.tamanho, "preco_unit": Decimal(calc["total"]), "adicionais": adicionais}
    p = conn.execute("SELECT id, nome, tipo, ativo FROM produto WHERE id = %s AND loja_id = %s", (it.produto_id, loja_id)).fetchone()
    if not p or p["tipo"] != it.tipo:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    if not p["ativo"]:
        raise HTTPException(status_code=400, detail=f"{p['nome']} está fora do cardápio.")
    preco = conn.execute("SELECT valor FROM preco_produto WHERE produto_id = %s AND tamanho = 'unico' ORDER BY id DESC LIMIT 1",
                         (p["id"],)).fetchone()
    if not preco:
        raise HTTPException(status_code=400, detail=f"{p['nome']} não tem preço.")
    return {"descricao": f"{_ROTULO_TIPO[it.tipo]}: {p['nome']}", "tamanho": "unico", "preco_unit": preco["valor"], "adicionais": []}


def totais(conn, loja_id: int, d) -> dict:
    """Subtotal, ajuste, taxa e total de um pedido (ou simulação). Não grava nada."""
    itens = [precificar_item(conn, loja_id, it) | {"quantidade": it.quantidade} for it in d.itens]
    subtotal = sum((i["preco_unit"] * i["quantidade"] for i in itens), Decimal("0.00"))
    desconto = acrescimo = Decimal("0.00")
    if d.ajuste:
        v = parse_reais(d.ajuste.valor)
        if d.ajuste.tipo == "desconto":
            if v > subtotal:
                raise HTTPException(status_code=400, detail="O desconto não pode passar do subtotal.")
            desconto = v
        else:
            acrescimo = v
    padrao = vigentes(conn, loja_id)["taxa_entrega_padrao"]["valor"]
    padrao = Decimal(padrao) if padrao is not None else Decimal("0.00")
    if d.tipo == "retirada":
        if d.taxa_entrega is not None and parse_reais(d.taxa_entrega) != 0:
            raise HTTPException(status_code=400, detail="Retirada não tem taxa de entrega.")
        taxa = Decimal("0.00")
    else:
        taxa = parse_reais(d.taxa_entrega) if d.taxa_entrega is not None else padrao
    total = subtotal - desconto + acrescimo + taxa
    pct = (desconto * 100 / subtotal).quantize(Decimal("0.01")) if subtotal > 0 else Decimal("0.00")
    return {"tipo": d.tipo, "itens": itens, "subtotal": subtotal, "desconto": desconto, "acrescimo": acrescimo, "taxa": taxa,
            "taxa_padrao": padrao, "total": total, "desconto_pct": pct}


def repartir_pagamentos(total: Decimal, pagamentos, formas_aceitas: list[str]) -> list[dict]:
    """Pagamento dividido: o líquido soma exatamente o total; só o dinheiro recebe troco (e não maior que o próprio valor)."""
    linhas = []
    for p in pagamentos:
        if p.forma not in formas_aceitas:
            raise HTTPException(status_code=400, detail=f"A forma {p.forma} não está aceita nesta loja.")
        linhas.append({"forma": p.forma, "valor": parse_reais(p.valor), "troco": Decimal("0.00")})
    recebido = sum((l["valor"] for l in linhas), Decimal("0.00"))
    if recebido < total:
        raise HTTPException(status_code=400, detail=f"Pagamento incompleto: faltam R$ {fmt(total - recebido)}.")
    sobra = recebido - total
    for l in linhas:
        if sobra == 0:
            break
        if l["forma"] == "dinheiro":
            t = min(sobra, l["valor"] - CENTAVO) if l["valor"] > CENTAVO else Decimal("0.00")
            l["troco"], sobra = t, sobra - t
    if sobra != 0:
        raise HTTPException(status_code=400, detail="Só o dinheiro gera troco, e o troco não passa do dinheiro recebido.")
    return linhas


def excede_limite(desconto: Decimal, subtotal: Decimal, limite) -> bool:
    """Compara em dinheiro, sem arredondar o percentual: desconto/subtotal > limite/100."""
    return limite is not None and desconto * 100 > subtotal * limite


def autorizar(conn, request: Request, aut, requerente_id: int, desconto: Decimal | None = None, subtotal: Decimal | None = None,
              perfis: tuple = AUTORIZADORES) -> int:
    """Confere login e senha de quem autoriza. Devolve o id do autorizador.
    A trava de tentativas é por quem pede e quem autoriza, não pelo IP: o terminal de um atendente não bloqueia o login do gerente."""
    ip = f"aut:{requerente_id}|{ip_cliente(request)}"
    exigir_login_liberado(conn, ip, aut.usuario)
    u = conn.execute("SELECT id, perfil, senha_hash, ativo, deve_trocar_senha FROM usuario WHERE usuario = %s",
                     (aut.usuario,)).fetchone()
    ok = verificar_senha(aut.senha, u["senha_hash"] if u else SENHA_DUMMY_HASH)
    valido = bool(u and ok and u["ativo"] and not u["deve_trocar_senha"] and u["perfil"] in perfis
                  and u["id"] != requerente_id)
    if not valido:
        registrar_falha_login(conn, ip, aut.usuario)
        raise HTTPException(status_code=403, detail=_RECUSADA)
    if desconto is not None and excede_limite(desconto, subtotal, limite_desconto(conn, LOJA_ID, u["perfil"])):
        registrar_falha_login(conn, ip, aut.usuario)  # mesma resposta e mesma contagem: não vira oráculo de senha
        raise HTTPException(status_code=403, detail=_RECUSADA)
    limpar_falhas_login(conn, ip, aut.usuario)
    return u["id"]
