# Protótipo 1D: Produção

Arquivo: `1D_Producao.html`. Abra no navegador. O seletor no topo troca a tela como se fosse o tablet de cada função. Dados de exemplo, nada é gravado.

## O que testar (fluxo completo de uma pizza)
1. Massa: veja a necessidade por tamanho menos a massa aberta; lance um lote; informe a contagem; registre perda com motivo.
2. Pizzaiolo: recebe sempre a próxima pizza; "Produzida" manda ao forno; "Retroceder" exige motivo da lista.
3. Forno: várias pizzas ao mesmo tempo, com aviso se passar da capacidade.
4. Acabamento: duas listas (pizzas do forno e todos os pedidos, só consulta); etiqueta por pizza (cliente, Id, sabor); o pedido só vira acabado à mão.
5. Balcão: despachar ou marcar retirado grava a hora real; marcar pedido urgente.
6. Parâmetros: tempo de forno, pizzas por vez e listas de motivos são tabelas da loja.
7. Rodapé: registro de eventos, só inserção, com usuário e hora.

## Regras para você confirmar (recomendação entre parênteses)
- W1: o pizzaiolo vê só a próxima pizza e o tamanho da fila atrás dela? (sim)
- W2: retroceder devolve a pizza à fila uma posição abaixo? (sim)
- W3: pizza no forno passa a "saiu do forno" por toque no forno ou por tempo parametrizado? (toque no começo; o tempo só alerta)
- W4: o forno só avisa quando passa da capacidade, sem bloquear? (sim)
- W5: pedido urgente vai ao topo sem mexer no que já está em produção? (sim)
- W6: etiqueta impressa ao marcar a pizza acabada? (sim; a impressão real depende de teste com a impressora, risco já registrado)
- W7: perda de pizza pronta também registrada pelo acabamento, com a lista de motivos? (sim)
