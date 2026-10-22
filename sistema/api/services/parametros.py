"""
Catálogo de parâmetros da loja e validação dos valores.
Valor guardado como texto; a regra de cada chave fica aqui, não espalhada nas telas.
Limites iniciais ficam vazios até Marlon definir (decisão de 16/10/2026).
"""
import json
import re
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

FORMAS_PAGAMENTO = ("dinheiro", "pix", "credito", "debito")
REGIMES = ("mei", "simples_nacional", "lucro_presumido", "lucro_real")

# chave: (tipo, padrão, descrição)
CATALOGO = {
    "loja_nome": ("texto", None, "Nome da loja"),
    "regime_tributario": ("regime", None, "Regime tributário da loja"),
    "formas_pagamento_aceitas": ("formas", list(FORMAS_PAGAMENTO), "Formas de pagamento aceitas"),
    "limite_desconto_atendente_pct": ("pct", None, "Limite de desconto do atendente (%)"),
    "limite_desconto_subgerente_pct": ("pct", None, "Limite de desconto do subgerente (%)"),
    "limite_desconto_gerente_pct": ("pct", None, "Limite de desconto do gerente (%)"),
    "valor_entrega_padrao": ("dinheiro", None, "Valor padrão por entrega paga ao entregador (R$)"),
    "diaria_entregador_padrao": ("dinheiro", None, "Valor padrão da diária do entregador (R$)"),
    "fundo_troco_padrao": ("dinheiro", None, "Fundo de troco padrão na abertura do caixa (R$)"),
    "tolerancia_diferenca_caixa": ("dinheiro", None, "Tolerância de diferença no fechamento do caixa (R$)"),
    "sangria_limite_gerente": ("dinheiro", None, "Valor de sangria ou suprimento acima do qual o gerente autoriza (R$)"),
    "taxa_entrega_padrao": ("dinheiro", None, "Taxa de entrega cobrada do cliente (R$)"),
    "calzone_massa_tamanho": ("tamanho_massa", None, "Tamanho de massa que o calzone consome (grande ou broto)"),
    "producao_montagem_min": ("decimal_pos", None, "Minutos para um pizzaiolo montar uma pizza (estimativa de entrega)"),
    "producao_pizzaiolos_ativos": ("inteiro_pos", None, "Pizzaiolos trabalhando ao mesmo tempo (estimativa de entrega)"),
    "producao_acabamento_min": ("decimal_pos", None, "Minutos de acabamento e embalagem por pedido (estimativa de entrega)"),
    "entrega_deslocamento_min": ("decimal_pos", None, "Minutos de deslocamento da entrega (estimativa de entrega)"),
    "perda_padrao_pct": ("pct", "10", "Perda padrão (%) de cada insumo nas fichas técnicas"),
    "forno_tempo_min": ("decimal_pos", "2", "Tempo de forno por pizza (minutos)"),
    "forno_pizzas_por_vez": ("inteiro_pos", None, "Pizzas que o forno comporta por vez"),
}


_NUMERO = re.compile(r"^[0-9]{1,9}([.,][0-9]{1,6})?$")


def descrever() -> list[dict]:
    return [{"chave": k, "tipo": t, "descricao": d} for k, (t, _, d) in CATALOGO.items()]


def _dec(texto: str, minimo: Decimal, maximo: Decimal | None = None) -> Decimal:
    if not _NUMERO.match(texto):  # só dígitos ASCII, com ponto ou vírgula decimal
        raise ValueError("Número inválido.")
    try:
        v = Decimal(texto.replace(",", "."))
    except InvalidOperation:
        raise ValueError("Número inválido.")
    if not v.is_finite() or v < minimo or (maximo is not None and v > maximo):
        raise ValueError("Valor fora da faixa permitida.")
    return v


def normalizar(chave: str, valor) -> str | None:
    """Valida o valor da chave e devolve o texto a guardar. HTTPException 400/404 em caso de erro."""
    if chave not in CATALOGO:
        raise HTTPException(status_code=404, detail="Parâmetro desconhecido.")
    if valor is None or valor == "" or valor == []:
        return None
    tipo = CATALOGO[chave][0]
    try:
        if tipo == "formas":
            if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
                raise ValueError("Informe a lista de formas de pagamento.")
            if any(x not in FORMAS_PAGAMENTO for x in valor) or len(set(valor)) != len(valor):
                raise ValueError("Forma de pagamento inválida ou repetida.")
            return json.dumps(sorted(valor, key=FORMAS_PAGAMENTO.index))
        if not isinstance(valor, str):
            raise ValueError("Valor deve ser texto ou número em texto.")
        if tipo == "texto":
            if len(valor) > 120:
                raise ValueError("Até 120 caracteres.")
            return valor.strip()
        if tipo == "regime":
            if valor not in REGIMES:
                raise ValueError("Regime inválido.")
            return valor
        if tipo == "pct":
            return str(_dec(valor, Decimal(0), Decimal(100)).quantize(Decimal("0.01")))
        if tipo == "dinheiro":
            return str(_dec(valor, Decimal(0), Decimal("999999.99")).quantize(Decimal("0.01")))
        if tipo == "tamanho_massa":
            if valor not in ("grande", "broto"):
                raise ValueError("Informe grande ou broto.")
            return valor
        if tipo == "decimal_pos":
            return format(_dec(valor, Decimal("0.1"), Decimal(1000)).normalize(), "f")
        if tipo == "inteiro_pos":
            d = _dec(valor, Decimal(1), Decimal(1000))
            if d != d.to_integral_value():
                raise ValueError("Informe um número inteiro.")
            return str(int(d))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=400, detail="Tipo de parâmetro não suportado.")


def vigentes(conn, loja_id: int) -> dict[str, dict]:
    """Valor atual de cada chave: o último registro, ou o padrão do catálogo quando nunca alterado."""
    linhas = conn.execute(
        "SELECT DISTINCT ON (chave) chave, valor, vigente_desde FROM parametro WHERE loja_id = %s "
        "ORDER BY chave, id DESC", (loja_id,)).fetchall()
    gravados = {r["chave"]: r for r in linhas}
    saida = {}
    for chave, (tipo, padrao, desc) in CATALOGO.items():
        if chave in gravados and gravados[chave]["valor"] is not None:
            bruto, desde = gravados[chave]["valor"], gravados[chave]["vigente_desde"]
        else:  # nunca alterado ou limpo: vale o padrão do catálogo (que pode ser "não definido")
            bruto, desde = (json.dumps(padrao) if tipo == "formas" and padrao else padrao), None
        valor = json.loads(bruto) if (tipo == "formas" and bruto) else bruto
        saida[chave] = {"chave": chave, "tipo": tipo, "descricao": desc, "valor": valor,
                        "vigente_desde": desde, "definido": desde is not None}
    return saida
