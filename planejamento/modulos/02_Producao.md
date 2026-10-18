# Detalhamento 02: Produção

Versão 0.2, 18/10/2026. Reescrito a partir da explicação completa de Marlon. Rascunho para discussão. Parte do [Plano Macro](../00_Plano_Macro.md). Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), aprovado em 18/10/2026.

**Critério de sucesso:** Marlon lê o fluxo, as fases e os dados e diz "é assim" ou corrige; as perguntas da seção 9 ficam respondidas antes de qualquer desenho de tela.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- O módulo roda sobre uma **API interna nossa**, em segundo plano num dos PCs. Os tablets a alimentam, chamando-a a cada fase executada **[Decisão, 18/10/2026]**.
- O pedido pode entrar de forma manual no nosso sistema ou por API de um aplicativo de venda; Produção funciona igual nos dois casos **[Decisão, 18/10/2026]**.
- Cada função (massa, pizzaiolo, acabamento) tem um comportamento próprio no aplicativo móvel, e cada colaborador tem login próprio **[Decisão A5 e C6]**.
- Equipamentos: 1 tablet na massa, 2 no pizzaiolo, 1 no acabamento com impressora **[Decisão P9]**; impressora térmica portátil com etiqueta autoadesiva, modelo variável **[Decisão A6]**; a etiqueta leva sabor, número do pedido, cliente e observações **[Decisão E2]**.
- OP por pedido e também por lote de pré-preparo, pedido primeiro **[Decisão P7]**.
- Só retirada e entrega; o entregador é terceiro **[Decisão B3 e B4]**.

---

## 2. Objetivo

Levar cada pizza do pedido até a retirada ou o despacho, mostrando a cada pessoa só o que a sua função precisa, calculando a necessidade de massa, estimando a hora da entrega e registrando tempos, responsáveis e perdas.

---

## 3. Como o módulo se liga (arquitetura)

- Uma **API interna** roda em segundo plano num dos PCs da recepção. Os tablets da massa, do pizzaiolo e do acabamento, e a tela do balcão, falam com ela pela rede da loja **[Decisão]**.
- O pedido entra por duas portas: digitado no balcão ou vindo de um aplicativo de venda (Anota Aí e outros). Nas duas, o pedido tem os mesmos dados e dispara o mesmo fluxo **[Decisão]**.
- Isso combina com o plano: um servidor local, os demais aparelhos como clientes, e só os canais externos dependendo de internet **[Prática]**.
- Falta definir qual PC é o servidor, como a API inicia sozinha quando o PC liga e o que se faz se esse PC parar (pergunta H11).

---

## 4. O fluxo em 5 passos, como Marlon descreveu

1. **Entra o pedido**, com os dados da seção 6.
2. **Gera a necessidade total de massas abertas por tamanho.** Pode existir estoque de massa aberta, que abate a necessidade.
3. **Gera a lista de pizzas para montagem** (grande, broto ou calzone).
4. **Gera o checklist de produção** para o acabamento e o despacho interno.
5. **Gera o checklist de entrega**, no balcão ou no despacho para o motoboy.

---

## 5. Fases, por função

### 5.1 Massa (duas fases) **[Decisão]**

- **Fase 1, preparo das massas:** bater, bolear e deixar crescer. O operador lança o **total de massas por tamanho** (Grande ou Broto). Essas massas também podem ser usadas para calzone.
- **Fase 2, produção de massas abertas e de massas com borda:** a necessidade é gerada a partir dos pedidos que **ainda não entraram em produção**. Pode existir estoque de massa aberta.
- Perdas de massa por vários motivos são registradas com o motivo **[Decisão A5]**.

### 5.2 Montagem, o pizzaiolo **[Decisão]**

- Recebe **sempre a próxima pizza** para montagem. A lista pega os pedidos um a um e coloca os itens nela.
- Pode **retroceder a pizza atual uma posição** na lista, para o caso de falta momentânea de algum insumo.
- Ao marcar como **produzida**, a pizza entra automaticamente **"no forno"**; essa lista alimenta o acabamento.

### 5.3 Pedido urgente **[Decisão]**

- O balcão (Vendas) pode inserir um pedido como **urgente**: ele vai para o topo da lista, e o sistema **refaz a lista toda, menos os itens que já estão em produção**.

### 5.4 Acabamento **[Decisão]**

- Enxerga **duas listas:** todos os pedidos em aberto (só consulta) e os pedidos ligados às pizzas que estão no forno.
- Marca cada pizza como **acabada** depois de sair do forno, receber o acabamento e ser empacotada.
- Quando as pizzas do pedido terminam, marca o pedido original como **acabado**, e ele vai para a lista de **despacho** ou de **retirada**, conforme o pedido identifica.

---

## 6. Dados que Marlon definiu

### 6.1 Pedido **[Decisão]**

