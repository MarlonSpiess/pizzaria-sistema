# Resposta ao QA cego das fatias 2A (Estoques) e 2B (Compras)

## Corrigido
- A1 preço do recebimento: a tela pré-preenche o preço por unidade de compra (preço do pedido × fator); a comparação com o pedido tem tolerância de R$ 0,001 (M3).
- A2 saída manual (perda, consumo, transferência) recusa quando passa do saldo total do item; só a baixa automática pode deixar o saldo negativo.
- A4 o esperado do inventário é gravado no instante da contagem; perda ou compra feita depois não vira diferença nem é desfeita no fechamento.
- A5 e M2 cada entrega sem código de lote ganha um lote próprio (data + origem); lote existente nunca troca de validade, a entrada com validade diferente pede outro código.
- Itens de data da nota: a data padrão da tela usa o fuso de Brasília (baixa).

## Pendente (decisão de Marlon; segue a recomendação)
- A3 limite de aprovação não definido: hoje significa que o comprador aprova sozinho. Recomendado: definir o limite antes de usar (a tela de parâmetros avisa). Pedido digitado direto e fracionamento em várias listas ainda não somam por dia.
- A2 (parte): a entrada de compra não compensa o saldo negativo sem lote.
- M1 refazer baixa que falhou por trava (hoje fica em pendência de estoque para tratamento manual).
- M4 a M13 e as baixas do relatório: nota duplicada por caixa/zeros, estoque sem custo diluindo o custo médio, cancelar pedido já acabado não estorna bebida, estoque inicial repetível, inventário mensal confirmando sempre os não contados, contagem cega do inventário (o saldo aparece na lista de itens), rendimento do preparo na ficha, vínculo da nota com a sangria, sugestão de validade que soma só o último lote, rateio de frete.
- M12: confirmar com Marlon se a ficha de preparo informa rendimento (receita de molho que rende X g).
