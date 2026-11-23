"""Popula um banco de DEMONSTRAÇÃO com dados fictícios para gravar o vídeo do sistema.

Nunca usar no banco da loja: recusa qualquer banco cujo nome não termine em _demo.
Tudo aqui é inventado: loja, pessoas, telefones, endereços, sabores, preços de custo.
Os preços de venda seguem só a regra do cardápio (Grande, Broto, Calzone, Borda).

Uso (com o servidor rodando sobre o banco pizzaria_demo):
    DB_NAME=pizzaria_demo DB_PASS=... DEMO_SENHA=... python semear_demo.py [--url http://127.0.0.1:8080]
"""
import argparse
import os
import sys
import uuid

import httpx
import psycopg

SENHA = os.environ.get("DEMO_SENHA", "")
DB = dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")), user=os.getenv("DB_USER", "postgres"),
          password=os.getenv("DB_PASS", ""), dbname=os.getenv("DB_NAME", ""))

# Equipe fictícia: login, nome, perfil
EQUIPE = [("carla", "Carla Mendes", "gerente"), ("bruno", "Bruno Alves", "atendente"), ("diego", "Diego Rocha", "pizzaiolo"),
          ("elisa", "Elisa Prado", "massa"), ("fabio", "Fábio Nunes", "acabamento")]
PARAMETROS = {"loja_nome": "Pizzaria Demonstração", "fundo_troco_padrao": "100,00", "taxa_entrega_padrao": "8,00",
              "valor_entrega_padrao": "6,00", "diaria_entregador_padrao": "40,00", "tolerancia_diferenca_caixa": "2,00",
              "limite_desconto_atendente_pct": "5", "limite_desconto_subgerente_pct": "10", "limite_desconto_gerente_pct": "20",
              "calzone_massa_tamanho": "grande", "producao_montagem_min": "3", "producao_pizzaiolos_ativos": "2",
              "producao_acabamento_min": "2", "entrega_deslocamento_min": "15", "forno_pizzas_por_vez": "4",
              "venda_exige_caixa_aberto": "sim", "cmv_meta_pct": "15", "checklist_temp_refrigerado_max": "5",
              "checklist_temp_congelado_max": "-18"}
# Insumos fictícios: nome, unidade, custo por unidade, saldo inicial
INSUMOS = [("Muçarela", "kg", "38,00", "12"), ("Molho de tomate", "kg", "9,50", "8"), ("Calabresa", "kg", "29,00", "5"),
           ("Cebola", "kg", "6,00", "4"), ("Presunto", "kg", "32,00", "4"), ("Ovo", "un", "0,80", "60"),
           ("Frango desfiado", "kg", "26,00", "4"), ("Catupiry", "kg", "42,00", "3"), ("Manjericão", "g", "0,12", "300"),
           ("Tomate", "kg", "7,00", "5"), ("Chocolate", "kg", "35,00", "2"), ("Caixa de pizza", "un", "1,60", "150"),
           ("Refrigerante 2 L", "un", "7,50", "24")]
# Sabores: nome, categoria, ingredientes (nome do insumo, quantidade na Grande)
SABORES = [("Margherita", "Tradicionais", [("Muçarela", "0,12"), ("Molho de tomate", "0,06"), ("Tomate", "0,04"), ("Manjericão", "3")]),
           ("Calabresa", "Tradicionais", [("Muçarela", "0,10"), ("Molho de tomate", "0,06"), ("Calabresa", "0,08"), ("Cebola", "0,03")]),
           ("Portuguesa", "Tradicionais", [("Muçarela", "0,10"), ("Molho de tomate", "0,06"), ("Presunto", "0,05"), ("Ovo", "1"), ("Cebola", "0,02")]),
           ("Frango com Catupiry", "Especiais", [("Muçarela", "0,10"), ("Molho de tomate", "0,06"), ("Frango desfiado", "0,08"), ("Catupiry", "0,05")]),
           ("Quatro Queijos", "Especiais", [("Muçarela", "0,15"), ("Molho de tomate", "0,05"), ("Catupiry", "0,06")]),
           ("Chocolate", "Doces", [("Chocolate", "0,10")])]
CLIENTES = [("Marina Costa", "11900000101", "Rua das Acácias, 120"), ("Rafael Lima", "11900000102", "Av. dos Ipês, 45"),
            ("Juliana Souza", "11900000103", "Rua do Sol, 9"), ("Pedro Henrique", "11900000104", "Rua Aurora, 300")]
ENTREGADORES = [("Lucas Moto", "11900000201"), ("Tiago Entregas", "11900000202")]


class Api:
    def __init__(self, url):
        self.c = httpx.Client(base_url=url.rstrip("/") + "/api", timeout=30)
        self.tokens = {}

    def entrar(self, login):
        r = self.c.post("/auth/login", json={"usuario": login, "senha": SENHA})
        r.raise_for_status()
        self.tokens[login] = r.json()["token"]

    def chamar(self, quem, metodo, caminho, corpo=None, ok=(200, 201), tolera=()):
        r = self.c.request(metodo, caminho, json=corpo, headers={"Authorization": "Bearer " + self.tokens[quem]})
        if r.status_code in tolera:
            return None
        if r.status_code not in ok:
            raise SystemExit(f"[erro] {metodo} {caminho}: {r.status_code} {r.text[:300]}")
        return r.json() if r.content else None


