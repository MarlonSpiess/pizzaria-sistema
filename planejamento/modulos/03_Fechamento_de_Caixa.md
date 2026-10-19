# Detalhamento 03: Fechamento de Caixa

Versão 0.2, 19/10/2026. Consolidada com as respostas I1 a I12 de Marlon. **APROVADA por Marlon em 19/10/2026.** Parte do [Plano Macro](../00_Plano_Macro.md). Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md) e de [Produção](02_Producao.md), ambos aprovados.

**Critério de sucesso:** Marlon lê o desenho e as respostas da seção 5 e diz "aprovado" ou aponta o que corrigir.

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
| Abertura | Uma gaveta, um fechamento por dia. Quem abre (gerente ou atendente) informa o fundo de troco; fica registrado quem, quando e quanto |
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

### 5.2 Respondidas em 19/10/2026 (todas as recomendações aceitas)

- **I3:** fundo de troco com valor padrão nos parâmetros, alterável na abertura; abre gerente ou atendente do turno **[Decisão]**.
- **I4:** sangria e suprimento com motivo em tabela; acima de um valor definido nos parâmetros, autorização do gerente **[Decisão]**.
- **I6:** tolerância de diferença nos parâmetros; acima dela, justificativa obrigatória **[Decisão]**.
- **I7:** o número de maquininhas é **variável, podendo passar de 2, sem limite**; se o sistema precisar de um teto técnico, usa-se 999 **[Decisão]**. Cartão e Pix são conferidos por extrato; taxas e prazos de recebimento ficam nos parâmetros, por forma de pagamento e por maquininha **[Decisão da recomendação]**.
- **I9:** pequenas despesas pagas do caixa são sangria com motivo e comprovante, e seguem para Contas a Pagar **[Decisão]**.
- **I10:** pedido cancelado depois de pago gera estorno com motivo e autorização, ligado ao pedido **[Decisão]**.
- **I11:** pedido sem CF informado só avisa, não impede o fechamento **[Decisão]**.
- **I12:** relatório do turno em tela e impressão; envio por WhatsApp fica para depois **[Decisão]**.

Todas as perguntas do módulo estão respondidas.

---

## 6. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de arredondamento (dinheiro em NUMERIC, como em todo o sistema) **[Prática]**.
- Conciliação bancária automática, que pertence a Contas e Fluxo de Caixa.
- Emissão fiscal pelo nosso sistema, projeto futuro.
