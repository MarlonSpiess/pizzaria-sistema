# QA cego da fatia 1D (Produção)

Escopo lido: migrations_pg/005_producao.sql, api/routers/producao.py, api/services/producao.py, trechos de api/routers/vendas.py, schemas, security, parametros, abaProducao em app.js e tests/test_producao.py.
Os 15 testes de tests/test_producao.py passam (62 s). Código de produção e testes não foram alterados. Só entram achados que dá para ver no código ou que foram reproduzidos.

Pontos verificados e sem falha: SQL com dado de usuário (todo valor vai por parâmetro; f-strings só montam nome de tabela vindo do código e colunas vindas do schema); XSS (a função h() usa nó de texto para todo filho, e os campos sabores, adicionais, observações, cliente e nome de motivo só entram por ela); permissão por rota (cada rota usa requer com a permissão certa); trava por pizza contra duas ações simultâneas na mesma pizza; trigger que impede ressuscitar pizza perdida, cancelada ou acabada; mensagens de erro de negócio sem detalhe técnico.

## Resumo

| # | Gravidade | Título |
|---|-----------|--------|
| 1 | alta | Deadlock entre pegar próxima pizza e cancelar pedido (vira erro 500) |
| 2 | alta | Etiqueta nunca aparece na tela depois de "Acabada e etiqueta" |
| 3 | alta | Refação e perda são aceitas com o pedido já acabado ou despachado |
| 4 | média | Gerência marca pedido acabado por /pedidos/{id}/situacao sem checar as pizzas |
| 5 | média | Perda de pizza sem checar dono nem função (pizzaiolo perde pizza de outro; massa perde qualquer pizza) |
| 6 | média | Retroceder calcula posição errada quando há pedido urgente na fila |
| 7 | média | Retroceder sem trava: duas retrocessões simultâneas geram a mesma ordem |
| 8 | média | Refação concorrente com cancelamento deixa pizza "na lista" em pedido cancelado |
| 9 | média | Tela de Acabamento nunca mostra o botão "Marcar pedido acabado" quando houve refação |
| 10 | média | Pizza perdida em montagem não baixa massa aberta |
| 11 | baixa | Ordem esgota a precisão NUMERIC(24,6) depois de cerca de 20 retrocessões no mesmo par |
| 12 | baixa | iniciar-padrao concorrente devolve 500 |
| 13 | baixa | Rotas de escrita sem tratamento de erro do banco (500 e exceção de trigger) |
| 14 | baixa | Tabelas novas sem trigger contra TRUNCATE |
| 15 | baixa | Tela: escolher motivo no select dispara a ação na hora; atualização automática só começa se a tela abrir em montagem, forno ou acabamento; chamadas de desenho podem se sobrepor |
| 16 | baixa | Sem índice único para uma refação por original e para ordem na fila |
| 17 | baixa | Lacunas de teste |

## 1. Deadlock entre pegar próxima pizza e cancelar pedido (alta)

Onde: api/routers/producao.py:97-105 (pegar_proxima) contra api/routers/vendas.py:229-246 e api/services/producao.py:85-86 (cancelar).

Cenário: o pizzaiolo A chama /pizzas/proxima. A transação trava a linha da pizza (FOR UPDATE SKIP LOCKED, linha 97) e só depois trava o pedido (_pedido travar=True, linha 105). Ao mesmo tempo o balcão cancela o mesmo pedido. A transação do cancelamento trava o pedido primeiro (linha 230 de vendas.py) e depois tenta travar as pizzas (FOR UPDATE, services/producao.py:85). A ordem de travas é invertida (pizza, pedido contra pedido, pizza).
Reproduzido com duas conexões no banco de teste, reproduzindo exatamente essa ordem de travas: uma das transações recebe DeadlockDetected (resultado: {'B': 'DeadlockDetected', 'A': 'ok'}). Na API isso sai como erro 500 genérico, e em cancelar o `except psycopg.Error` chama traduzir_erro, que relança a exceção (linha 93 de database.py). Um cancelamento pode falhar justamente no pedido em que a pizza acabou de ser pega.

