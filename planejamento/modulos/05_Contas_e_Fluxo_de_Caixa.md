# Detalhamento 05: Contas a Pagar/Receber e Fluxo de Caixa

Versão 0.2, 19/10/2026. Consolidada com as respostas K1 a K14 de Marlon. Aguarda aprovação. Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), [Produção](02_Producao.md), [Fechamento de Caixa](03_Fechamento_de_Caixa.md) e [Estoques e Compras](04_Estoques_e_Compras.md), todos aprovados.

**Critério de sucesso:** Marlon lê o desenho e as respostas da seção 6 e diz "aprovado" ou aponta o que corrigir.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Objetivo: saber o que a pizzaria deve, o que tem a receber e quanto dinheiro terá em cada dia **[Plano Macro]**.
- Contas a Pagar recebe os **títulos das compras** de Estoques e Compras, com prazo e forma de pagamento por fornecedor **[Decisão J10]**.
- Pequenas despesas pagas do caixa são sangria com motivo e comprovante e **seguem para Contas a Pagar** **[Decisão I9]**.
- Contas a Receber recebe os **valores realizados por forma de pagamento** do Fechamento de Caixa; cartão e Pix são conferidos por extrato, e taxas e prazos de recebimento ficam nos parâmetros por forma de pagamento e por maquininha, sem limite de maquininhas **[Decisão I7]**.
- O entregador é terceiro e recebe valor por entrega mais diária por dia; o total apurado em Vendas vira conta a pagar **[Decisão F1 e F2, Suposição de ligação]**.
- Regime tributário é parâmetro da loja; RH é gerencial, e a folha legal fica com o contador **[Decisão P4 e P5]**.
- Uma loja, um banco, identificador da loja em todo registro; dinheiro em NUMERIC; auditoria só de inserção **[Decisão P2 e Kit]**.

---

## 2. Objetivo

Registrar tudo o que a pizzaria vai pagar e vai receber, com data e valor, dar baixa quando o dinheiro se move, e mostrar o saldo do dia e a projeção dos próximos dias.

---

## 3. Submódulos propostos **[Prática, a confirmar]**

| Submódulo | O que faz |
|---|---|
| Contas a pagar | Títulos, parcelas, vencimento e baixa; recorrentes (aluguel, energia, internet); agendamento |
| Contas a receber | Recebíveis de cartão (com prazo e taxa da maquininha), Pix, repasse do Anota Aí e de outros canais |
| Contas e caixas | Contas bancárias e o caixa físico, cada uma com saldo calculado dos movimentos |
| Conciliação de cartões | Venda x repasse x taxa, para revelar a taxa escondida |
| Conciliação bancária | Extrato (OFX ou digitado) contra os movimentos do sistema |
| Fluxo de caixa | Realizado por dia e projetado a partir dos títulos abertos |

---

## 4. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Estoques e Compras | Títulos a pagar das compras | Estoques para Contas |
| Fechamento de Caixa | Valores realizados por forma de pagamento; sangrias e suprimentos | Fechamento para Contas |
| Vendas | Total a pagar do entregador | Vendas para Contas |
| RH | Valores gerenciais da folha e encargos | RH para Contas |
| Imobilizado | Parcelas e manutenções | Imobilizado para Contas |
| Custos | Despesas fixas reais e taxas de cartão e de canal | Contas para Custos |
| BI | Realizado por categoria, em regime de caixa | Contas para BI |

Cada ligação tem forma manual, para o módulo funcionar sozinho **[Prática]**.

**Ponto de atenção.** Taxas de cartão e do canal de delivery são custo variável relevante e costumam ficar escondidas na diferença entre venda e repasse. A conciliação é o que as revela (Plano Macro).

---

## 5. O que os módulos aprovados deixaram para cá

1. Taxa e prazo por maquininha e por forma de pagamento (I7).
2. Despesas pagas em dinheiro do caixa (I9) e compra urgente ligada à sangria (J11): cada uma gera ou baixa um título, sem duplicar o lançamento.
3. Repasse do Anota Aí: depende de acesso que Marlon só pedirá depois do sistema funcionar; começar com lançamento manual.
4. Pagamento do entregador: a apuração é de Vendas, o pagamento é daqui.

---

## 6. Perguntas

### 6.1 Respondidas por Marlon em 19/10/2026

- **K1:** haverá um **cadastro de contas bancárias**, por loja, porque **cada loja é uma empresa à parte** e pode ter várias contas **[Decisão]**. Isso reforça o identificador da loja em todo registro e a visão futura de várias lojas.
- **K2:** despesas fixas são **cadastradas como recorrentes**, com um **cadastro de tipos de despesa** **[Decisão]**.
- **K4 e K5:** repasse **por canal**, com prazo e taxa nos parâmetros (minha sugestão, aceita) **[Decisão]**.
- **K6:** **não há fiado, convênio nem venda a prazo por padrão** **[Decisão]**.
- **K7:** o entregador é **conta a pagar, com baixa no acerto do dia** **[Decisão]**.

### 6.2 Respondidas em 19/10/2026 (todas as recomendações aceitas)

- **K3:** a forma de pagamento é registrada em cada baixa **[Decisão]**.
- **K8:** lança o gerente ou o subgerente; aprova o administrador acima de um valor nos parâmetros **[Decisão]**.
- **K9:** conciliação bancária digitada no começo; importação de OFX depois **[Decisão]**.
- **K10:** fluxo de caixa projetado para 30 dias, com 7 em destaque **[Decisão]**.
- **K11:** empréstimos e financiamentos são títulos parcelados, ligados ao Imobilizado quando forem bem **[Decisão]**.
- **K12:** tributos, contador e alvarás viram contas recorrentes cadastradas à mão no começo; o regime tributário fica como parâmetro **[Decisão]**.
- **K13:** pro-labore, folha e encargos entram como valor gerencial vindo do RH; a folha legal continua com o contador **[Decisão]**.
- **K14:** retirada do proprietário é separada de despesa, para não distorcer o resultado **[Decisão]**.

Todas as perguntas do módulo estão respondidas.

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de baixa parcial, juros e multa.
- Importação de OFX e conciliação automática (pesquisar quando chegar a hora).
- Cálculo de tributos, que fica com o contador.
