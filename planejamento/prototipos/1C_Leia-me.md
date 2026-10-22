# Protótipo 1C: Vendas (balcão)

Arquivo: `1C_Vendas.html`. Abra no navegador. Dados de exemplo, nada é gravado. O seletor "Perfil simulado" no topo troca entre atendente e gerente.

## O que testar
1. Novo pedido de retirada: Grande com 2 sabores (cada metade vale metade do preço do sabor), Broto, borda, adicional, calzone, bebida.
2. Entrega: exige cliente; a taxa padrão entra no total.
3. Desconto acima do limite do atendente: o sistema pede o gerente. Troque o perfil para gerente e confirme.
4. Pagamento dividido: soma exata do total; troco só sai do dinheiro.
5. Pedidos do dia: Id reinicia por dia, situações recebido, em produção, acabado, despachado ou retirado; cancelar exige motivo, e pedido já em produção só o gerente cancela.
6. Parâmetros de venda: limites, taxa, formas de pagamento (tudo parametrizável, com histórico).

## Regras para você confirmar (recomendação entre parênteses)
- V1: o pedido nasce ao confirmar e já segue para a Produção? (sim)
- V2: cliente é opcional na retirada e obrigatório na entrega? (sim)
- V3: autorização do gerente por senha dele na própria tela do atendente? (sim, registrada com quem autorizou)
- V4: acréscimo também exige motivo e tem limite? (motivo sim, limite não)
- V5: cancelar pedido em produção só gerente ou subgerente, e a pizza já feita vira perda na Produção? (sim)
- V6: troco só em dinheiro e nunca maior que o dinheiro recebido? (sim)
- V7: taxa de entrega editável no pedido com motivo? (sim, padrão vem dos parâmetros)
- V8: pedido de funcionário com preço especial entra depois, na fatia de Estoques? (sim)
