# Detalhamento 02: Produção

Versão 0.1, 18/10/2026. Rascunho para discussão, escrito só com o que Marlon explicou até agora. Parte do [Plano Macro](../00_Plano_Macro.md). Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), aprovado por Marlon em 18/10/2026.

**Critério de sucesso:** Marlon lê o fluxo, as visões por função e os dados e diz "é assim" ou corrige; as perguntas da seção 7 ficam respondidas antes de qualquer desenho de tela.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Produção é um módulo separado e especial; Marlon explicará os detalhes **[Decisão]**.
- Ordem de produção (OP) por pedido e também por lote de pré-preparo, pedido primeiro **[Decisão P7]**.
- O aplicativo móvel tem comportamento diferente em cada função (massa, pizzaiolo, acabamento), e cada colaborador tem login próprio **[Decisão A5 e C6]**.
- Equipamentos planejados: 1 tablet na massa, 2 no pizzaiolo e 1 no acabamento, este com impressora **[Decisão P9]**.
- A impressora é térmica portátil, com etiqueta autoadesiva; o modelo varia **[Decisão A6]**.
- A etiqueta leva sabor, número do pedido, cliente e observações **[Decisão E2]**.
- O pedido nasce em Vendas; o número do pedido reinicia por dia **[Decisão B7]**.
- Só há retirada e entrega; o entregador é terceiro **[Decisão B3 e B4]**.
- Perdas de massa por vários motivos precisam ser registradas **[Decisão A5]**.

---

## 2. Objetivo

Levar cada pizza do pedido até o balcão de saída, mostrando a cada pessoa só o que a sua função precisa, registrando tempos, responsáveis e perdas, e avisando Vendas, Estoques e BI do que aconteceu.

---

## 3. Fluxo, com o que Marlon explicou

A unidade de trabalho é a **pizza**, não o pedido: o pedido é dividido em pizzas, e as pizzas entram numa fila **[Decisão A5]**.

1. **Vendas confirma o pedido.** Cada pizza do pedido vira um item na fila de produção **[Suposição: o momento exato da entrada na fila está na pergunta G3]**.
2. **Massa.** Vê as bordas por pedido e a quantidade de massas abertas normais que a fila exige. A massa é maleável: pode ser produzida antes da necessidade **[Decisão A5]**.
3. **Pizzaiolo.** Vê só a pizza que precisa produzir, não o pedido. As pizzas são solicitadas em sequência, não importa quantos pizzaiolos haja. Quando o pizzaiolo confirma a manufatura, a pizza segue para o forno **[Decisão A5]**.
4. **Forno.** A pizza fica no forno depois da confirmação do pizzaiolo **[Decisão A5; quem registra a entrada e a saída está na pergunta G5]**.
5. **Acabamento.** Vê os pedidos e as pizzas que estão no forno, e imprime a etiqueta de identificação **[Decisão A5 e A6]**.
6. **Saída.** Retirada pelo cliente ou entrega pelo entregador terceiro **[Suposição: onde e quem registra a saída está na pergunta G6]**.

---

## 4. Visão de cada função no aplicativo móvel

| Função | Vê | Faz | Origem |
|---|---|---|---|
| Massa | Bordas por pedido; quantidade de massas abertas normais necessárias | Registra a massa produzida e as perdas, com motivo | [Decisão A5] |
| Pizzaiolo | Só a pizza a produzir: sabor(es), tamanho, borda, adicionais [Suposição: e as observações da pizza] | Pede a próxima pizza da fila; confirma a manufatura | [Decisão A5] |
| Acabamento | Pedidos e as pizzas deles que estão no forno | Confere, imprime a etiqueta e libera [Suposição: a liberação] | [Decisão A5 e A6] |

Regras de comportamento que proponho **[Prática]**:

- **Pedir a próxima pizza é uma operação única:** quando dois pizzaiolos pedem ao mesmo tempo, o sistema entrega pizzas diferentes, nunca a mesma. Cada confirmação registra quem, quando e qual pizza.
- **Nenhuma função vê valores** de venda nem dados pessoais do cliente, exceto o que a etiqueta exige (E2).
- **Login pessoal em todas as funções** (C6): cada tablet entra com a pessoa do turno; trocar de pessoa exige novo login, para a auditoria saber quem fez cada etapa.

