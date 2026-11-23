"""CRAP por função (Savoia e Evans): CRAP = cc² x (1 - cobertura)³ + cc.

cc vem do radon; a cobertura de linhas, do JSON do coverage.py. Uso, a partir de sistema/:
    python -m pytest -q --cov=api --cov=scripts --cov-report=json:cobertura.json
    python tools/crapper.py cobertura.json [limite]
Lista as funções com CRAP acima do limite (padrão 10), da pior para a melhor.
"""
import json
import sys

from radon.complexity import cc_visit


def funcoes(bloco):
    """Funções e métodos do radon (classes entram só pelos métodos)."""
    if hasattr(bloco, "methods"):
        return list(bloco.methods)
    return [bloco]


def crap(cc: int, cobertura: float) -> float:
    return cc ** 2 * (1 - cobertura) ** 3 + cc


def medir(caminho_json: str):
    arquivos = json.load(open(caminho_json, encoding="utf-8"))["files"]
    for arq, d in arquivos.items():
        executadas, faltando = set(d["executed_lines"]), set(d["missing_lines"])
        for bloco in cc_visit(open(arq, encoding="utf-8").read()):
            for f in funcoes(bloco):
                linhas = set(range(f.lineno, f.endline + 1))
                ex, fa = len(linhas & executadas), len(linhas & faltando)
                cob = ex / (ex + fa) if ex + fa else 1.0
                yield crap(f.complexity, cob), f.complexity, cob, f"{arq}:{f.lineno} {f.name}"


def main():
    limite = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    todas = sorted(medir(sys.argv[1]), reverse=True)
    acima = [t for t in todas if t[0] >= limite]
    for valor, cc, cob, nome in acima:
        print(f"CRAP {valor:6.1f}  cc {cc:3d}  cobertura {cob * 100:5.1f}%  {nome}")
    print(f"\n{len(acima)} de {len(todas)} funções com CRAP >= {limite}")


if __name__ == "__main__":
    main()
