"""Gera tecnico/Apendice_B_Permissoes_por_Perfil.md a partir de PERMISSOES em sistema/api/security.py.
Uso, na raiz do repositório: python planejamento/documentacao/fonte/gerar_apendice_permissoes.py
Lê o arquivo como texto (não importa o sistema, não precisa de banco)."""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SEC = RAIZ / "sistema" / "api" / "security.py"
SAIDA = Path(__file__).resolve().parents[1] / "tecnico" / "Apendice_B_Permissoes_por_Perfil.md"


def carregar():
    arvore = ast.parse(SEC.read_text(encoding="utf-8"))
    nomes = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            nomes[no.targets[0].id] = no.value

    def avaliar(v):
        if isinstance(v, ast.Set):
            return {e.value for e in v.elts}
        if isinstance(v, ast.Tuple):
            return tuple(e.value for e in v.elts)
        if isinstance(v, ast.Name):
            return avaliar(nomes[v.id])
        if isinstance(v, ast.BinOp) and isinstance(v.op, ast.BitOr):
            return avaliar(v.left) | avaliar(v.right)
        if isinstance(v, ast.Dict):
            return {k.value: avaliar(x) for k, x in zip(v.keys, v.values)}
        raise ValueError(ast.dump(v))
    return avaliar(nomes["PERFIS"]), avaliar(nomes["PERMISSOES"])


def main():
    perfis, perm = carregar()
    todas = sorted(set().union(*perm.values()))
    cab = ["administrador", "proprietario", "gerente", "subgerente", "atendente", "massa", "pizzaiolo", "acabamento"]
    cab = [p for p in cab if p in perfis]
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
