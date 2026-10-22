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

## Resultado

76 sabores (60 salgados e 16 doces), 327 linhas, 43 itens. Ficaram **20 linhas marcadas PENDENTE** no CSV.

## O que ainda falta

1. Quantidade do chocolate em cada doce (16 linhas).
2. SEIS QUEIJOS usa "Catupiry e Cheddar": quanto de cada na meia? Hoje o CSV repete 50g para os dois, só como espaço reservado.
3. CHOC BRANCO e CHOC PRETO: a planilha repete leite condensado; com a regra, o ingrediente 2 também seria leite condensado. Marlon ajusta.
4. Quais outros ingredientes entram depois do forno nos salgados (só a batata palha está marcada)?
5. Categoria e preço Grande e Broto de cada sabor (D2).
6. Calzone, borda, adicionais, bebidas, massa (farinha etc.), embalagem e o tempo de cada etapa.