Correção: padronizar a ordem de travas como pedido e depois pizza. Em pegar_proxima, escolher a pizza sem trava (ou com trava), ler o pedido, travar o pedido primeiro e depois travar e revalidar a pizza. Em refazer (linha 214 e 218) e demais rotas que tocam as duas, seguir a mesma ordem. Opcionalmente, tratar DeadlockDetected e SerializationFailure em traduzir_erro como 409 "Tente novamente".

## 2. Etiqueta nunca aparece na tela (alta)

Onde: frontend/static/app.js, subAcabamento (botão "Acabada e etiqueta") e a função acao.

Cenário: o botão faz `const r = await acao("POST", ".../acabada"); if (r) etiqueta(r.etiqueta)`. Dentro de acao, depois da chamada à API vem `await desenharSub()`, que monta um corpo novo (com um `box` novo) e troca o conteúdo de `alvo`. Quando acao devolve, `etiqueta()` escreve no `box` antigo, que já saiu da página. O backend grava a etiqueta (etiqueta_impressa), a pizza some da lista de "Saíram do forno" e nada é exibido nem pode ser impresso, já que a pizza não está mais na lista.
Mesmo se funcionasse, a atualização automática a cada 8 s (linhas finais de abaProducao) refaria a tela e apagaria a etiqueta antes de imprimir; além disso window.print() imprime a página inteira, não só a etiqueta.

Correção: guardar a etiqueta num estado fora do corpo (por exemplo `let etiquetaAtual`) e fazer subAcabamento desenhá-la dentro do corpo novo; o temporizador não deve apagá-la até o usuário dispensar. Dar uma folha de impressão própria (CSS @media print só para .etiqueta). Considerar reimpressão pela lista de pedidos.

## 3. Refação e perda aceitas com o pedido já acabado ou despachado (alta)

Onde: api/routers/producao.py:218-220 (refazer) e 198-208 (perder). O único bloqueio é pedido cancelado.

Cenário: pedido com uma pizza acabada e pedido marcado acabado (ou despachado ou retirado). O acabamento chama /pizzas/{id}/refazer: a original vira perdida, nasce uma pizza "na lista" e o pedido continua "acabado" ou "despachado ou retirado". Resultado: pedido acabado com pizza pendente, que ainda aparece na fila (a fila só exclui pedido cancelado) e o pizzaiolo a recebe em /proxima, produzindo uma pizza para um pedido que o cliente já levou. perder em pizza acabada de pedido despachado deixa o pedido acabado com pizza perdida sem refação. O mesmo ocorre sem corrida: basta chamar depois do pedido acabado.
Há também corrida: pedido_acabado (linhas 182-193) trava o pedido mas não as pizzas; se rodar ao mesmo tempo que refazer ou perder de uma pizza acabada, a contagem de pendentes (linha 185) ainda vê "acabada" e o pedido vira acabado com a refação criada logo depois. refazer lê o pedido sem trava (linha 218, sem travar=True).

Correção: em refazer e perder, travar o pedido (pedido primeiro, ver achado 1) e exigir pedido em "recebido" ou "em producao". Se a regra de negócio permitir refazer depois de acabado, o pedido precisa voltar a "em producao" por evento próprio e registrado. Em pedido_acabado, travar também as pizzas do pedido (SELECT ... FOR UPDATE) antes de contar.

## 4. Gerência marca pedido acabado sem checar pizzas (média)

Onde: api/routers/vendas.py:207-216 (situacao) e :193-204 (mudar_situacao).

