# Resposta ao QA cego das fatias 4 (Custos) e 5 (Imobilizado)

## Corrigido
- 1 data ou taxa extrema: taxa de categoria entre 1% e 100%, vida limitada a 1200 meses, datas do bem entre 2000 e 2100; a geração de depreciação só calcula até o mês corrente e não estoura o ano 10000.
- 2 aprovação da ordem presa ao valor: a aprovação guarda o valor aprovado; custo maior no fechamento derruba a aprovação e exige outra. Aprovação antecipada sem custo não vale para custo maior.
- 3 NaN em fator de correção, taxa, quantidade de peça, leitura e limite: recusado com 422.
- 4 ordem de terceiro com mão de obra sem tipo de despesa (nem o tipo "Manutenção"): recusa com 400 em vez de gerar título sem natureza.
- 5 baixa com data anterior ao último mês depreciado: recusada.
- 8 abertura de ordem trava o bem (FOR UPDATE) contra a baixa simultânea.
- 10 PATCH com o mesmo valor de campo de depreciação não muda nada (sem 500).
- 12 fechamento de CMV recusa mês vazio e anterior a 2020.

## Pendente (segue a recomendação)
- 6 e 7 CMV real com entrada inicial no mês, devolução e peças de manutenção.
- 9 insumo sem custo mostra margem alta; a tela já marca "insumo sem custo".
- 11 taxa de cartão do resultado usa a regra de hoje.
- 13 fator de correção em dobro com a perda da ficha (decisão de regra, perguntar a Marlon).
- 14 a 21 arredondamento de bem de valor pequeno, ordens duplicadas por plano, depreciação retroativa, natureza "investimento", auto-aprovação parcial, mês 9999, corrida de parâmetros e detalhes de tela.
