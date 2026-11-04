# Manual do Usuário: Caixa do dia e acerto dos entregadores

Versão 2.0, 04/11/2026. Para quem opera o caixa: atendente e gerência. Leia antes o [manual comum](00_Comum_a_Todos.md).

**Tela:** Vendas > **Caixa e entregas**, com as abas **Caixa do dia**, **Entregas** e **Motivos e maquininhas**.

**Regras da loja:** um caixa por dia e uma gaveta. A contagem é **cega**: você informa o que contou antes de ver o valor esperado. O caixa vai da abertura até o fechamento, mesmo que a loja venda depois da meia-noite.

## 1. Abrir o caixa

1. Conte o dinheiro da gaveta.
2. Em **Caixa do dia**, informe o **fundo de troco** e toque em **Abrir caixa**.

O fundo de troco padrão vem dos parâmetros. Valor diferente só a gerência define. Não é possível abrir um caixa novo se o anterior não foi fechado.

Sem caixa aberto: o acabamento não despacha, a recepção não atribui nem acerta entregas e, se o parâmetro mandar, não há venda.

## 2. Sangria e suprimento

- **Sangria (saída):** dinheiro que sai da gaveta (exemplo: pagar uma despesa ou levar para o cofre).
- **Suprimento (entrada):** dinheiro que entra na gaveta (exemplo: reforço de troco).

Escolha o tipo, o motivo e o valor. Motivo marcado como "vira despesa" exige o comprovante (número ou descrição). Se a soma das sangrias passar do limite do parâmetro, um gerente autoriza com login e senha.

Os motivos são cadastrados em **Motivos e maquininhas** (na primeira vez, a gerência toca em "Criar os motivos combinados"; só a gerência cria e altera motivos).

## 3. Entregas e acerto do entregador

**Entregas de hoje:** lista os pedidos de entrega. O despacho (escolher o entregador) é feito pelo acabamento ou aqui. Atribuir não muda a situação: quando o entregador sair, marque o pedido como despachado em Pedidos do dia.

**Acerto do entregador:** o entregador devolve o dinheiro que recebeu dos clientes e recebe o valor das entregas mais a diária (uma vez por dia). Só entram pedidos já marcados como **despachado ou retirado**. Escolha o entregador e confirme. A diária vem do parâmetro; valor diferente só a gerência define.

Para pedidos do Anota Ai, o acerto do entregador também **finaliza** os pedidos dele no Anota Ai (quando a integração estiver conectada). Por isso pedido de entrega do Anota Ai só pode ser marcado como despachado depois de ter o entregador atribuído.

## 4. Contagem do fim do dia

1. Acerte **todos** os entregadores antes. Com entrega sem acerto, o sistema não aceita a contagem.
2. Em **Contagem do fim do dia**, informe o que há de fato em cada forma: dinheiro da gaveta, extrato do Pix, comprovantes das maquininhas (crédito e débito). Use 0 quando não houver nada.
3. Toque em **Registrar contagem** e confirme. **A contagem não pode ser refeita.**
4. Só agora o sistema mostra o **esperado** e a **diferença** de cada forma.

Depois da contagem, o caixa não aceita novos pedidos nem cancelamentos.

## 5. Fechar o caixa

1. Confira o **Resultado da contagem**.
2. Se a diferença passar da **tolerância**, escreva a **justificativa** e peça a um gerente, proprietário ou administrador que **não fez a contagem** para aprovar com login e senha. Subgerente não aprova diferença.
3. Toque em **Fechar o caixa**.

## 6. Pedidos sem número de CF

Na tela Caixa do dia aparece a lista de pedidos sem o número do cupom fiscal. Digite o número emitido no outro software e toque em **Salvar**.

## 7. Maquininhas e regras de recebimento (gerência)

Em **Motivos e maquininhas** a gerência cadastra as maquininhas e a taxa e o prazo de recebimento de cada forma. Cada regra nova vale dali para frente; o histórico fica guardado. O atendente só consulta.
