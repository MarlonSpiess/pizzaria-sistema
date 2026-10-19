# Detalhamento 05: Contas a Pagar/Receber e Fluxo de Caixa

Versão 0.1, 19/10/2026. Rascunho para discussão, montado com o que Marlon já decidiu, com o plano macro (seção 4.4) e com boas práticas marcadas. Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), [Produção](02_Producao.md), [Fechamento de Caixa](03_Fechamento_de_Caixa.md) e [Estoques e Compras](04_Estoques_e_Compras.md), todos aprovados.

**Critério de sucesso:** Marlon responde as perguntas da seção 6, corrige o desenho e diz "é assim". Só então o módulo vira v0.2 para aprovação.

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

### 6.2 Em aberto


| # | Pergunta | Minha recomendação |
|---|---|---|
| K1 | Quais contas bancárias a loja usa? Há conta separada do proprietário? | Cadastrar as contas da loja; conta pessoal fora do sistema |
| K2 | Quais as despesas fixas recorrentes (aluguel, energia, água, internet, contador, sistema, outras) e dia de vencimento? | Cadastrar como recorrentes, gerando o título todo mês |
| K3 | Como a loja paga: dinheiro do caixa, transferência, Pix, boleto, cartão? Há pagamento por débito automático? | Registrar a forma em cada baixa |
| K4 | As vendas do Anota Aí chegam por repasse ou o cliente paga direto à loja? Com que prazo e taxa? | Cadastrar o repasse por canal, com prazo e taxa nos parâmetros |
| K5 | Quando o cliente paga online pelo Anota Aí (Pix ou cartão), esse dinheiro entra em qual conta e em quanto tempo? | Mesmo cadastro de K4, por canal |
| K6 | Existe fiado, convênio ou venda a prazo para clientes? | Não existe por padrão; só se você disser |
| K7 | Como é o pagamento do entregador: no mesmo dia, semanal ou mensal? Sai do caixa do dia? | Tratar como conta a pagar, com baixa no acerto do dia ou na data combinada |
| K8 | Quem lança e quem aprova pagamentos? Há limite por perfil? | Lança o gerente ou subgerente; aprova o administrador acima de um valor nos parâmetros |
| K9 | Conciliação bancária: importar OFX do banco ou digitar? Qual banco? | Digitar no começo, OFX depois, como a nota fiscal |
| K10 | Quer ver o fluxo de caixa projetado por quantos dias (7, 30, 90)? | 30 dias, com 7 em destaque |
| K11 | Há empréstimos, financiamentos ou parcelas de equipamentos hoje? | Cadastrar como títulos parcelados, ligados ao Imobilizado quando for bem |
| K12 | Tributos e taxas (Simples ou outro regime, contador, alvarás) viram contas a pagar recorrentes? | Sim, cadastrados à mão no começo; o regime fica como parâmetro |
| K13 | Pro-labore, folha e encargos: entram em Contas a Pagar como valor gerencial vindo do RH? | Sim; a folha legal continua com o contador |
| K14 | Há conta de adiantamento, sócios ou retiradas do proprietário que precisem ser separadas das despesas? | Separar retirada do proprietário de despesa, para não distorcer o resultado |

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de baixa parcial, juros e multa.
- Importação de OFX e conciliação automática (pesquisar quando chegar a hora).
- Cálculo de tributos, que fica com o contador.
