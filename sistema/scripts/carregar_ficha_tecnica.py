"""Carrega itens e fichas técnicas a partir de planejamento/carga/ficha_tecnica_normalizada.csv, pela API do sistema.

Por padrão só mostra o que faria (simulação). Com --aplicar cadastra os itens que faltam e grava a ficha de cada sabor que já
existe como produto (pizza, mesmo nome sem considerar maiúsculas e acentos). Sabor sem produto fica no relatório: o produto
precisa ter categoria e preço antes (cadastro do cardápio). Ficha já salva não é regravada se estiver igual.

Uso:  set PZ_SENHA=...   python scripts/carregar_ficha_tecnica.py --usuario admin [--url http://127.0.0.1:8000] [--aplicar] [arquivo.csv]
"""
import argparse
import csv
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.request

PREPAROS = {"Alho e óleo"}  # feitos em casa; a receita é cadastrada depois
FASES = {"montagem", "pos_forno"}


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower().strip()


class Api:
    def __init__(self, url: str):
        self.url, self.token = url.rstrip("/"), None

    def chamar(self, metodo, caminho, corpo=None):
        req = urllib.request.Request(self.url + "/api" + caminho, method=metodo, data=None if corpo is None else json.dumps(corpo).encode())
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or "null")
        except urllib.error.HTTPError as e:
            try:
                detalhe = json.loads(e.read()).get("detail")
            except Exception:
                detalhe = None
            raise SystemExit(f"Erro {e.code} em {metodo} {caminho}: {detalhe}")


def ler_csv(caminho):
    sabores = {}
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["fase"] not in FASES:
                raise SystemExit(f"Fase inválida em {r['sabor']} / {r['ingrediente']}: {r['fase']}")
            if not r["meia_base"].strip():
                raise SystemExit(f"Quantidade em branco em {r['sabor']} / {r['ingrediente']}: preencha antes de carregar.")
            sabores.setdefault(r["sabor"].strip(), []).append(r)
    return sabores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", nargs="?", default=os.path.join(os.path.dirname(__file__), "..", "..", "planejamento", "carga", "ficha_tecnica_normalizada.csv"))
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--usuario", required=True)
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    senha = os.environ.get("PZ_SENHA")
    if not senha:
        raise SystemExit("Defina a senha na variável PZ_SENHA (não é aceita como argumento).")
    sabores = ler_csv(a.arquivo)
    api = Api(a.url)
    api.token = api.chamar("POST", "/auth/login", {"usuario": a.usuario, "senha": senha})["token"]
    itens = {sem_acento(i["nome"]): i for i in api.chamar("GET", "/itens")}
    necessarios = {}
    for linhas in sabores.values():
        for r in linhas:
            necessarios.setdefault(r["ingrediente"].strip(), r["unidade"].strip())
    faltam = [(n, u) for n, u in necessarios.items() if sem_acento(n) not in itens]
    print(f"{len(sabores)} sabores no arquivo, {len(necessarios)} itens usados, {len(faltam)} itens a cadastrar.")
    for n, u in faltam:
        classe = "preparo" if n in PREPAROS else "insumo"
        if a.aplicar:
            itens[sem_acento(n)] = api.chamar("POST", "/itens", {"nome": n, "classe": classe, "unidade": "fatia" if u == "fatia" else "g"})
        print(f"  item {'cadastrado' if a.aplicar else 'a cadastrar'}: {n} ({classe}, {u})")
    produtos = {sem_acento(p["nome"]): p for p in api.chamar("GET", "/produtos?tipo=pizza")}
    sem_produto, gravadas, iguais = [], 0, 0
    for sabor, linhas in sabores.items():
        prod = produtos.get(sem_acento(sabor))
        if not prod:
            sem_produto.append(sabor)
            continue
        novas = sorted(({"item_id": itens[sem_acento(r["ingrediente"])]["id"], "quantidade": r["meia_base"].strip().replace(",", "."), "fase": r["fase"]} for r in linhas
                        if sem_acento(r["ingrediente"]) in itens), key=lambda x: x["item_id"])
        atual = api.chamar("GET", f"/fichas/produto/{prod['id']}")["linhas"]
        if sorted(((x["item_id"], float(x["quantidade"]), x["fase"]) for x in atual)) == sorted(((x["item_id"], float(x["quantidade"]), x["fase"]) for x in novas)):
            iguais += 1
            continue
        if a.aplicar:
            api.chamar("PUT", f"/fichas/produto/{prod['id']}", {"linhas": novas})
        gravadas += 1
    print(f"Fichas {'gravadas' if a.aplicar else 'a gravar'}: {gravadas}; já iguais: {iguais}; sabores sem produto no cardápio: {len(sem_produto)}.")
    for s in sem_produto:
        print("  sem produto:", s)
    if not a.aplicar:
        print("Simulação: nada foi alterado. Use --aplicar para gravar.")


if __name__ == "__main__":
    sys.exit(main())