Cenário: gerente ou subgerente chama POST /api/pedidos/{id}/situacao com {"situacao": "acabado"} num pedido "em producao" com pizzas na lista. O guard só verifica vendas.gerir e mudar_situacao só confere a sequência; a verificação "todas as pizzas acabadas ou refeitas" existe apenas em /producao/pedidos/{id}/acabado (producao.py:185-189). A regra "pedido só vira acabado com todas as pizzas acabadas" é contornada, e o pedido acabado ainda tem pizzas na fila.

Correção: mover a checagem de pizzas para mudar_situacao quando nova for "acabado" (ou extrair uma função em services/producao.py usada pelas duas rotas), ou retirar "acabado" de PedidoSituacao e deixar só a rota da Produção.

## 5. Perda de pizza sem checar dono nem função (média)

Onde: api/routers/producao.py:198-208 (perder); api/security.py:39-41.

Cenário A: o pizzaiolo B chama /pizzas/{id}/perder numa pizza em montagem do pizzaiolo A. produzida e retroceder usam _minha (linhas 114-116), perder não, então B tira a pizza de A e registra perda em nome de B.
Cenário B: o perfil massa recebe producao.perda só para perder massa, mas essa mesma permissão libera /pizzas/{id}/perder em qualquer pizza (em montagem, no forno, saiu do forno, acabada). "Cada função só faz o que é da sua permissão" não vale para perda de pizza. O pizzaiolo também pode perder pizza acabada.

Correção: separar permissões (producao.perda_massa e producao.perda_pizza), ou exigir _minha para pizza em montagem e restringir situações por perfil (pizzaiolo: em montagem e no forno que ele mesmo produziu; acabamento: saiu do forno e acabada). Adicionar teste de permissão para o perfil massa em /perder.

## 6. Retroceder calcula posição errada com pedido urgente (média)

Onde: api/routers/producao.py:136-143.

Cenário: a fila ordena por urgente DESC e depois ordem, mas a nova ordem é a média simples das ordens das duas próximas pizzas, sem considerar o grupo. Fila "na lista": U1 (urgente, ordem 50), N1 (20), N2 (30). Pizza X normal (ordem 10) é retrocedida. prox = [U1, N1], nova = (50+20)/2 = 35, e X cai depois de N2: desce duas posições em vez de uma. Caso inverso: X urgente com prox[0] urgente de ordem 5 e prox[1] normal de ordem 3 dá nova = 4, que é menor que 5, e X continua em primeiro (não desceu). A regra "volta uma posição" falha sempre que as duas vizinhas estão em grupos de urgência diferentes.

Correção: calcular a nova ordem só entre vizinhas do mesmo grupo de urgência da pizza; se a segunda vizinha é de outro grupo, usar maior ordem do grupo da pizza (+1) ou, se a primeira já é a última do grupo, manter a ordem. Cobrir com teste de retrocesso com urgente na fila.

## 7. Retroceder sem trava de ordem (média)

Onde: api/routers/producao.py:128-153 (sem pg_advisory_xact_lock(5, loja)) e migrations_pg/005_producao.sql (sem unicidade de ordem).

Cenário: dois pizzaiolos retrocedem ao mesmo tempo. Ambos leem as mesmas duas próximas pizzas (READ COMMITTED), calculam a mesma média e gravam a mesma ordem para pizzas diferentes. Duplicidade de ordem torna a ordem entre as duas indeterminada (ORDER BY sem desempate) e a fila pode trocar de posição entre recarregamentos. gerar_pizzas e refazer travam com a chave (5, loja); retroceder é o único que escreve ordem sem ela.

Correção: pegar a trava (5, loja) em retroceder antes de ler as vizinhas, e acrescentar p.id como desempate no ORDER BY (_ORDEM e consultas de proxima).

## 8. Refação concorrente com cancelamento (média)

Onde: api/routers/producao.py:214-235 contra api/services/producao.py:85-91.

