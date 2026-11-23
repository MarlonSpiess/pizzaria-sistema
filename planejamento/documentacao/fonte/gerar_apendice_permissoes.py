"""Gera tecnico/Apendice_B_Permissoes_por_Perfil.md a partir de PERMISSOES em sistema/api/security.py.
Uso, na raiz do repositório: python planejamento/documentacao/fonte/gerar_apendice_permissoes.py
Lê o arquivo como texto (não importa o sistema, não precisa de banco)."""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SEC = RAIZ / "sistema" / "api" / "security.py"
SAIDA = Path(__file__).resolve().parents[1] / "tecnico" / "Apendice_B_Permissoes_por_Perfil.md"


def _copia_de_matriz(v):
    if len(v.generators) != 1 or v.generators[0].ifs:
        return False
    g = v.generators[0]
    it, alvo = g.iter, g.target
    if not (isinstance(it, ast.Call) and not it.args and isinstance(it.func, ast.Attribute) and it.func.attr == "items"
            and isinstance(it.func.value, ast.Name)):
        return False
    if not (isinstance(alvo, ast.Tuple) and len(alvo.elts) == 2 and all(isinstance(e, ast.Name) for e in alvo.elts)):
        return False
    k, x = (e.id for e in alvo.elts)
    corpo = v.value
    return (isinstance(v.key, ast.Name) and v.key.id == k and isinstance(corpo, ast.Call) and isinstance(corpo.func, ast.Name)
            and corpo.func.id in ("frozenset", "set") and len(corpo.args) == 1 and isinstance(corpo.args[0], ast.Name)
            and corpo.args[0].id == x)


def carregar():
    arvore = ast.parse(SEC.read_text(encoding="utf-8"))
    nomes = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            if no.targets[0].id in nomes:
                raise ValueError(f"{no.targets[0].id} atribuído duas vezes em security.py; o gerador não sabe qual vale")
            nomes[no.targets[0].id] = no.value
    for no in ast.walk(arvore):
        alvo = getattr(no, "target", None)
        if isinstance(no, (ast.AugAssign, ast.AnnAssign)) and isinstance(alvo, ast.Name) and (alvo.id.isupper() or alvo.id.startswith("_")):
            raise ValueError(f"{alvo.id} alterado com += ou anotação em security.py; ajuste o gerador")

    def avaliar(v):
        if isinstance(v, ast.Set):
            return {e.value for e in v.elts}
        if isinstance(v, ast.Tuple):
            return tuple(e.value for e in v.elts)
        if isinstance(v, ast.Name):
            return avaliar(nomes[v.id])
        if isinstance(v, ast.BinOp) and isinstance(v.op, ast.BitOr):
            return avaliar(v.left) | avaliar(v.right)
        if isinstance(v, ast.BinOp) and isinstance(v.op, ast.Sub):
            return avaliar(v.left) - avaliar(v.right)
        if isinstance(v, ast.Dict):
            return {k.value: avaliar(x) for k, x in zip(v.keys, v.values)}
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id in ("frozenset", "set") and len(v.args) == 1:
            return set(avaliar(v.args[0]))
        if isinstance(v, ast.DictComp) and _copia_de_matriz(v):
            # só a forma exata {k: frozenset(x) for k, x in MATRIZ.items()}, sem filtro: o conteúdo é o da matriz
            return {k: set(x) for k, x in avaliar(v.generators[0].iter.func.value).items()}
        raise ValueError(ast.dump(v))
    return avaliar(nomes["PERFIS"]), avaliar(nomes["PERMISSOES"])


def main():
    perfis, perm = carregar()
    todas = sorted(set().union(*perm.values()))
    if set(perm) != set(perfis):
        raise ValueError(f"PERFIS e PERMISSOES não têm os mesmos perfis: {sorted(set(perm) ^ set(perfis))}")
    cab = list(perfis)
    out = ["# Apêndice B: permissões por perfil", "",
           "Gerado automaticamente de `PERMISSOES` em `sistema/api/security.py` por `planejamento/documentacao/fonte/gerar_apendice_permissoes.py`. "
           "Não edite à mão. Perfil sem a permissão recebe 403 do servidor (negado por padrão).", "",
           "| Permissão | " + " | ".join(cab) + " |", "|---|" + "---|" * len(cab)]
    for p in todas:
        out.append(f"| `{p}` | " + " | ".join("✔" if p in perm.get(c, set()) else "" for c in cab) + " |")
    out += ["", f"Total: {len(todas)} permissões, {len(cab)} perfis."]
    SAIDA.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(todas)} permissões em {SAIDA}")


if __name__ == "__main__":
    main()
