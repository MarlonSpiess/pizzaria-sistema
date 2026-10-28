# Resposta ao QA cego da fatia 3 (Contas a Pagar/Receber e Fluxo de Caixa)

## Corrigido
- A1 fracionar lançamentos: o limite de aprovação soma por dia e por usuário; o aprovador não é quem lançou.
- A2 título duplicado: a sincronização é idempotente e pula a nota que já tem título vinculado à sangria.
- A3 listagem: a tela mostra os títulos em aberto primeiro; filtro de atrasados no servidor.
- M1 baixa com desconto, juros e multa somando mais de 20% do valor só com a permissão de aprovar.
- M2 e M8 conciliação 1 para 1 exige valor igual.
- M3 baixa simultânea: trava por título.
- M6 o fluxo de caixa inclui pendentes e mostra os a receber líquidos da taxa; atrasados contam hoje.
- B1 a B3 datas e parcelas: validação e arredondamento da última parcela.

## Pendente (segue a recomendação; Marlon avalia depois)
- M4 a tela de canais de repasse ainda não alimenta o cálculo de todos os relatórios.
- M5 a regra de recebimento usa a mais recente, não a vigente na data da venda.
- M7 saldo das contas em situações de baixa sem conta.
- B4 a B6 sincronização em GET, gatilho do título e cancelamento por qualquer operador.
