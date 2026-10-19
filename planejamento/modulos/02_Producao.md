# Detalhamento 02: Produção

Versão 0.3, 18/10/2026. Consolidada com todas as respostas de Marlon (G1 a G13 e H1 a H12). **APROVADA por Marlon em 19/10/2026.** Parte do [Plano Macro](../00_Plano_Macro.md). Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), aprovado em 18/10/2026.

**Critério de sucesso:** Marlon lê o documento e diz "aprovado" ou aponta o que corrigir. Aprovado, o módulo segue para o desenho das tabelas e das telas dos tablets.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. Decisões que sustentam o módulo

- Roda sobre uma **API interna nossa**, em segundo plano num dos PCs. Os tablets a alimentam, chamando-a a cada fase executada **[Decisão]**.
- O pedido entra de forma manual no nosso sistema ou por API de um aplicativo de venda, com os mesmos dados, e dispara o mesmo fluxo **[Decisão]**.
- Cada função (massa, pizzaiolo, acabamento) tem comportamento próprio no aplicativo móvel, e cada colaborador tem login próprio **[Decisão]**.
- Equipamentos: 1 tablet na massa, 2 no pizzaiolo, 1 no acabamento com impressora térmica portátil de etiqueta, modelo variável **[Decisão]**.
- A unidade de trabalho é a **pizza**, não o pedido **[Decisão]**.
- Só retirada e entrega; o entregador é terceiro **[Decisão]**.
- Produção grava só nas suas tabelas; o pedido e os itens continuam sendo de Vendas **[Prática]**.

---

## 2. Objetivo

Levar cada pizza do pedido até a retirada ou o despacho, mostrando a cada pessoa só o que a sua função precisa, calculando a necessidade de massa, estimando a hora da entrega e registrando tempos, responsáveis e perdas.

---

## 3. Arquitetura

- Uma API interna roda em segundo plano num PC da recepção. Tablets da massa, do pizzaiolo e do acabamento e a tela do balcão falam com ela pela rede da loja **[Decisão]**.
- **Contingência [Decisão, H11]:** os dois PCs da recepção devem poder servir a API, e a impressora deve aceitar mais de uma forma de conexão (Wi-Fi, mais Bluetooth ou cabo). Marlon confirmou esta leitura.
- A API inicia sozinha quando o PC liga [Prática]. Como o segundo PC assume se o primeiro parar entra no desenho técnico.
- Só os canais externos (Anota Aí, iFood futuro) dependem de internet; a produção continua sem ela **[Decisão]**.

---

## 4. O fluxo em 5 passos

1. **Entra o pedido**, com os dados da seção 6.
2. **Gera a necessidade total de massas abertas por tamanho.** O estoque de massa aberta abate a necessidade.
3. **Gera a lista de pizzas para montagem** (Grande, Broto ou calzone).
4. **Gera o checklist de produção** para o acabamento e o despacho interno.
5. **Gera o checklist de entrega**, no balcão ou no despacho para o motoboy.

---

## 5. Fases, por função

### 5.1 Massa (duas fases) **[Decisão]**

- **Fase 1, preparo:** bater, bolear e deixar crescer. A função massa lança o **total de massas por tamanho**. Essas massas também servem ao calzone. O sistema baixa farinha e demais insumos pela ficha técnica, e o operador conta e informa o estoque de massa aberta (H12).
- **Fase 2, massas abertas e massas com borda:** a necessidade vem dos pedidos que **ainda não entraram em produção**, menos o estoque de massa aberta.
- **Perdas** de massa e de pizza pronta (queimou, saiu errada, caiu) são registradas com motivo em tabela (H9). **A massa é o único preparo em lote**; não há outros (H9).

### 5.2 Montagem, o pizzaiolo **[Decisão]**

- Recebe **sempre a próxima pizza**. A lista pega os pedidos um a um e coloca os itens nela.
- Pode **retroceder a pizza atual uma posição**, para falta momentânea de insumo. O motivo é **obrigatório**, de uma tabela: falta de insumo, saída inesperada do pizzaiolo, erro na borda, outros. Falta de insumo avisa Estoques (H5).
- Ao marcar como **produzida**, a pizza entra automaticamente **"no forno"**.

### 5.3 Forno **[Decisão, H7]**

- Forno esteira: a pizza assa em cerca de 2 minutos e o forno comporta de 4 a 6 por vez; há variações de forno.
- Tempo de forno e capacidade são **parâmetros da loja**, e a situação "no forno" aceita várias pizzas ao mesmo tempo.

### 5.4 Pedido urgente e agendado **[Decisão, H6]**

- O balcão pode inserir um pedido como **urgente**: vai ao topo da lista, e o sistema refaz a lista toda, **menos os itens já em produção**. Só gerente e atendente marcam urgente.
- Pedido **agendado** para horário futuro entra na fila só perto da hora.

### 5.5 Acabamento **[Decisão]**

- Enxerga **duas listas:** todos os pedidos em aberto (só consulta) e os pedidos ligados às pizzas que estão no forno.
- Marca cada pizza como **acabada** ao fim de acabar: depois do forno, do acabamento e de empacotar.
- A **etiqueta** é impressa uma por pizza, com nome do cliente, Id do pedido e nome do sabor.
- O **pedido** é marcado como acabado **obrigatoriamente à mão**, nunca sozinho. Refrigerante e acompanhamento **não** entram no checklist do acabamento.
- Pedido acabado vai para a lista de **despacho** ou de **retirada**.
- Quem marca o pedido como **entregue ou retirado** é o **balcão**, e ali se grava a hora de entrega real.