| Campo | Observação |
|---|---|
| Id | Único, sequencial, universal |
| Id do dia | Único e sequencial dentro do dia (igual ao número do pedido de Vendas, B7) |
| Id no aplicativo de venda | Código do pedido no Anota Aí, iFood ou outro |
| Aplicativo de venda | Anota Aí, iFood ou outro |
| Cliente | Nome, WhatsApp e outros |
| Data e hora do pedido | |
| Data e hora de entrega calculada | Calculada pela quantidade de pedidos na frente vezes o tempo médio de preparo total (ver 8.6) |
| Data e hora de entrega sugerida | Ver pergunta H4 |
| Data e hora de entrega real | |
| Tempo total de preparo | |
| Retirada ou entrega | |
| Observações gerais | |

### 6.2 Itens do pedido **[Decisão]**

| Campo | Observação |
|---|---|
| Sequência | Número do item dentro do pedido |
| Produto | Pizza Grande, pizza Broto, calzone, refrigerante, acompanhamento e outros |
| Sabor 1 | Para pizza Grande, Broto ou calzone |
| Sabor 2 | Só para pizza Grande |
| Observações do item | |

### 6.3 Dados que o fluxo gera **[Suposição de nome e campos]**

| Registro | O que guarda |
|---|---|
| Pizza a produzir | Item de origem, sabor(es), tamanho, borda, situação, hora de cada etapa, quem fez cada etapa |
| Lista de montagem | Ordem das pizzas aguardando; o que cada pizzaiolo está montando |
| Lote de massa (fase 1) | Tamanho, quantidade, responsável, hora |
| Estoque de massa aberta | Quantidade por tamanho e tipo (normal ou com borda) |
| Necessidade de massa (fase 2) | Calculada dos pedidos que não entraram em produção, menos o estoque; é consulta, não cadastro |
| Perda de massa | Quantidade, motivo, quem registrou |
| Evento de etapa | Mudança de etapa com usuário e hora, só inserção (auditoria) |
| Etiqueta | O que foi impresso, quando e por quem |

**Quem é dono de quê [Prática].** O pedido e os itens nascem em Vendas e continuam sendo de Vendas. Hora de entrega calculada, real, tempo total de preparo e todas as etapas são de Produção, ligadas ao pedido pelo Id. Assim cada módulo escreve só nas suas tabelas.

---

## 7. Situações propostas **[Suposição]**

| Objeto | Situações |
|---|---|
| Pizza | na lista, em montagem, no forno, acabada, perdida |
| Pedido | recebido, em produção, acabado, despachado ou retirado, cancelado |

---

## 8. O que verifiquei no que foi explicado

Conferi o fluxo com o que já está aprovado em Núcleo e Vendas. Seis pontos pedem uma decisão:

1. **Borda e adicional não aparecem nos itens.** Vendas decidiu que há bordas e adicionais cobrados à parte, e a fase 2 da massa trata massas com borda. Mas a tabela de itens de Produção só tem produto, sabores e observações. Onde a borda e os adicionais ficam registrados? Recomendo campos próprios no item, não texto livre (pergunta H1).
2. **Calzone, refrigerante e acompanhamento são produtos novos para Vendas.** O cardápio aprovado só fala de pizzas Grande e Broto. Precisam entrar no cadastro de produtos, com preço (pergunta H1).
3. **iFood aparece como aplicativo de venda.** Até agora os canais eram balcão e Anota Ai. O iFood vem pelo Anota Aí ou é um canal separado? (pergunta H2).
4. **"Id universal" e um banco por loja.** Um número sequencial só é único dentro de um banco. Para valer entre lojas, recomendo guardar o identificador da loja junto do Id, ou usar um identificador único global (pergunta H3). Não precisa agora, porque há uma loja só, mas decide o desenho da tabela.
5. **A estimativa de entrega por "pedidos na frente vezes tempo médio" pode errar.** Um pedido de 1 pizza e outro de 6 pesam igual, e dois pizzaiolos trabalham em paralelo. Recomendo estimar por **pizzas na frente**, dividir pelo número de pizzaiolos ativos e somar forno, acabamento e deslocamento da entrega. O tempo médio sai do histórico real da própria loja [Prática]. Preciso do seu aval (pergunta H4).
6. **Quando o pizzaiolo retrocede a pizza,** a falta de insumo some do registro, e ela é uma informação valiosa para Estoques. Recomendo pedir o motivo ao retroceder e avisar Estoques [Prática] (pergunta H5).

---

## 9. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Vendas | Pedido e itens entram em Produção | Vendas para Produção |
| Vendas | Pedido urgente, vindo do balcão | Vendas para Produção |
| Vendas | Situação do pedido e hora de entrega real | Produção para Vendas |
| Estoques | Consumo de insumos e de massa; perdas; falta de insumo ao retroceder | Produção para Estoques |
| Custos | Perdas de massa e de pizza, para o CMV real | Produção para Custos |
| BI | Tempos por etapa, atrasos, refações | Produção para BI |
| Impressora | Etiqueta | Produção para a impressora |

Como em todo o plano, cada ligação tem forma manual para o módulo funcionar sozinho **[Prática]**.

---

## 10. Perguntas

### 10.1 Das perguntas anteriores (G1 a G13)

