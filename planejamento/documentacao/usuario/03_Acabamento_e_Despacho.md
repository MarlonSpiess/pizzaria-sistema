# Manual do Usuário: Acabamento e Despacho

Versão 2.0, 04/11/2026. Leia antes o [manual comum](00_Comum_a_Todos.md).

**As suas telas:** Produção > **Forno**, **Acabamento** e **Despacho**. O forno e o despacho fazem parte da sua função (decisão de 03/11/2026).

As telas Forno e Acabamento se atualizam sozinhas a cada 8 segundos. Toque em **Atualizar** se precisar na hora.

## 1. Forno

- O topo mostra quantas pizzas estão no forno e a capacidade. Se passar da capacidade, aparece um aviso (o sistema só avisa, não bloqueia).
- Quando a pizza sair do forno, toque em **Saiu do forno** na linha dela.
- Se perceber que a pizza está com o **sabor errado** ou com **problema no formato/esteira**, toque no botão correspondente na linha dela (no Forno ou no Acabamento). A pizza vira **avulsa** e a pizza certa volta para o **topo** da lista de montagem. O sistema pede uma observação opcional (até 120 caracteres, exemplo: "sem cebola por engano"), que vai junto na venda da avulsa.

## 2. Acabamento e etiqueta

**Saíram do forno:** as pizzas esperando acabamento, com o número do pedido e o nome do cliente.

1. Corte, embale e confira a pizza.
2. Toque em **Acabada e etiqueta**. A etiqueta aparece na tela com o nome do cliente, o número do pedido, os sabores e o tamanho.
3. Toque em **Imprimir** e cole a etiqueta na caixa. Toque em **Fechar** para tirar a etiqueta da tela.

Se a pizza saiu errada, escolha o motivo em **Refazer** e confirme. A pizza atual vira perda e uma pizza igual entra **na frente** da fila de montagem. A refação só é possível enquanto o pedido está em produção; depois disso, a recepção faz um pedido novo.

**Pizzas avulsas (montagem errada):** a pizza errada aparece neste cartão, com sabores, adicionais e observações (sem valores). Quem vende é a recepção, pelo Novo pedido (você não lança a venda). Se não houver venda, toque em **Descartar (motivo)**: ela entra nas perdas e o estoque baixa como perda (a ficha inteira se a pizza já foi ao forno; só a montagem, se não foi).

**Avisos da Produção:** o cartão no alto da tela mostra montagem errada e falta de ingrediente; para você, aparece também o cliente do pedido.

**Pizzas perdidas para refazer:** quando o pizzaiolo perde uma pizza na montagem, aparece no Acabamento o cartão **Pizzas perdidas para refazer** (ele só aparece se houver alguma). Toque em **Refazer**, escolha o motivo (obrigatório) e confirme. Uma pizza igual entra **na frente** da fila de montagem, ligada à perdida. A perdida não conta mais como pendente: o pedido pode ser marcado acabado quando a pizza nova ficar acabada. Não há perda nem baixa de estoque em dobro; a pizza nova baixa a ficha técnica quando ficar acabada.

**Pedidos em aberto:** mostra, por pedido, quantas pizzas já estão acabadas. Quando todas estiverem acabadas, toque em **Marcar pedido acabado**. Bebidas e acompanhamentos não são contados como pizzas. Pedido só com bebida ou acompanhamento aparece com "0 de 0": separe os itens e toque em **Marcar pedido acabado**.

Atenção: o teste da impressora térmica Bluetooth ainda está pendente. Se a etiqueta não imprimir, avise a gerência.

## 3. Despacho (pedidos de entrega)

O despacho exige o **caixa do dia aberto** pela recepção. Se não estiver, a tela avisa e não deixa despachar.

1. Em **Entregas de hoje**, ache o pedido.
2. Escolha o **entregador** na lista.
3. Toque em **Despachar**. Isso registra o entregador. Quem marca o pedido como "despachado" é a recepção, em Pedidos do dia, quando o entregador sai.

O **valor por entrega** (o que a loja paga ao entregador, diferente da taxa cobrada do cliente) é sempre o padrão da loja. Hoje a tela usa sempre o valor padrão; valor diferente não tem tela. Pedido que já tem entregador mostra o nome dele.

## 4. O que você não vê

O valor do pedido, o total, o pagamento e os dados de contato do cliente. Isso é proposital: o despacho funciona sem valores.

## 5. O que acontece no Anota Ai

Para pedidos que vieram do Anota Ai, o sistema avisa o cliente sozinho: na **retirada**, "pronto" quando o pedido fica acabado; na **entrega**, "pronto" quando o entregador sai. Isso só funciona quando a integração estiver conectada (pendente do token do Anota Ai).
