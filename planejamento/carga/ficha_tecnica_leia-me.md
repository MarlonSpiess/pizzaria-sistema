# Carga da ficha técnica: o que a planilha traz e o que falta

22/10/2026. Fonte: FICHA_TECNICA_PIZZARIA.pdf (Pizzaria Maria Gabriela), enviada por Marlon. Leitura feita por script e conferida contra o texto do PDF; o resultado está em [ficha_tecnica_normalizada.csv](ficha_tecnica_normalizada.csv) (abre no Excel). Nada foi carregado no sistema ainda.

## O que a planilha traz

- **76 sabores**: 60 salgados e 16 doces (a estimativa anterior era 50).
- **46 ingredientes** distintos, depois de unir grafias diferentes (por exemplo "Alho e oleo" e "Alho e óleo").
- Cada ingrediente tem a quantidade da **Grande** e da **meia (1/2)**, no formato "200g ou 100g 1/2". Usei a coluna 1/2 como base da ficha e a Grande como o dobro, o que confere com a regra que você confirmou (U1). Nas quantidades ímpares a planilha arredonda (225g vira 112g na meia); a diferença é de no máximo 1 g.
- Salgados: molho ("1 COLHER") e mussarela em todos, mais até 4 ingredientes. Doces: uma base (coluna "CREME LEITE CHOCOLATE") mais até 2 ingredientes.

## O que a planilha não traz

1. Categoria (Tradicionais ou Especiais) e preço Grande e Broto de cada sabor (D2).
2. Ficha do calzone, da borda, dos adicionais e das bebidas.
3. Massa: insumos do preparo (farinha, água, fermento) e quanto de massa vai em cada tamanho.
4. Embalagem por tamanho (caixa, etiqueta).
5. Tempo de cada etapa.
6. Unidade de compra e custo de cada ingrediente (vem com Estoques e Compras).

## Pontos que parecem erro ou precisam de decisão

- **W1.** "1 COLHER" de molho: quantos gramas ou ml tem uma colher, e vale por meia ou pela pizza inteira? (recomendo: pesar uma colher uma vez e cadastrar em g)
- **W2.** Nos doces, a coluna "CREME LEITE CHOCOLATE" é a base: creme de leite em alguns e chocolate em outros? Qual sabor usa qual?
- **W3.** CHOC BRANCO e CHOC PRETO têm "leite condensado" duas vezes e nenhum chocolate. O primeiro deve ser chocolate branco e chocolate preto? (recomendo: sim)
- **W4.** STROG FRANGO usa "Stro Carne" e STROG CARNE usa "Stro Frango": estão trocados? (recomendo: sim, corrigir)
- **W5.** BANANA NEVADA, TROVOADA, SENSAÇÃO e TENTAÇÃO trazem leite condensado "40g ou 15g"; a meia seria 20g. É 20g? (recomendo: 20g)
- **W6.** "Frango" e "Frango desfiado" são o mesmo item? E "Calab ralada" e "Calabres ralada" são "Calabresa ralada", diferente de "Calabresa"? (recomendo: frango é um item só; calabresa ralada é outro item)
- **W7.** "Catupiry/Cheddar" no SEIS QUEIJOS: qual dos dois, ou a metade de cada? (recomendo: você me diz qual)
- **W8.** Lombinho, salame e pepperoni vêm em fatias (24, 20 e 34 fatias na Grande). Posso cadastrar em fatias, como na planilha? (recomendo: sim, e a conversão para kg entra em Estoques)
- **W9.** "Alho e óleo", "Strogonoff de carne" e "Strogonoff de frango" são feitos na casa (preparo, com ficha própria) ou comprados prontos? (recomendo: se feitos na casa, mandar a receita depois)
- **W10.** Os nomes dos itens sugeridos na coluna "ingrediente_sugerido" do CSV estão certos? Corrija o que quiser direto no arquivo.