| # | Situação |
|---|---|
| G1 massa aberta normal | Respondida: a fase 2 gera massas abertas e massas com borda, por tamanho |
| G2 onde se faz a borda | Respondida: na fase 2 da massa. A lista de bordas vem com o cadastro (D2) |
| G3 quando entra na fila | Respondida em parte: ao entrar o pedido. Falta saber se existe pedido agendado (H6) |
| G4 ordem da fila | Respondida: ordem de chegada, com pedido urgente no topo |
| G5 forno | Respondida: a pizza entra no forno ao ser marcada como produzida; a saída é do acabamento. Falta o número de fornos (H7) |
| G6 saída do pedido | Respondida em parte: o acabamento marca o pedido como acabado. Faltam os itens que não são pizza e quem marca a entrega (H8) |
| G7 perdas | Em aberto (H9) |
| G8 refação | Em aberto (H10) |
| G9 impressora | Em aberto: falta o momento da impressão e a conexão (H8 e H11) |
| G10 cancelamento em produção | Em aberto (H10) |
| G11 meta de tempo | Respondida em parte: o tempo médio entra na estimativa (H4) |
| G12 pré-preparo em lote | Respondida em parte: o lote de massa é a fase 1. Falta saber se há outros lotes (H9) |
| G13 internet | Respondida: a API roda num PC e os tablets usam a rede local |

### 10.3 Respondidas por Marlon em 18/10/2026

Pontos de verificação da seção 8:
1. **Borda é um adicional** (assim como cheddar extra, catupiri extra ou qualquer insumo extra). Todo extra é um adicional com valor somado ao item vendido. Não existe campo "borda" separado: o item leva uma lista de adicionais **[Decisão]**.
2. **O cardápio é montado aqui e exportado ao Anota Aí**, incluindo pizzas, calzones e bebidas **[Decisão]**.
3. **iFood**: uso futuro, no mesmo modelo do "Pedidos 10" (um canal a mais, via adaptador) **[Decisão]**.
4. **Id universal**: o identificador da loja vai junto do Id **[Decisão]**.
5. **Estimativa por pizzas na frente** (dividido pelos pizzaiolos ativos) **[Decisão]**.
6. **Retroceder exige motivo**, escolhido numa tabela: falta de insumo, saída inesperada do pizzaiolo, erro na borda, outros **[Decisão]**. Falta de insumo avisa Estoques.

Perguntas: H1 sim, H2 sim, H3 sim, H4 sim, H5 sim. H8, em parte: a pizza **entregue** é marcada no balcão; no acabamento a pizza fica finalizada ao fim de "acabar" **[Decisão]**.

H8, fechada: o pedido é marcado como acabado **obrigatoriamente à mão** (nunca sozinho); refrigerante e acompanhamento **não** entram no checklist do acabamento; a etiqueta é **uma por pizza**, com nome do cliente, Id do pedido e nome do sabor **[Decisão]**. Abertas: H6, H7 e H9 a H12.

### 10.2 Novas

- **H1.** Borda e adicional: onde entram no item? Calzone, refrigerante e acompanhamento: precisam de preço no cadastro; o calzone tem um tamanho só? Quais acompanhamentos existem?
- **H2.** iFood: vem pelo Anota Aí ou é um canal separado?
- **H3.** "Id universal": único entre lojas? Recomendo a loja junto do Id.
- **H4.** Hora de entrega calculada x sugerida: qual a diferença e quem vê cada uma? O tempo médio de preparo é digitado ou vem do histórico? Aceita a estimativa por pizzas na frente?
- **H5.** Ao retroceder a pizza, ela volta uma posição? O sistema pergunta o motivo, por exemplo "falta de insumo"? Recomendo que sim.
- **H6.** Existe pedido agendado para um horário futuro? Quem pode marcar um pedido como urgente?
- **H7.** Quantos fornos a loja tem?
- **H8.** No acabamento, o pedido é marcado como acabado à mão ou sozinho quando todas as pizzas ficam acabadas? Refrigerante e acompanhamento entram no checklist do acabamento? Quem marca como entregue ou retirado e grava a hora de entrega real: o balcão ou o despacho? Quando a etiqueta é impressa: ao marcar a pizza como acabada, e uma por pizza ou uma por pedido?
- **H9.** Quais os motivos de perda de massa, e há perda de pizza pronta (queimou, saiu errada, caiu)? Há outros preparos em lote além da massa, como molho?
- **H10.** Refação (pizza errada ou reclamação) e cancelamento de pedido já em produção: como registrar? Recomendo nova pizza ligada à original, com motivo, e perda registrada para o que já foi feito.
- **H11.** Qual PC é o servidor, a API inicia sozinha ao ligar o PC, e como a impressora conecta ao tablet (Wi-Fi, Bluetooth ou cabo)? Há Wi-Fi na cozinha?
- **H12.** Fase 1 da massa: quem lança o total (a função massa), gasta farinha e outros insumos pela ficha técnica, e o estoque de massa aberta é contado e informado pelo operador?

---

## 11. O que este documento ainda não cobre

- Desenho de telas dos tablets e fluxo de cliques.
- Tabelas finais e regras de cálculo da necessidade de massa e da estimativa de entrega.
- Ficha técnica da massa e dos preparos (depende de Estoques e Custos).
