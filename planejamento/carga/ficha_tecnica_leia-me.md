# Carga da ficha técnica: situação

Versão 2, 22/10/2026. Fonte: FICHA_TECNICA_PIZZARIA.pdf (modelo e incompleto, segundo Marlon). Resultado da leitura, já com as respostas dele: [ficha_tecnica_normalizada.csv](ficha_tecnica_normalizada.csv) (abre no Excel; uma linha por ingrediente, com a fase e as observações). Nada foi carregado no sistema ainda.

## Regras aplicadas (respostas de Marlon em 22/10/2026)

- Todas as quantidades são **meia Grande ou 1 Broto**; a Grande é o dobro (U1).
- **Molho:** 1 colher = 100g na meia (200g na Grande).
- **Doces:** creme de leite é a base **antes do forno**, e frutas também; o resto entra **depois do forno**. Ingrediente 1 é sempre chocolate (branco se o nome tiver "branco" ou "branca", senão preto), ingrediente 2 é o que a planilha mostra no 1, ingrediente 3 é leite condensado. A planilha não traz a quantidade do chocolate.
- **Strogonoff:** estavam trocados; STROG FRANGO leva frango e STROG CARNE leva filé.
- **Frango** e "Frango desfiado" viram um item; "Calab ralada" e "Calabres ralada" viram **Calabresa**.
- **Fatias** passam a ser uma unidade (lombinho, salame, pepperoni).
- **Alho e óleo** é feito em casa (preparo, com receita a enviar).
- **Batata palha** entra depois do forno.
- Nos quatro doces com leite condensado "40g ou 15g", mantive a meia como está na planilha (15g).

## Respostas finais de 22/10/2026

- Chocolate: 50g por meia em todos os doces. SEIS QUEIJOS: 50g de Catupiry e 50g de Cheddar por meia. Nenhum outro item salgado entra depois do forno (só a batata palha).
- CHOC BRANCO e CHOC PRETO: a planilha trazia leite condensado duas vezes; ficou uma só, marcada na observação para Marlon ajustar.

## Resultado

76 sabores (60 salgados e 16 doces), 325 linhas, 43 itens, sem linhas pendentes. Arquivo: [ficha_tecnica_normalizada.csv](ficha_tecnica_normalizada.csv).

## Cardápio e carga (22/10/2026)

[cardapio.csv](cardapio.csv): 76 pizzas (60 salgadas e 16 doces), 3 calzones e 4 bordas.

- Salgados: os 48 primeiros da planilha são Tradicionais (Grande R$ 35), os 12 de COLONIAL a CHURRASCO são Especiais (Grande R$ 50). **Doces entram como Tradicionais**, e qualquer sabor pode mudar de categoria depois pela tela do Cardápio. Broto R$ 25 em todas as pizzas.
- Calzones (R$ 50): Calzone Portuguesa, Calzone Calabresa e Calzone Bacon. Estão em formulação; a ficha de cada um é **provisória, copiada da pizza de mesmo sabor**.
- Bordas: Catupiry, Cheddar, Chocolate preto e Chocolate branco, R$ 10 na Grande e na Broto (suposição minha de que vale nos dois tamanhos). A ficha de insumos de cada borda ainda não existe.

## Como carregar

1. `scripts/carregar_cardapio.py` cria as categorias, as pizzas, os calzones e as bordas.
2. `scripts/carregar_ficha_tecnica.py` cadastra os 43 itens e grava a ficha de cada produto.

Os dois usam a API, só simulam por padrão, aceitam `--aplicar` e podem rodar de novo sem duplicar. Testados em banco de teste (83 itens de cardápio e 79 fichas). A carga real acontece na instalação na loja.

## O que ainda falta

1. Nomes por extenso das abreviações da planilha (Bróc Bacon, Calabresa Ace, Champgnon, Strog Frango, Strog Carne, Calab 4 Queijos, Agentina); hoje os produtos mantêm o texto da planilha.
2. Ficha de insumos das bordas, dos adicionais e das bebidas; ficha final dos calzones.
3. Massa (farinha etc.), receita do alho e óleo, embalagem e o tempo de cada etapa.
