# Resposta ao QA cego da fatia 1E (Caixa)

## Corrigido
- A1 virada de dia: o caixa cobre a faixa de datas da abertura até o dia anterior ao próximo caixa; contagem e fechamento valem depois da meia-noite.
- A2 entrega e diária fora do padrão exigem `caixa.gerir`.
- A3 limite de sangria não definido vale 0, acumulado por caixa para sangrias sem autorização.
- A4 contagem cega: esperado, vendas, descontos, acréscimos, acertos, pedidos, totais de pedidos sem CF, cancelamentos e estornos ficam ocultos até contar.
- M1 formas da contagem = aceitas, com movimento e dinheiro.
- M4 aprovador precisa ser gerente, proprietário ou administrador e diferente de quem contou; subgerente nunca aprova.
- M6 motivo copiado no movimento (`motivo_nome`, `vira_despesa`).
- B4 `diferenca` em NUMERIC(14,2).

## Pendente (decisão de Marlon, seguindo a recomendação por ora)
- M2 fundo de troco livre na abertura (recomendado: aviso acima de um valor nos parâmetros).
- M3 gerência cancelar pedido pago sem segunda pessoa (recomendado: exigir segundo gerente).
- M5 sem reabertura de caixa contado (recomendado: reabertura só pelo administrador, com motivo).
- B1 pedido de entrega em dinheiro sem entregador atribuído (recomendado: bloquear a contagem com aviso).
- B2 correção de atribuição de entregador.
- B3 esperado negativo por estorno de pedido de outro dia.
- B5, B6, B7 endurecimentos menores.