Cenário: refazer tem a pizza travada e lê o pedido sem trava (situação ainda "recebido"/"em producao"). O cancelamento trava o pedido, marca "cancelado" e fica esperando a pizza (por causa do achado 1 pode até dar deadlock). Quando refazer comita, a nova pizza "na lista" foi inserida depois do SELECT do cancelamento, que não a enxerga. Fica uma pizza "na lista" em pedido cancelado. Ela não aparece na fila nem sai em /proxima (filtro ped.situacao <> 'cancelado'), mas é contada em saldo_massa.necessidade (services/producao.py:117 não filtra pedido) e em /pedidos. Estado inconsistente permanente.

Correção: a mesma do achado 3 (travar o pedido em refazer e checar a situação depois da trava). Em saldo_massa filtrar pedido cancelado, ou fazer cancelar_pizzas rodar de novo a seleção depois de obter a trava.

## 9. Botão "Marcar pedido acabado" nunca aparece com refação (média)

Onde: api/routers/producao.py:81 e frontend/static/app.js, subAcabamento (condição `p.acabadas === p.pizzas`).

Cenário: pedido com uma pizza refeita. /producao/pedidos conta `pizzas` como tudo que não é "cancelada", ou seja, a original perdida mais a refação. Com a refação acabada: acabadas = 1 e pizzas = 2; a tela mostra "1 de 2" e esconde o botão, embora a API aceitaria acabar o pedido (linha 187 ignora a perdida refeita). A única forma é chamar a API à mão. O mesmo vale para pizza perdida e refeita no Andamento (contagem "1 de 2" enganosa).

Correção: no SQL contar apenas pizzas que não são canceladas nem perdidas-com-refação (mesmo critério do pedido_acabado) e devolver um campo `pode_acabar` calculado no servidor, que a tela usa.

## 10. Pizza perdida em montagem não baixa massa (média)

Onde: api/services/producao.py:113-116 (usadas contam só evento "no forno"); services/producao.py:83-91 e routers/producao.py:198-208.

Cenário: o pizzaiolo pega uma pizza, abre a massa e a perde em montagem (perder) ou o pedido é cancelado com a pizza em montagem. A massa foi consumida, mas não houve evento "no forno" e a perda registrada é do tipo "pizza", que saldo_massa ignora (só soma tipo = 'massa', linha 112). O saldo de massa aberta fica acima da realidade até a próxima contagem. Pizza perdida depois de ir ao forno é contada uma vez, pelo evento "no forno"; só o caso em montagem falha.

Correção: decidir a regra e fixá-la: ou usada = evento "em montagem" (e retrocesso devolve a massa), ou perda de pizza em montagem soma como perda de massa no tamanho certo. Se a decisão for manter, documentar. Adicionar teste.

## 11. Esgotamento da precisão da ordem (baixa)

Onde: migrations_pg/005_producao.sql (ordem NUMERIC(24,6)) e routers/producao.py:139.

Cenário: cada retrocesso entre o mesmo par divide a distância à metade. Com vizinhas de ordem 1 e 2, depois de cerca de 20 retrocessões a média arredonda para o mesmo valor de uma vizinha (seis casas) e a pizza fica empatada em vez de descer.

Correção: renumerar a fila (ordem inteira com espaçamento) quando a diferença ficar menor que, por exemplo, 0,001; ou usar posição inteira recalculada na própria transação sob a trava (5, loja).

## 12. iniciar-padrao concorrente devolve 500 (baixa)

Onde: api/routers/producao.py:280-292.

Cenário: duas chamadas simultâneas passam pela checagem de "vazio" e a segunda inserção de motivo_retrocesso viola uq_motivo_retrocesso. Não há try/except nem ON CONFLICT na tabela de retrocesso (só a de perda tem), então a resposta é 500.

Correção: pegar uma trava consultiva no início, ou usar ON CONFLICT DO NOTHING nas duas tabelas, ou envolver em try com traduzir_erro.

## 13. Rotas de escrita sem tratamento de erro do banco (baixa)

