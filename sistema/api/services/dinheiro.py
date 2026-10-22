"""Valores em reais: entrada em texto (ponto ou vírgula, até 2 casas), cálculo em Decimal, saída em texto com 2 casas."""
import re
from decimal import ROUND_CEILING, Decimal

_REAIS = re.compile(r"^[0-9]{1,8}([.,][0-9]{1,2})?$")
CENTAVO = Decimal("0.01")


def parse_reais(texto: str) -> Decimal:
    """Texto como "35", "35,5" ou "35.50" vira Decimal com 2 casas. Recusa sinal, expoente, espaço e dígitos não ASCII."""
    if not isinstance(texto, str) or not _REAIS.match(texto.strip()):
        raise ValueError("Valor em reais inválido. Use números, com ponto ou vírgula e até 2 casas.")
    return Decimal(texto.strip().replace(",", ".")).quantize(CENTAVO)


def fmt(v) -> str | None:
    return None if v is None else format(Decimal(v).quantize(CENTAVO), "f")


def metade_para_cima(v: Decimal) -> Decimal:
    """Metade de um valor, arredondada para cima ao centavo (regra T4 do desenho técnico)."""
    return (Decimal(v) / 2).quantize(CENTAVO, rounding=ROUND_CEILING)
