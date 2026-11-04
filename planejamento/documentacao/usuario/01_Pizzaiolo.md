# Manual do Usuário: Pizzaiolo

Versão 2.0, 04/11/2026. Leia antes o [manual comum](00_Comum_a_Todos.md).

**A sua tela:** Produção > **Montagem**. É a única tela da sua função. O forno, o acabamento e o despacho são da função acabamento.

**A unidade de trabalho é a pizza**, não o pedido. Cada pizza (ou calzone) entra na fila sozinha.

## 1. A tela Montagem

- **Pizza atual:** a pizza que está com você, com tamanho, sabores, número do pedido, adicionais (borda, extras) e observações.
- **Fila:** as próximas pizzas na lista. Pedido urgente aparece com ⚡ e vem antes.
- A lista se atualiza sozinha a cada 8 segundos (não atualiza enquanto você escolhe um motivo).

## 2. Montar uma pizza

1. Toque em **Pegar a próxima pizza**. O sistema dá a próxima da fila para você.
2. Leia sabores, tamanho, borda, adicionais e observações.
3. Monte a pizza.
4. Toque em **Produzida (vai ao forno)**. A pizza sai da sua tela e vai para o forno.

Você trabalha uma pizza por vez. Só pega a próxima depois de marcar a atual.

## 3. Quando algo dá errado

| Situação | O que fazer |
|---|---|
| Não dá para montar agora (exemplo: falta um ingrediente na bancada) | Em **Retroceder**, escolha o motivo. A pizza volta uma posição na fila. O motivo é obrigatório |
| A pizza estragou na montagem | Em **Perdeu a pizza**, escolha o motivo e confirme. A pizza vira perda. **Avise a gerência na hora.** O acabamento ou a gerência toca em **Refazer** e uma pizza igual volta para a sua fila, **na frente**. Em implementação: botões próprios do pizzaiolo para montagem errada no sabor, problema no formato ou esteira e falta de ingrediente; este manual será atualizado quando entrarem |

Retroceder e perder ficam registrados com o seu nome e o motivo. A gerência vê isso nos relatórios. Os motivos são cadastrados pela gerência.

## 4. O que você não vê

Valores do pedido, dados do cliente, outras etapas da cozinha e o andamento geral. Isso é proposital.
