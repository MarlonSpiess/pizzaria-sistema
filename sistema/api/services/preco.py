"""
Preço da pizza (regra de Marlon, decisões C2 e D1):
- um sabor: preço do sabor no tamanho;
- Grande com dois sabores: metade do preço da Grande de cada sabor, cada metade arredondada para cima ao centavo (T4);
- borda e adicional somam ao item, pelo preço do tamanho.
"""
from decimal import Decimal

from fastapi import HTTPException

from api.services.dinheiro import fmt, metade_para_cima

_PRECO_ATUAL = ("SELECT valor FROM preco_produto WHERE produto_id = p.id AND tamanho = %s ORDER BY id DESC LIMIT 1")


def _sabor(conn, loja_id: int, sabor_id: int, tamanho: str) -> dict:
    s = conn.execute(
        f"SELECT p.id, p.nome, p.ativo, ({_PRECO_ATUAL}) AS valor FROM produto p "
        "WHERE p.id = %s AND p.loja_id = %s AND p.tipo = 'pizza'", (tamanho, sabor_id, loja_id)).fetchone()
    if not s:
        raise HTTPException(status_code=404, detail="Sabor não encontrado.")
    if not s["ativo"]:
        raise HTTPException(status_code=400, detail=f"O sabor {s['nome']} está fora do cardápio.")
    if s["valor"] is None:
        raise HTTPException(status_code=400, detail=f"O sabor {s['nome']} não tem preço para este tamanho.")
    return s


def calcular_pizza(conn, loja_id: int, tamanho: str, sabor1_id: int, sabor2_id, adicional_ids: list[int]) -> dict:
    if sabor2_id is not None:
        if tamanho != "grande":
            raise HTTPException(status_code=400, detail="Só a pizza Grande aceita dois sabores.")
        if sabor2_id == sabor1_id:
            raise HTTPException(status_code=400, detail="Escolha dois sabores diferentes ou só um sabor.")
    s1 = _sabor(conn, loja_id, sabor1_id, tamanho)
    itens, total = [], Decimal("0.00")
    if sabor2_id is not None:
        s2 = _sabor(conn, loja_id, sabor2_id, tamanho)
        for s in (s1, s2):
            metade = metade_para_cima(s["valor"])
            itens.append({"descricao": f"Metade {s['nome']} (Grande {fmt(s['valor']).replace('.', ',')} ÷ 2)", "valor": fmt(metade)})
            total += metade
    else:
        itens.append({"descricao": f"{s1['nome']} ({tamanho})", "valor": fmt(s1["valor"])})
        total += s1["valor"]
    for aid in adicional_ids:
        a = conn.execute(
            "SELECT a.nome, a.ativo, (SELECT valor FROM preco_adicional WHERE adicional_id = a.id AND tamanho = %s "
            "ORDER BY id DESC LIMIT 1) AS valor FROM adicional a WHERE a.id = %s AND a.loja_id = %s",
            (tamanho, aid, loja_id)).fetchone()
        if not a:
            raise HTTPException(status_code=404, detail="Borda ou adicional não encontrado.")
        if not a["ativo"] or a["valor"] is None:
            raise HTTPException(status_code=400, detail=f"{a['nome']} não está disponível.")
        itens.append({"descricao": a["nome"], "valor": fmt(a["valor"])})
        total += a["valor"]
    return {"tamanho": tamanho, "itens": itens, "total": fmt(total)}
