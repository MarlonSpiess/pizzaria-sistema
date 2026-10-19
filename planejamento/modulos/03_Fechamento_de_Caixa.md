# Detalhamento 03: Fechamento de Caixa

Versão 0.1, 19/10/2026. Rascunho para discussão, montado só com o que Marlon já decidiu e com boas práticas marcadas. Parte do [Plano Macro](../00_Plano_Macro.md). Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md) e de [Produção](02_Producao.md), ambos aprovados.

**Critério de sucesso:** Marlon responde as perguntas da seção 5, corrige o desenho e diz "é assim". Só então o módulo vira v0.2 para aprovação.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Formas de pagamento: dinheiro (com troco), Pix, crédito e débito; a venda pode ser dividida em mais de uma forma **[Decisão B5 e D4]**.
- Desconto e acréscimo no fechamento da venda, com motivo obrigatório e auditoria; cancelamento exige motivo, e o atendente respeita o limite em % do perfil **[Decisão B6 e F3]**.
- Entregador é terceiro e recebe **valor por entrega** mais **diária por dia**, com padrões nos parâmetros e alteração no fechamento das entregas **[Decisão F1 e F2]**. A apuração do que cada entregador recebe é de Vendas; o **acerto do dinheiro** do entregador ao fim do turno é deste módulo **[Prática]**.
- Hoje o cupom fiscal (CF) é digitado em software de terceiro; o fechamento lista os pedidos pagos sem "CF emitido" informado **[Suposição aprovada com Vendas]**.
- Uma loja, com 1 a 5 pessoas na recepção e 2 PCs **[Decisão]**.
- Login pessoal e intransferível; toda ação do caixa fica na auditoria **[Decisão B9]**.

---

## 2. Objetivo

Garantir, a cada turno ou dia, que o dinheiro e os comprovantes conferem com as vendas, apontar diferenças com responsável e motivo, e entregar os valores realizados a Contas a Receber, Fluxo de Caixa e BI.

---

## 3. Desenho proposto **[Prática]**

| Etapa | O que acontece |
|---|---|
| Abertura | Quem abre informa o fundo de troco; fica registrado quem, quando e quanto |
| Durante o turno | Cada pagamento recebido em Vendas vira valor esperado por forma de pagamento; sangrias (retiradas) e suprimentos (entradas) são lançados com motivo |
| Fechamento | **Contagem cega:** o operador informa o que contou sem ver o esperado; só depois o sistema mostra a diferença |
| Conferência | Pix, crédito e débito conferidos com o extrato e as maquininhas; pedidos sem CF informado listados |
| Diferença | Sobra ou falta exige justificativa e responsável; fica na auditoria |
| Acerto do entregador | Dinheiro recebido do cliente na entrega, troco levado e total devido ao entregador |
| Relatório do turno | Totais por forma de pagamento, sangrias, diferenças, cancelamentos e descontos |
| Envio | Valores realizados vão a Contas a Receber e Fluxo de Caixa; quebras de caixa vão ao BI |

---

## 4. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Vendas | Valor esperado por forma de pagamento; descontos, acréscimos e cancelamentos; pedidos sem CF | Vendas para Fechamento |
| Vendas | Valores do fechamento das entregas | Vendas para Fechamento |
| Contas a Receber e Fluxo de Caixa | Valores realizados por forma de pagamento | Fechamento para Contas |
| BI | Quebras de caixa, descontos, cancelamentos | Fechamento para BI |

Cada ligação tem forma manual, para o módulo funcionar sozinho **[Prática]**.

---

## 5. Perguntas

### 5.1 Respondidas por Marlon em 19/10/2026

- **I1:** o caixa fecha **por dia**, um fechamento diário **[Decisão]**.
- **I2:** **uma só** gaveta de dinheiro para a loja; um caixa aberto por vez, com o operador registrado **[Decisão]**.
- **I5:** **contagem cega sim**, com o atendente contando e o gerente aprovando diferenças **[Decisão]**.
- **I8:** o entregador é **registrado por pedido** (o que recebeu e o troco levado) e **acerta no fim do turno** **[Decisão]**.

### 5.2 Em aberto

| # | Pergunta | Minha recomendação |
|---|---|---|
| I1 | O caixa fecha uma vez por dia ou por turno? Quais os turnos e o horário de funcionamento? | Por turno, se houver troca de pessoa |
| I2 | Quantas gavetas de dinheiro existem: uma por PC da recepção ou uma só para a loja? | Uma gaveta, um caixa aberto por vez, com o operador registrado |
| I3 | O fundo de troco é um valor fixo por dia? Quem abre o caixa? | Valor padrão nos parâmetros, alterável na abertura; abre gerente ou atendente do turno |
| I4 | Há sangria (retirada de dinheiro) e suprimento? Quem autoriza e com qual motivo? | Sim, com motivo em tabela e autorização do gerente acima de um valor nos parâmetros |
| I5 | Concorda com a contagem cega no fechamento? Quem fecha: o atendente ou só o gerente? | Sim, contagem cega; o atendente conta e o gerente aprova diferenças |
| I6 | Existe tolerância de diferença (por exemplo até R$ 2)? O que se faz com sobra e falta, e quem responde por ela? | Tolerância nos parâmetros; acima dela, justificativa obrigatória |
| I7 | Quantas maquininhas há e como confere o cartão e o Pix: extrato da adquirente, da conta ou ambos? Quais taxas e prazos de recebimento valem para Contas a Receber? | Conferir por extrato; taxas e prazos nos parâmetros por forma de pagamento |
| I8 | Pedido do Anota Aí pago no app (online) e pedido pago na entrega: como o entregador recebe e presta contas do dinheiro e da maquininha? | Registrar por pedido o que o entregador recebeu e o troco levado, e acertar no fim do turno |
| I9 | Pode pagar pequenas despesas com o dinheiro do caixa (gás, diarista, entregador)? | Sim, como sangria com motivo e comprovante, e o lançamento segue para Contas a Pagar |
| I10 | Pedido cancelado depois de pago: o dinheiro é devolvido como? | Estorno registrado com motivo e autorização, ligado ao pedido |
| I11 | O pedido sem CF informado impede o fechamento ou só avisa? | Só avisa, com a lista na tela, enquanto o CF for digitado em software de terceiro |
| I12 | Quem recebe o relatório do turno e em que formato (tela, impressão, WhatsApp)? | Tela e impressão; o envio por WhatsApp fica para depois |

---

## 6. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de arredondamento (dinheiro em NUMERIC, como em todo o sistema) **[Prática]**.
- Conciliação bancária automática, que pertence a Contas e Fluxo de Caixa.
- Emissão fiscal pelo nosso sistema, projeto futuro.