---

## 5. Dados guardados (candidatos)

| Registro | O que guarda |
|---|---|
| Pizza a produzir | Pedido de origem, número do pedido do dia, sabor(es), tamanho, borda, adicionais, observações, situação, hora de cada etapa, quem fez cada etapa |
| Fila de produção | Ordem das pizzas aguardando; o que cada pizzaiolo puxou |
| Necessidade de massa | Calculada da fila: massas abertas normais e bordas por pedido (não é cadastro, é consulta) |
| Perda de massa | Quantidade, motivo, quem registrou, quando |
| Evento de etapa | Cada mudança de etapa com usuário e hora, só inserção (auditoria) |
| Etiqueta | O que foi impresso (sabor, número do pedido, cliente, observações), quando e por quem |
| Lote de pré-preparo | Preparo (massa, molho, outros), quantidade produzida, responsável, data; consome insumos e gera saldo de preparo |

Situações propostas para a pizza **[Suposição]**: na fila, em produção (puxada pelo pizzaiolo), no forno, pronta, entregue ao cliente ou ao entregador, perdida, refeita.

---

## 6. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Vendas | Pedido confirmado vira pizzas na fila | Vendas para Produção |
| Vendas | Situação do pedido (por exemplo, pronto) | Produção para Vendas |
| Estoques | Consumo de insumos pela ficha técnica; consumo e perda de massa | Produção para Estoques |
| Custos | Perdas (massa e pizza), para o CMV real | Produção para Custos |
| BI | Tempo em cada etapa, atrasos, refações | Produção para BI |
| Impressão | Etiqueta no acabamento | Produção para a impressora |

Como em todo o plano, cada ligação tem forma manual para o módulo funcionar sozinho: sem Estoques, o consumo simplesmente não é baixado **[Prática]**.

**Impressora [Prática].** Como o modelo varia, o sistema terá uma camada de impressão separada do conteúdo da etiqueta: o conteúdo é sempre o mesmo, e cada modelo ganha o seu "driver". Como a impressora conecta (Wi-Fi, Bluetooth, cabo) define o desenho; está na pergunta G9.

---

## 7. Perguntas em aberto

As cinco primeiras travam o desenho do fluxo; as demais podem esperar.

- **G1.** O que é a "massa aberta normal"? Qual a diferença para a massa da pizza com borda? A Broto usa massa própria?
- **G2.** A borda é feita na estação da massa, e quais bordas existem (a lista de bordas entra com o cadastro, D2)?
- **G3.** Quando o pedido entra na fila: assim que é confirmado, ou só depois do pagamento? Existe pedido agendado para um horário futuro?
- **G4.** Qual a ordem da fila? Recomendo ordem de chegada, com o gerente podendo priorizar um pedido.
- **G5.** Quantos fornos há? Quem registra a pizza entrando no forno e quem registra a saída: o pizzaiolo, o acabamento ou o próprio sistema ao confirmar?
- **G6.** O pedido só sai quando todas as pizzas estão prontas? Há bebidas e outros produtos no pedido, e passam pela produção? Quem registra a saída para o cliente ou o entregador?
- **G7.** Quais são os motivos de perda de massa? Há perda de pizza pronta (queimou, saiu errada, caiu)? Quem registra?
- **G8.** Refação (pizza errada ou reclamação): como registrar? Recomendo uma nova pizza ligada à original, com motivo.
- **G9.** Como a impressora conecta ao tablet do acabamento: Wi-Fi, Bluetooth ou cabo? Há Wi-Fi na cozinha?
- **G10.** Cancelamento de pedido já em produção: as pizzas já feitas viram perda registrada?
- **G11.** Há meta de tempo por etapa, com alerta de atraso?
- **G12.** Pré-preparo em lote: quais preparos existem (massa em bolas, molho, cortes) e como são feitos hoje?
- **G13.** Se a internet cair, a produção continua? Recomendo que sim: tablets e servidor conversam pela rede local da loja, e só o Anota Ai depende de internet.

---

## 8. O que este documento ainda não cobre

- Desenho de telas dos tablets e fluxo de cliques.
- Tabelas finais e regras de cálculo da necessidade de massa.
- Ficha técnica da massa e dos preparos (depende de Estoques e Custos).
