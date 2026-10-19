# Detalhamento 06: Custos

Versão 0.1, 19/10/2026. Rascunho para discussão, montado com o que Marlon já decidiu, com o plano macro (seção 4.5) e com boas práticas marcadas. Depende de todos os módulos já aprovados: [Núcleo e Vendas](01_Nucleo_e_Vendas.md), [Produção](02_Producao.md), [Fechamento de Caixa](03_Fechamento_de_Caixa.md), [Estoques e Compras](04_Estoques_e_Compras.md) e [Contas e Fluxo de Caixa](05_Contas_e_Fluxo_de_Caixa.md).

**Critério de sucesso:** Marlon responde as perguntas da seção 6, corrige o desenho e diz "é assim". Só então o módulo vira v0.2 para aprovação.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Objetivo: saber quanto custa cada pizza e quanto custa manter a pizzaria aberta, para precificar e medir margem **[Plano Macro]**.
- A **ficha técnica** existe em planilha: por 1/2 Grande ou Broto, nome do sabor e lista de ingrediente com quantidade; a carga vem de Estoques e Compras **[Decisão J6]**.
- O custo do insumo é o **custo médio móvel**, com os últimos 3 preços visíveis **[Decisão J14]**.
- O **consumo interno** (refeição de funcionário) chega a Custos com valor; não vai para o RH **[Decisão J12]**.
- **Perdas** de massa e de pizza pronta chegam com motivo, vindas de Produção **[Decisão H9]**.
- Despesas fixas reais vêm de Contas a Pagar, por tipo de despesa, e a retirada do proprietário fica separada da despesa **[Decisão K2 e K14]**.
- Taxas de cartão e de canal vêm por maquininha e por canal, nos parâmetros de Contas **[Decisão I7 e K4]**.
- Preço varia por categoria (Tradicionais e Especiais) e por tamanho; a Grande com dois sabores soma metade do preço de cada sabor **[Decisão B2 e C2]**.
- Preço de funcionário com desconto e limite de quantidade **[Decisão J12]**.
- Regime tributário é parâmetro da loja **[Decisão P4]**.

---

## 2. Objetivo

Calcular o custo de cada produto, comparar o CMV teórico com o real, apurar custos fixos e variáveis, e mostrar margem por produto e por canal, para Marlon precificar com segurança.

---

## 3. Submódulos propostos **[Prática, a confirmar]**

| Submódulo | O que faz |
|---|---|
| Custo do produto | Soma dos insumos da ficha técnica, com fator de correção (perda no preparo) e rendimento; recalcula quando o custo médio do insumo muda |
| CMV teórico x real | Teórico: fichas técnicas das vendas. Real: estoque inicial + compras - estoque final. A diferença mede desperdício, porcionamento fora do padrão e desvios |
| Custos fixos | Aluguel, pessoal fixo, depreciação, sistemas, tributos fixos |
| Custos variáveis | Insumos, embalagem, taxa de cartão, comissão do canal, entrega, perdas |
| Margem e precificação | Margem de contribuição por produto e por canal; sugestão de preço para Vendas |
| Ponto de equilíbrio | Faturamento necessário para cobrir os custos fixos |

**Referência.** O Sebrae, citado pela Saipos, aponta CMV ideal por volta de 30% a 40% do faturamento; a Saipos cita 25% a 35% para delivery (Plano Macro, fonte 4). São referências de mercado, não metas: a meta sai do histórico da loja.

---

## 4. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Estoques e Compras | Custo médio dos insumos, estoque inicial e final, perdas, consumo interno | Estoques para Custos |
| Núcleo | Ficha técnica (insumos e quantidades por sabor e tamanho) | Núcleo para Custos |
| Vendas | Mix vendido, preços, descontos, canal, preço de funcionário | Vendas para Custos |
| Produção | Perdas de massa e de pizza com motivo; retrocessos por falta de insumo | Produção para Custos |
| Contas a Pagar | Despesas fixas reais por tipo; taxas de cartão e de canal | Contas para Custos |
| RH | Custo de pessoal gerencial | RH para Custos |
| Imobilizado | Depreciação | Imobilizado para Custos |
| BI | CMV e margens | Custos para BI |
| Vendas | Sugestão de preço | Custos para Vendas |

Cada ligação tem forma manual, para o módulo funcionar sozinho **[Prática]**.

---

## 5. O que os módulos aprovados deixaram para cá

1. **Grande com dois sabores:** o custo é a soma de meia receita de cada sabor, em linha com o preço por metade.
2. **Borda e adicionais:** são extras com preço; cada um precisa de ficha técnica própria para ter custo e margem.
3. **Calzone e bebidas:** calzone precisa de ficha técnica; bebida é item de revenda, com custo da última compra.
4. **Taxas por maquininha e por canal** definem a margem diferente entre balcão e delivery.
5. **Embalagem e material de entrega** são custo variável e vêm do cadastro de itens.

---

## 6. Perguntas

| # | Pergunta | Minha recomendação |
|---|---|---|
| L1 | A planilha de ficha técnica traz o fator de correção e o rendimento (por exemplo, queijo fatiado, massa que encolhe)? | Cadastrar fator por insumo; usar 1,0 quando você não souber |
| L2 | A embalagem (caixa, saco, guardanapo) entra no custo de cada pizza? | Sim, como insumo da ficha de cada tamanho |
| L3 | Quais custos você considera fixos hoje (aluguel, pessoal, energia, outros) e quais variáveis? | Usar o cadastro de tipos de despesa e marcar cada tipo como fixo ou variável |
| L4 | Pessoal da produção e do atendimento é custo fixo, variável ou rateado por pizza? | Fixo, com o rateio por pizza só como indicador |
| L5 | A energia e o gás do forno entram no custo da pizza ou ficam como custo fixo? | Fixo, a menos que você queira estimar por pizza |
| L6 | O custo da entrega (diária e valor por entrega) é custo do pedido de entrega? | Sim, variável, apenas nos pedidos de entrega |
| L7 | Qual a meta de CMV e de margem da loja? Tem alguma referência hoje? | Começar sem meta e propor depois, a partir do histórico |
| L8 | Quer precificar por margem desejada (o sistema sugere o preço) ou só ver a margem do preço atual? | Os dois; a decisão do preço é sempre sua |
| L9 | O CMV real é calculado por mês, por semana ou por dia? | Mensal, com fechamento do estoque no inventário completo |
| L10 | O preço de funcionário entra na margem como desconto ou fica fora da análise? | Entra como desconto, com visão separada |
| L11 | Promoção e desconto concedido entram como redução de receita ou como custo? | Redução de receita, com motivo, como já definido em Vendas |
| L12 | A depreciação do forno e dos equipamentos entra no custo fixo? | Sim, vinda do Imobilizado |

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Fórmulas finais de custo médio, fator de correção e rateio.
- Tributos sobre a venda: dependem do regime e ficam com o contador.
- Carga da ficha técnica: depende da planilha que Marlon vai enviar.
