"""Números do sistema lidos do código, para as apresentações nunca ficarem com contagem digitada à mão.
Lê os arquivos como texto (não importa o sistema, não precisa de banco).
Rotas: só as dos routers em sistema/api/routers (a mesma regra do Apêndice A); as 4 rotas do main.py
(saúde, ícone, página e arquivos do app) não entram."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SISTEMA = RAIZ / "sistema"
MIGRACOES = SISTEMA / "migrations_pg"

# Mesmo critério de nome do aplicador (sistema/scripts/aplicar_migrations_pg.py).
_NOME_MIGRACAO = re.compile(r"^(\d+)_.+\.sql$")
# Comentários, literais entre aspas simples e corpos $$...$$ não são comandos (mesma ideia do aplicador).
_IGNORAVEL = re.compile(r"--[^\n]*|/\*.*?\*/|\$([A-Za-z_]*)\$.*?\$\1\$|'(?:[^']|'')*'", re.DOTALL)
_NOME = r'(?:"?\w+"?\.)?"?(\w+)"?'
_CRIA = re.compile(r"\bCREATE\s+(?:UNLOGGED\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?" + _NOME, re.I)
_APAGA = re.compile(r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?" + _NOME, re.I)
_RENOMEIA = re.compile(r"\bALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?" + _NOME + r"\s+RENAME\s+TO\s+" + _NOME, re.I)
# Igual a gerar_apendice_rotas.py: decorador no começo da linha e caminho entre aspas duplas.
_ROTA = re.compile(r'^@router\.(?:get|post|put|patch|delete)\("', re.M)


def migracoes():
    """Migrações na ordem em que o aplicador as roda."""
    achadas = [(int(m.group(1)), p.name) for p in MIGRACOES.glob("*.sql") if (m := _NOME_MIGRACAO.match(p.name))]
    return [nome for _, nome in sorted(achadas)]


def tabelas():
    """Tabelas que existem depois de aplicar todas as migrações em ordem (criadas, menos apagadas, com renomeações)."""
    existentes = set()
    for m in migracoes():
        sql = _IGNORAVEL.sub(" ", (MIGRACOES / m).read_text(encoding="utf-8"))
        eventos = [(x.start(), "cria", x.group(1)) for x in _CRIA.finditer(sql)]
        eventos += [(x.start(), "apaga", x.group(1)) for x in _APAGA.finditer(sql)]
        eventos += [(x.start(), "renomeia", (x.group(1), x.group(2))) for x in _RENOMEIA.finditer(sql)]
        for _, acao, nome in sorted(eventos, key=lambda e: e[0]):
            if acao == "cria":
                existentes.add(nome.lower())
            elif acao == "apaga":
                existentes.discard(nome.lower())
            else:
                existentes.discard(nome[0].lower())
                existentes.add(nome[1].lower())
    return sorted(existentes)


def rotas():
    """Decoradores @router.<método>( nos routers, a mesma regra do gerador do Apêndice A."""
    return sum(len(_ROTA.findall(arq.read_text(encoding="utf-8"))) for arq in (SISTEMA / "api" / "routers").glob("*.py"))


def numeros():
    return {"migracoes": len(migracoes()), "tabelas": len(tabelas()), "rotas": rotas()}


if __name__ == "__main__":
    print(numeros())
