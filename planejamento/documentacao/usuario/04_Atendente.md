# Manual do Usuário: Atendente (recepção)

Versão 2.0, 04/11/2026. Leia antes o [manual comum](00_Comum_a_Todos.md). O caixa do dia tem manual próprio: [05_Caixa.md](05_Caixa.md).

**A sua área:** 🧾 Vendas. Telas: **Pedidos** (Novo pedido e Pedidos do dia), **Caixa e entregas**, **Clientes**, **Entregadores** (consulta). Você também consulta o **Cardápio** (Administrativo > Cardápio). Você não acessa Produção: a hora de entrega calculada aparece em Pedidos do dia.

## 1. Fazer um pedido (Vendas > Pedidos > Novo pedido)

1. Escolha **Retirada** ou **Entrega**.
2. **Cliente:** digite o telefone com DDD. Se o cliente existe, o sistema o encontra. Se não existe, cadastre na hora (nome, telefone e, para entrega, endereço) e toque em **Cadastrar e usar**. Retirada pode ficar **Sem cliente (balcão)**. Entrega exige cliente com endereço.
3. **Itens:**
   - Pizza: escolha o tamanho (Grande ou Broto) e o sabor. **Sabor 2** só existe na Grande: a Grande com 2 sabores custa metade do preço de cada sabor.
   - **Borda:** no máximo uma por pizza. **Adicionais:** quantos quiser, cada um com preço.
   - **Observação do item** (exemplo: sem cebola) e **Quantidade**.
   - Calzone, bebida e acompanhamento: escolha o produto e a quantidade.
   - Toque em **Adicionar ao pedido**. Repita para cada item.
4. **Taxa de entrega** (cobrada do cliente): vem o valor padrão. Valor diferente exige o motivo. Taxa **menor** que a padrão sempre exige a autorização de um gerente ou subgerente, com login e senha.
5. **Desconto ou acréscimo:** escolha o tipo, o valor e o motivo e toque em **Aplicar ajuste**. Desconto acima do seu limite exige um gerente ou subgerente, que digita o login e a senha na hora (o desconto precisa caber no limite dele).
6. **Pagamento:** escolha a forma (dinheiro, Pix, crédito ou débito) e o valor. Pode dividir em mais de uma forma. Só o dinheiro tem troco. O sistema mostra "Falta receber" até fechar o total. **Não existe fiado**: o pedido só é confirmado pago por completo.
7. Marque **Pedido urgente** se for o caso, escreva observações do pedido e toque em **Confirmar pedido**.

As pizzas entram sozinhas na fila da produção. Bebidas e acompanhamentos não passam pela cozinha.

Se a loja estiver configurada para vender só com caixa aberto, abra o caixa antes do primeiro pedido.

## 2. Acompanhar os pedidos (Vendas > Pedidos > Pedidos do dia)

- **Ver como:** quadro (uma coluna por situação) ou lista.
- Situações: recebido, em produção, acabado, despachado ou retirado, cancelado.
- Cada pedido mostra o tipo, o cliente, o total e a **hora de entrega calculada**.
- Ações:

| Botão | Quando |
|---|---|
| **Avançar para despachado ou retirado** | O cliente retirou no balcão, ou o entregador saiu com o pedido. Só depois de o acabamento marcar o pedido acabado. Entrega do Anota Ai exige o entregador atribuído antes |
| **Urgente** ou **Tirar urgência** | Só enquanto o pedido está "recebido" (antes de a produção começar) |
| **Cancelar** | Motivo obrigatório. Como todo pedido está pago, um gerente confirma com login e senha. O valor fica registrado como estorno no caixa do dia, por forma de pagamento; a devolução ao cliente (dinheiro, Pix ou estorno na maquininha) é feita fora do sistema |
| **Ver** | Detalhes do pedido, pagamentos e histórico |

## 3. Entregas

O despacho (atribuir o entregador) normalmente é feito pelo **acabamento**. A recepção também pode atribuir em **Caixa e entregas > Entregas**. Atribuir **não** muda a situação do pedido: quando o entregador sair, toque em **Avançar para despachado ou retirado** em Pedidos do dia. É a recepção que faz o **acerto do entregador**. Veja o [manual do caixa](05_Caixa.md).

## 4. Clientes

Em **Clientes** você busca, cadastra e corrige nome, telefone e endereço. Cadastre o cliente na primeira compra.

## 5. Pedidos do Anota Ai

**Hoje** a integração não está conectada (falta o token e a documentação da API). Continue atendendo o Anota Ai pelo aplicativo dele, como hoje, e aceite o pedido lá em até 15 minutos (senão o Anota Ai cancela). Para o pedido ir para a cozinha, digite-o aqui em Novo pedido.

**Sabor com venda fechada:** quando a gerência fecha um sabor por falta de ingrediente, o balcão **não** é bloqueado pelo sistema. Siga o aviso da gerência e não venda o sabor. Quando a integração for conectada, os pedidos do Anota Ai entrarão sozinhos e seguirão o mesmo caminho; a fila de entrada do canal é da gerência (Vendas > Canais).

## 6. Cupom fiscal

O cupom fiscal é emitido em outro software. Depois, informe o número do CF no sistema em **Caixa e entregas > Caixa do dia > Pedidos sem número de CF**.