### 5.6 Refação e cancelamento **[Decisão, H10]**

- Refação (pizza errada ou reclamação) é uma **nova pizza ligada à original**, com motivo; a perda do que já foi feito é registrada.
- O mesmo vale para cancelamento com o pedido já em produção.

---

## 6. Dados

### 6.1 Pedido **[Decisão]**

| Campo | Observação |
|---|---|
| Id | Único e sequencial; leva o **identificador da loja** junto (H3) |
| Id do dia | Sequencial dentro do dia, igual ao número do pedido de Vendas |
| Id no aplicativo de venda | Código do pedido no Anota Aí, iFood futuro ou outro |
| Aplicativo de venda | Balcão, Anota Aí ou outro canal |
| Cliente | Nome, WhatsApp e outros |
| Data e hora do pedido | |
| Entrega calculada | Pelo sistema: **pizzas na frente** divididas pelos pizzaiolos ativos, mais forno, acabamento e deslocamento; o tempo médio vem do histórico da loja (H4) |
| Entrega sugerida | Valor oferecido ao cliente, editável pelo atendente **[Suposição]** |
| Entrega real | Gravada pelo balcão |
| Tempo total de preparo | |
| Retirada ou entrega | |
| Observações gerais | |

### 6.2 Itens do pedido **[Decisão]**

| Campo | Observação |
|---|---|
| Sequência | Número do item no pedido |
| Produto | Pizza Grande, pizza Broto, calzone, bebida, acompanhamento e outros, todos do cardápio |
| Sabor 1 | Pizza Grande, Broto ou calzone |
| Sabor 2 | Só pizza Grande |
| Adicionais | Lista de extras, **inclusive a borda**; cada um tem preço somado ao item (H1) |
| Observações do item | |

### 6.3 Dados que o fluxo gera **[Suposição de nomes e campos]**

| Registro | O que guarda |
|---|---|
| Pizza a produzir | Item de origem, sabores, tamanho, adicionais, situação, hora e responsável de cada etapa, pizza original em caso de refação |
| Lista de montagem | Ordem das pizzas aguardando e o que cada pizzaiolo monta |
| Lote de massa (fase 1) | Tamanho, quantidade, responsável, hora |
| Estoque de massa aberta | Quantidade por tamanho e tipo (normal ou com borda) |
| Necessidade de massa (fase 2) | Calculada dos pedidos fora de produção, menos o estoque; é consulta |
| Perda | Massa ou pizza, quantidade, motivo, quem registrou |
| Retrocesso | Pizza, motivo, quem, hora |
| Evento de etapa | Mudança de etapa com usuário e hora, só inserção (auditoria) |
| Etiqueta | O que foi impresso, quando e por quem |

**Quem é dono de quê.** Pedido e itens são de Vendas. Entrega calculada, entrega real, tempo de preparo e todas as etapas são de Produção, ligadas ao pedido pelo Id.

---

## 7. Situações propostas **[Suposição]**

| Objeto | Situações |
|---|---|
| Pizza | na lista, em montagem, no forno, acabada, perdida |
| Pedido | recebido, em produção, acabado, despachado ou retirado, cancelado |

---

## 8. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Vendas | Pedido e itens; pedido urgente | Vendas para Produção |
| Vendas | Situação do pedido e entrega real | Produção para Vendas |
| Estoques | Consumo de insumos e de massa; perdas; falta de insumo ao retroceder | Produção para Estoques |
| Custos | Perdas de massa e de pizza, para o CMV real | Produção para Custos |
| BI | Tempos por etapa, atrasos, refações, motivos de retrocesso | Produção para BI |
| Impressora | Etiqueta por pizza | Produção para a impressora |

Cada ligação tem forma manual para o módulo funcionar sozinho **[Prática]**.

---

## 9. Efeitos em Vendas e no Plano (a incorporar)

- Cardápio único inclui **pizzas, calzones e bebidas**, montado aqui e exportado ao Anota Aí **[Decisão]**.
- **Borda é um adicional**; todo extra é adicional com preço somado ao item. Vendas passa a tratar a borda assim **[Decisão]**.
- **iFood** é um canal futuro, via adaptador, no modelo do "Pedidos 10" **[Decisão]**.
- O Id do pedido leva o identificador da loja.

---

## 10. Perguntas

Todas as perguntas de Produção (G1 a G13 e H1 a H12) foram respondidas por Marlon em 18/10/2026. Restam três itens, nenhum bloqueia a aprovação:

1. **Entrega sugerida:** confirmar que é o valor que o atendente oferece ao cliente, calculado a partir da entrega calculada e editável (minha suposição).
2. **Lista de acompanhamentos e preços** do calzone, bebidas e acompanhamentos, junto com D2 (sabores e preços), só no momento da carga do cadastro.
3. **Modelo da impressora e dos fornos:** necessário só no desenho técnico.

---

## 11. O que este documento ainda não cobre

- Desenho de telas dos tablets e fluxo de cliques.
- Tabelas finais e regras de cálculo da necessidade de massa e da estimativa de entrega.
- Ficha técnica da massa (depende de Estoques e Custos).
- Failover entre os dois PCs servidores.