Onde: producao.py linhas 118-125, 157-176, 179-194, 198-235, 244-270.

Só retroceder, criar e alterar motivo capturam psycopg.Error. As demais deixam subir erros do banco (DeadlockDetected, exceção RAISE do trigger pizza_so_andamento, conexão). O handler geral devolve 500 genérico, sem vazar detalhe, mas sem mensagem útil e sem rollback explícito. Correção: um helper comum que faça rollback e traduza deadlock e serialização em 409 "Tente novamente"; teste de que erro de trigger não vaza texto.

## 14. Tabelas novas sem trigger contra TRUNCATE (baixa)

Onde: migrations_pg/005_producao.sql, bloco DO (só BEFORE UPDATE OR DELETE).

As tabelas auditoria (001) e ficha_versao, ficha_linha (003) têm também trigger BEFORE TRUNCATE FOR EACH STATEMENT. Nas de produção (evento_producao, retrocesso, lote_massa, contagem_massa, perda, etiqueta_impressa) e em pizza_producao, TRUNCATE passa e apaga o histórico "só de inserção". Correção: acrescentar o trigger de TRUNCATE no loop e em pizza_producao, como nas outras fatias. O teste test_banco_protege_a_pizza_e_o_historico também deve cobrir TRUNCATE.

## 15. Tela de Produção (baixa)

Onde: frontend/static/app.js, abaProducao.
a) seletorMotivo dispara a ação no onchange sem confirmar. Num tablet, um toque errado no select "Perdeu a pizza" registra perda irreversível (só inserção). Sugestão: botão de confirmar depois de escolher.
b) O setInterval de 8 s é criado só uma vez, quando abaProducao abre. Se o gerente abre em "massa" e vai para "montagem", a tela não atualiza sozinha (o pizzaiolo, que abre em montagem, atualiza). A atualização só pula quando o foco está em INPUT ou SELECT; o aviso de resultado (msg) nunca expira.
c) Chamadas de desenharSub podem se sobrepor (timer e clique): a resposta mais lenta vence e pode mostrar fila velha. Sugestão: contador de versão, descartando respostas antigas.

## 16. Sem índice único para refação e ordem (baixa)

Onde: migrations_pg/005_producao.sql.

"Uma refação por original" só se garante pela trava da linha e por um SELECT (producao.py:216); "ordem sem repetição" só pela trava consultiva (e não em retroceder, achado 7). Acrescentar CREATE UNIQUE INDEX sobre pizza_producao (original_id) WHERE original_id IS NOT NULL e sobre (loja_id, ordem) dá defesa no banco.

## 17. Lacunas de teste (baixa)

Nada em tests/test_producao.py cobre:
- concorrência (dois proxima simultâneos, proxima contra cancelar, dois retroceder, refazer contra cancelar ou acabado);
- retrocesso com pedido urgente na fila e com a fila de um item só;
- refazer e perder com pedido acabado, despachado ou cancelado (achado 3);
- /pedidos/{id}/situacao para "acabado" por gerente com pizzas pendentes (achado 4);
- perda de pizza por perfil massa e por outro pizzaiolo (achado 5);
- saldo de massa: perda e lote anteriores à contagem não contam; perda de pizza em montagem; calzone com parâmetro vazio; calzone com "grande";
- cancelamento com pizza acabada e com refação pendente; motivo de cancelamento renomeado ou inativo;
- contagem retornada de /pedidos com refação (achado 9);
- permissões negativas para forno (massa), refazer (pizzaiolo já testado), motivos e perda de massa por pizzaiolo e acabamento;
- XSS: sabores e observações com HTML devolvidos como texto na API (e teste de front);
- estimativa de entrega: o teste só confere "não nulo"; falta valor esperado, pedido de entrega, parâmetro ausente (deve dar nulo);
- iniciar-padrao concorrente, e PATCH de motivo com `nome: null`;
- TRUNCATE nas tabelas de histórico.
