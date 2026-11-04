"""Gera tecnico/Apendice_A_Rotas_da_API.md lendo os routers de sistema/api (rota, método e permissão exigida).
Uso, na raiz do repositório: python planejamento/documentacao/fonte/gerar_apendice_rotas.py
Rodar de novo sempre que uma rota mudar; o arquivo gerado não deve ser editado à mão."""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
ROUTERS = RAIZ / "sistema" / "api" / "routers"
SAIDA = Path(__file__).resolve().parents[1] / "tecnico" / "Apendice_A_Rotas_da_API.md"
NOME = {"auth": "Autenticação", "usuarios": "Usuários", "parametros": "Parâmetros", "auditoria": "Auditoria", "sistema": "Sistema (backup)",
        "cardapio": "Cardápio", "pessoas": "Clientes e entregadores", "receitas": "Itens, fichas técnicas e etapas", "vendas": "Pedidos (Vendas)",
        "producao": "Produção", "caixa": "Caixa, entregas e despacho", "canais": "Canais de venda", "estoque": "Estoque", "compras": "Compras",
        "contas": "Contas e fluxo de caixa", "vendas_fechadas": "Vendas fechadas por ingrediente", "custos": "Custos", "imobilizado": "Imobilizado", "rh": "RH", "bi": "BI"}


def rotas(arq: Path):
    src = arq.read_text(encoding="utf-8")
    m = re.search(r'APIRouter\((?:prefix="([^"]*)")?', src)
    pre = (m.group(1) or "") if m else ""
    linhas = src.split("\n")
    for i, l in enumerate(linhas):
        r = re.match(r'@router\.(get|post|put|patch|delete)\("([^"]*)"', l)
        if not r:
            continue
        bloco = "\n".join(linhas[i + 1:i + 8]).split("\n@router")[0]
        perms = []
        for g in re.findall(r'requer(_alguma)?\(([^)]*)\)', bloco):
            nomes = [p.strip().strip('"') for p in g[1].split(",") if p.strip()]
            perms.append(" ou ".join(f"`{p}`" for p in nomes))
        rota = f"/api{pre}{r.group(2)}"
        padrao = "nenhuma (é a rota que abre a sessão)" if rota == "/api/auth/login" else "sessão válida (sem permissão específica)"
        yield r.group(1).upper(), rota, "; ".join(perms) or padrao


def main():
    out = ["# Apêndice A: rotas da API e permissão exigida", "",
           "Gerado automaticamente a partir de `sistema/api/routers/` por `planejamento/documentacao/fonte/gerar_apendice_rotas.py`. "
           "Não edite à mão: rode o script de novo quando o código mudar.", "",
           "A permissão é conferida no servidor em cada chamada (`requer` exige a permissão; `requer_alguma` aceita qualquer uma das listadas). "
           "Quais perfis têm cada permissão está na seção 5 do Manual Técnico. Além da permissão, várias rotas aplicam regras de negócio "
           "(por exemplo, caixa aberto, limite de desconto, aprovação por outra pessoa) que devolvem 400, 403 ou 409.", "",
           "`/health` (sem login) e as telas (`/`, `/static/*`) ficam fora da API.", ""]
    total = 0
    for arq in sorted(ROUTERS.glob("*.py")):
        if arq.stem == "__init__":
            continue
        lista = list(rotas(arq))
        if not lista:
            continue
        total += len(lista)
        out += [f"## {NOME.get(arq.stem, arq.stem)} (`{arq.name}`)", "", "| Método | Rota | Permissão |", "|---|---|---|"]
        out += [f"| {m} | `{r}` | {p} |" for m, r, p in lista]
        out.append("")
    out.insert(4, f"Total: {total} rotas.\n")
    SAIDA.write_text("\n".join(out), encoding="utf-8")
    print(f"{total} rotas em {SAIDA}")


if __name__ == "__main__":
    sys.exit(main())