def sql(consulta, params=()):
    with psycopg.connect(**DB) as c:  # uma transação por chamada; SET vale só para ela
        for parte in consulta.split("; "):
            c.execute(parte, params if "%s" in parte else ())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    a = ap.parse_args()
    if not DB["dbname"].endswith("_demo"):
        sys.exit("Recusado: este script só roda em banco cujo nome termina em _demo.")
    if len(SENHA) < 8:
        sys.exit("Defina DEMO_SENHA (8 ou mais caracteres): será a senha de todos os usuários fictícios.")
    from api.security import hash_senha  # roda de dentro de sistema/ (PYTHONPATH)
    hs = hash_senha(SENHA)
    sql("UPDATE usuario SET senha_hash = %s, deve_trocar_senha = false WHERE usuario = 'admin'", (hs,))
    api = Api(a.url)
    api.entrar("admin")
    A = "admin"

    for k, v in PARAMETROS.items():
        api.chamar(A, "PUT", f"/parametros/{k}", {"valor": v})
    for rota in ("/producao/motivos/iniciar-padrao", "/caixa/motivos/iniciar-padrao", "/etapas/iniciar-padrao",
                 "/estoque/locais/iniciar-padrao", "/contas/tipos-despesa/iniciar-padrao", "/checklists/modelos/padrao"):
        api.chamar(A, "POST", rota, tolera=(409,))

    for login, nome, perfil in EQUIPE:
        api.chamar(A, "POST", "/usuarios", {"usuario": login, "nome": nome, "perfil": perfil, "senha": SENHA}, tolera=(409,))
    sql("UPDATE usuario SET deve_trocar_senha = false")
    for login, *_ in EQUIPE:
        api.entrar(login)

    # Cardápio: preços de venda pela regra (Grande Tradicional 35, Especial 50, Broto 25, Calzone 50, Borda 10)
    cats = {}
    for nome, g, b in (("Tradicionais", "35,00", "25,00"), ("Especiais", "50,00", "25,00"), ("Doces", "35,00", "25,00")):
        cats[nome] = api.chamar(A, "POST", "/categorias", {"nome": nome, "preco_padrao_grande": g, "preco_padrao_broto": b})["id"]
    itens = {}
    for nome, un, custo, saldo in INSUMOS:
        classe = {"Caixa de pizza": "embalagem", "Refrigerante 2 L": "revenda"}.get(nome, "insumo")
        it = api.chamar(A, "POST", "/itens", {"nome": nome, "classe": classe, "unidade": un})
        itens[nome] = it["id"]
        api.chamar(A, "POST", "/estoque/movimentos", {"tipo": "entrada_inicial", "item_id": it["id"], "quantidade": saldo,
                                                      "custo_unit": custo, "motivo": "Estoque inicial da demonstração"})
    # Calabresa abaixo do mínimo: aparece nos alertas do estoque, de onde a gerência fecha a venda dos sabores
    api.chamar(A, "PUT", f"/estoque/itens/{itens['Calabresa']}/config", {"estoque_minimo": "6", "ponto_pedido": "8"})
    prod = {}
    for nome, cat, ingr in SABORES:
        g = "50,00" if cat == "Especiais" else "35,00"
        p = api.chamar(A, "POST", "/produtos", {"tipo": "pizza", "nome": nome, "categoria_id": cats[cat], "preco_grande": g,
                                                "preco_broto": "25,00", "ingredientes": ", ".join(i for i, _ in ingr)})
        prod[nome] = p["id"]
        api.chamar(A, "PUT", f"/fichas/produto/{p['id']}", {"linhas": [{"item_id": itens[i], "quantidade": q} for i, q in ingr]})
    prod["Calzone de Calabresa"] = api.chamar(A, "POST", "/produtos", {"tipo": "calzone", "nome": "Calzone de Calabresa",
                                                                         "preco_unico": "50,00"})["id"]
    api.chamar(A, "PUT", f"/fichas/produto/{prod['Calzone de Calabresa']}",
               {"linhas": [{"item_id": itens["Muçarela"], "quantidade": "0,12"}, {"item_id": itens["Calabresa"], "quantidade": "0,08"}]})
    prod["Refrigerante 2 L"] = api.chamar(A, "POST", "/produtos", {"tipo": "bebida", "nome": "Refrigerante 2 L", "preco_unico": "14,00"})["id"]
    api.chamar(A, "PUT", f"/fichas/produto/{prod['Refrigerante 2 L']}", {"linhas": [{"item_id": itens["Refrigerante 2 L"], "quantidade": "1", "perda_pct": "0"}]})
    borda = api.chamar(A, "POST", "/adicionais", {"tipo": "borda", "nome": "Borda de Catupiry", "preco_grande": "10,00", "preco_broto": "10,00"})["id"]
    api.chamar(A, "PUT", f"/fichas/adicional/{borda}/grande", {"linhas": [{"item_id": itens["Catupiry"], "quantidade": "0,08"}]})

    clientes = [api.chamar("bruno", "POST", "/clientes", {"nome": n, "telefone": t, "endereco": e})["id"] for n, t, e in CLIENTES]
    for n, t in ENTREGADORES:
        api.chamar(A, "POST", "/entregadores", {"nome": n, "telefone": t})

    # Caixa do dia aberto pela atendente com o fundo padrão
    api.chamar("bruno", "POST", "/caixa/abrir", {}, tolera=(409,))
    # Massa do dia
    api.chamar("elisa", "POST", "/producao/massa/lote", {"tamanho": "grande", "quantidade": 40})
    api.chamar("elisa", "POST", "/producao/massa/lote", {"tamanho": "broto", "quantidade": 20})

    def pedido(itens_ped, tipo="retirada", cliente=None, forma="pix", urgente=False, obs=None):
        corpo = {"itens": itens_ped, "tipo": tipo}
        total = api.chamar("bruno", "POST", "/pedidos/calcular", corpo)["total"]
        extra = {"cliente_id": cliente} if cliente else {}
        return api.chamar("bruno", "POST", "/pedidos", {**corpo, **extra, "pagamentos": [{"forma": forma, "valor": total}],
                                                        "urgente": urgente, "observacoes": obs, "chave": uuid.uuid4().hex})

    def pz(sabor, tam="grande", s2=None, borda_=False, q=1):
        it = {"tipo": "pizza", "produto_id": prod[sabor], "tamanho": tam, "quantidade": q}
        if s2:
            it["sabor2_id"] = prod[s2]
        if borda_:
            it["adicional_ids"] = [borda]
        return it

    beb = {"tipo": "bebida", "produto_id": prod["Refrigerante 2 L"], "quantidade": 1}
    # Pedidos já concluídos ao longo do dia (alimentam caixa, estoque e BI)
    feitos = [pedido([pz("Calabresa"), beb]), pedido([pz("Margherita", s2="Quatro Queijos")], forma="credito"),
              pedido([pz("Portuguesa", borda_=True)], forma="dinheiro"), pedido([pz("Frango com Catupiry", q=2)], forma="debito"),
              pedido([pz("Chocolate", tam="broto"), beb]), pedido([{"tipo": "calzone", "produto_id": prod["Calzone de Calabresa"]}], forma="pix")]
    for p in feitos:
        concluir(api, p["id"])
    # Horários espalhados pela noite (só no banco de demonstração), para o tempo médio do painel ter sentido
    # A trava de imutabilidade do pedido é desligada na conexão desta chamada (session_replication_role; exige superusuário),
    # que fecha logo depois. Só no banco _demo.
    for i, p in enumerate(feitos):
        atras, duracao = (len(feitos) - i) * 22 + 15, 26 + (i * 5) % 11
        sql("SET session_replication_role = replica; UPDATE pedido SET criado_em = now() - make_interval(mins => %s), entrega_real = now() - make_interval(mins => %s) "
            "WHERE id = %s", (atras, atras - duracao, p["id"]))
    # Entrega já produzida, esperando o despacho (cena do caixa e entregas)
    pronta = pedido([pz("Frango com Catupiry"), beb], tipo="entrega", cliente=clientes[3], forma="credito")
    concluir(api, pronta["id"], retirar=False)
    # Pedidos em andamento para as telas de produção
    pedido([pz("Calabresa", q=2), beb], tipo="entrega", cliente=clientes[0], forma="pix")
    pedido([pz("Margherita", s2="Calabresa", borda_=True)], tipo="entrega", cliente=clientes[1], forma="credito")
    pedido([pz("Quatro Queijos")], forma="dinheiro", obs="Bem assada")
    pedido([pz("Portuguesa"), pz("Chocolate", tam="broto")], tipo="entrega", cliente=clientes[2], forma="pix")
    print("[ok] demonstração pronta: loja, equipe, cardápio, fichas, estoque, caixa e pedidos fictícios.")


def concluir(api, pedido_id, retirar=True):
    """Leva um pedido pela produção inteira, com o login de cada função. A fila é da loja toda: chamar com a fila só deste pedido."""
    while True:
        r = api.c.post("/producao/pizzas/proxima", headers={"Authorization": "Bearer " + api.tokens["diego"]})
        if r.status_code == 404:  # fila vazia
            break
        if r.status_code != 200:
            raise SystemExit(f"[erro] próxima pizza: {r.status_code} {r.text[:200]}")
        pid = r.json()["id"]
        api.chamar("diego", "POST", f"/producao/pizzas/{pid}/produzida")
        api.chamar("fabio", "POST", f"/producao/pizzas/{pid}/saiu-do-forno")
        api.chamar("fabio", "POST", f"/producao/pizzas/{pid}/acabada")
    api.chamar("fabio", "POST", f"/producao/pedidos/{pedido_id}/acabado")
    if retirar:
        api.chamar("bruno", "POST", f"/pedidos/{pedido_id}/situacao", {"situacao": "despachado ou retirado"})


if __name__ == "__main__":
    main()
