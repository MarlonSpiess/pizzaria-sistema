"""Cadastra categorias, pizzas (salgadas e doces), calzones e bordas a partir de planejamento/carga/cardapio.csv, pela API.

Por padrão só simula. Com --aplicar cria o que ainda não existe (mesmo nome, sem considerar maiúsculas e acentos). Produto
existente não é alterado: mude preço, nome e categoria pela tela do Cardápio.
Colunas: tipo (pizza, calzone, borda), nome, categoria, grande, broto, unico.

Uso:  set PZ_SENHA=...   python scripts/carregar_cardapio.py --usuario admin [--url http://127.0.0.1:8000] [--aplicar] [arquivo.csv]
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from carregar_ficha_tecnica import Api, sem_acento  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", nargs="?", default=os.path.join(os.path.dirname(__file__), "..", "..", "planejamento", "carga", "cardapio.csv"))
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--usuario", required=True)
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    senha = os.environ.get("PZ_SENHA")
    if not senha:
        raise SystemExit("Defina a senha na variável PZ_SENHA (não é aceita como argumento).")
    with open(a.arquivo, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    api = Api(a.url)
    api.token = api.chamar("POST", "/auth/login", {"usuario": a.usuario, "senha": senha})["token"]
    categorias = {sem_acento(c["nome"]): c for c in api.chamar("GET", "/categorias")}
    for nome in dict.fromkeys(l["categoria"] for l in linhas if l["tipo"] == "pizza"):
        if sem_acento(nome) not in categorias:
            primeira = next(l for l in linhas if l["categoria"] == nome)
            if a.aplicar:
                categorias[sem_acento(nome)] = api.chamar("POST", "/categorias", {"nome": nome, "preco_padrao_grande": primeira["grande"], "preco_padrao_broto": primeira["broto"]})
            print(f"categoria {'criada' if a.aplicar else 'a criar'}: {nome} (Grande {primeira['grande']}, Broto {primeira['broto']})")
    existentes = {(p["tipo"], sem_acento(p["nome"])) for p in api.chamar("GET", "/produtos")}
    bordas = {sem_acento(x["nome"]) for x in api.chamar("GET", "/adicionais")}
    criados = ja = 0
    for l in linhas:
        t, chave = l["tipo"], sem_acento(l["nome"])
        if (t == "borda" and chave in bordas) or (t != "borda" and (t, chave) in existentes):
            ja += 1
            continue
        if a.aplicar:
            if t == "pizza":
                api.chamar("POST", "/produtos", {"tipo": "pizza", "nome": l["nome"], "categoria_id": categorias[sem_acento(l["categoria"])]["id"],
                                                 "preco_grande": l["grande"], "preco_broto": l["broto"]})
            elif t == "calzone":
                api.chamar("POST", "/produtos", {"tipo": "calzone", "nome": l["nome"], "preco_unico": l["unico"]})
            elif t == "borda":
                api.chamar("POST", "/adicionais", {"tipo": "borda", "nome": l["nome"], "preco_grande": l["grande"], "preco_broto": l["broto"]})
            else:
                raise SystemExit(f"Tipo desconhecido: {t}")
        criados += 1
    print(f"Itens do cardápio {'criados' if a.aplicar else 'a criar'}: {criados}; já existiam: {ja}.")
    if not a.aplicar:
        print("Simulação: nada foi alterado. Use --aplicar para gravar.")


if __name__ == "__main__":
    sys.exit(main())
