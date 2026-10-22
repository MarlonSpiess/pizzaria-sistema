# Resposta ao QA cego da fatia 1D

Relatório: `qa_cego_1D.md`. Situação dos 17 achados:

**Alta**
1. **Deadlock entre pegar pizza e cancelar pedido: corrigido.** Toda ação de pizza trava primeiro o pedido e depois a pizza, na mesma ordem do cancelamento; a escolha da próxima pizza usa `SKIP LOCKED` em pizza e pedido. Teste de corrida com threads.
2. **Etiqueta nunca aparecia: corrigido.** A etiqueta fica guardada e é redesenhada a cada atualização até o operador fechar.
3. **Refação e perda com pedido acabado ou despachado: corrigido.** Refação só com pedido recebido ou em produção (reclamação depois vira novo pedido; pergunta para Marlon abaixo); perda é recusada em pedido cancelado ou despachado; o pedido trava as pizzas antes de contar.

**Média**
4. **Gerência marcava acabado sem checar pizzas: corrigido.** A regra está no passo de situação, vale para qualquer caminho.
5. **Perda por qualquer perfil: corrigido.** Perda de massa virou permissão própria (`producao.perda_massa`, só massa e gerência); o perfil massa não perde pizza; pizza em montagem só o dono, o acabamento ou a gerência perdem.
6. **Posição errada do retroceder com urgente: corrigido.** A posição é calculada só entre as pizzas do mesmo grupo de urgência.
7. **Ordem duplicada e sem desempate: corrigido.** Retroceder usa a mesma trava da criação e todo `ORDER BY` desempata por id.
8. **Refação concorrente com cancelamento: corrigido** pela trava do pedido e pela checagem de situação.
9. **Contagem de pizzas com refação: corrigido.** A refação conta no lugar da original perdida; o botão de acabar o pedido aparece.
10. **Perda em montagem não baixava a massa: corrigido.** Pizza perdida antes do forno conta como massa usada.

**Baixa**
11. **Precisão da ordem: corrigido.** Quando o espaço entre duas ordens fica menor que 0,001, a fila é renumerada.
12. **`iniciar-padrao` concorrente: corrigido** com trava.
13. **Rotas sem tratamento de erro do banco:** aceito nas rotas que só gravam com validação prévia; as que gravam com dado novo já traduzem o erro.
14. **TRUNCATE nas tabelas novas: corrigido** (também nas de vendas).
15. **Tela:** ações que não voltam (perder, refazer) pedem confirmação; atualizações não se sobrepõem; o relógio vale para qualquer subtela.
16. **Índice único de refação por original: criado.** Índice único de ordem: não criado, a trava já impede a repetição.
17. **Lacunas de teste:** cobertas concorrência, urgente com retrocesso, refação com pedido acabado, perda pelo perfil massa e renumeração.

**Pergunta para Marlon (recomendação: sim).** Reclamação depois de o pedido acabado ou entregue vira um novo pedido sem custo, e não uma refação do pedido antigo?
