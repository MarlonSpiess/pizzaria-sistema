# Resposta ao QA cego da fatia 1C

Relatório: `qa_cego_1C.md`. Nenhum achado de gravidade alta. Situação de cada item:

1. **Limite furado por arredondamento (média): corrigido.** A comparação agora é em dinheiro (`desconto * 100 > subtotal * limite`), sem arredondar o percentual. Teste com limite exato, 29,75 passa e 29,76 exige gerente.
2. **Taxa de entrega abaixo do padrão como desconto sem limite (média): corrigido.** Na entrega, taxa menor que a padrão exige gerência ou autorização de gerente, além do motivo.
3. **Entrega grátis impossível (média): corrigido.** A taxa aceita 0,00; a gerência pode dar entrega grátis com motivo, o atendente precisa de autorização.
4. **Envio duplicado (média): corrigido.** A tela gera uma chave por pedido e trava o botão; a API devolve o pedido já criado quando recebe a mesma chave (índice único, inclusive em envios simultâneos).
5. **Trava de autorização compartilhada com o login do gerente (média): corrigido.** A contagem de falhas é por quem pede e quem autoriza; o login do gerente não é bloqueado pelo erro de um atendente.
6. **Trigger do pedido incompleto (baixa): corrigido.** Agora congela também motivo da taxa, observações, canal, chave e quem criou, impede mudar pedido final (cancelado, despachado ou retirado) e só deixa a situação andar um passo, ou ir para cancelado.
7. **Banco não garante soma dos pagamentos (baixa): aceito.** A regra fica na API e as linhas são só de inserção. `pagamento.valor` guarda o valor entregue e `troco` o troco, documentado. Estorno de cancelamento entra na fatia de Caixa (1E).
8. **Verificação morta de "urgente" (baixa): corrigido.** Removida; atendente e gerência marcam urgente, como decidido.
9. **Rascunho visível após sair (baixa): corrigido.** `sair()` limpa o rascunho.
10. **Mensagem de autorização como oráculo (baixa): corrigido.** Credencial inválida e desconto acima do limite de quem autoriza dão a mesma resposta e contam como falha.

Lacunas de teste apontadas: cobertas as de limite exato, taxa abaixo do padrão, envio duplicado, trava de autorização e triggers. Seguem sem teste automático a tela (testada à mão com navegador) e o cancelamento concorrente.
