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

## Como carregar

O script `sistema/scripts/carregar_ficha_tecnica.py` lê esse CSV e usa a API do sistema: cadastra os itens que faltam (Alho e óleo como preparo, o resto como insumo; fatias onde a planilha usa fatias) e grava a ficha de cada sabor que já existe como produto. Por padrão só simula; `--aplicar` grava. Pode rodar de novo sem duplicar. Testado em banco de teste.

## O que ainda falta

1. Os 76 sabores como produtos no cardápio, com categoria e preço Grande e Broto (D2). Sem isso as fichas não têm onde entrar.
2. Calzone, borda, adicionais, bebidas, massa (farinha etc.), receita do alho e óleo, embalagem e o tempo de cada etapa.
