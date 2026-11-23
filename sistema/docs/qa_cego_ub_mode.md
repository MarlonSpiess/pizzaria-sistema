# QA cego: revisão geral do código

**Escopo:** api/ (main, database, security, config, schemas, routers, services), migrations_pg/, scripts/, tests/, tests_unidade/ e frontend/static/app.js por amostragem.
**Método:** leitura completa dos módulos de dinheiro, caixa, vendas, produção, estoque, compras, contas e RH; reprodução com pytest no banco qa_cego_teste (testes em scratchpad/qa_cego_repro/test_repro_a.py, test_repro_b.py, test_repro_c.py, todos passando, ou seja, o defeito acontece); tests_unidade rodados (56 passaram).
**Legenda:** CONFIRMADO = reproduzido; LEITURA = visto no código, não reproduzido.

As regras do dono listadas no pedido não foram tratadas como defeito. Os achados que citam uma dessas regras mostram que o código não a cumpre.

## Alta

### A1. A folha de pagamento chega à gerência pela conciliação, pelo saldo bancário, pelo fluxo e pela auditoria (CONFIRMADO)
- **Onde:** api/routers/contas.py:175 esconde o título de origem 'folha' só em GET /contas/titulos. Os pontos abaixo não têm o filtro:
  - pendencias_conciliacao, contas.py:316-324, que devolve descricao e valor_movimento;
  - contas_bancarias, contas.py:25-27, com o saldo;
  - fluxo, contas.py:346-372, com o realizado e a projeção.
  Também api/routers/auditoria.py:19 filtra só a ação 'lancar_folha', e a 'baixar' do título da folha fica visível.
- **Reprodução:** test_repro_b.py::test_folha_aparece_para_gerente_na_conciliacao_e_no_fluxo. O administrador lança a folha (um funcionário com contrato de R$ 4.321,00) e dá baixa. O gerente então recebe:
  - na conciliação, `{'descricao': 'Folha 11/2026 (prévia gerencial)', 'valor_movimento': '4321.00'}`;
  - em /contas/contas-bancarias, o saldo `-4321.00`;
  - no fluxo, `saidas: '4321.00'`;
  - na auditoria, `('baixar', {'valor': '4321.00', ...})`.
- **Impacto:** com poucos funcionários, o total da folha revela o salário de cada um. O resto do sistema trata isso como restrito a rh.salarios: custos.py:152, bi.py:98 e 134, e o filtro de títulos.
- **Correção:** centralize a regra numa função pura, por exemplo `oculta_folha(sessao) -> str`, que devolve o trecho SQL `AND t.origem_tipo <> 'folha'`. Aplique essa função em toda consulta sobre titulo e baixa_titulo: conciliação, fluxo e saldo, onde o saldo vira "parcial sem folha" ou some para quem não tem rh.salarios. Na auditoria, filtre por entidade_id dos títulos de folha. Acrescente um teste que percorra todas as rotas de contas com o perfil gerente e procure o valor do contrato na resposta.

### A2. O pizzaiolo marca como perdida uma pizza que está no forno ou já acabada (CONFIRMADO)
- **Onde:** api/routers/producao.py:247-261. `perder` exige só producao.perda, que o pizzaiolo tem (security.py), e aceita as situações "no forno", "saiu do forno" e "acabada" (linha 249). A trava de responsável só vale para "em montagem" (linhas 252-254).
- **Reprodução:** test_repro_a.py::test_pizzaiolo_perde_pizza_que_esta_no_forno_e_acabada. O pizzaiolo põe a pizza no forno e chama /perder: a resposta é 200 com `{"situacao":"perdida"}`. A fila já esconde dele essa pizza (test_acesso_rigido), mas a ação pelo id passa.
- **Impacto:** fura a regra "pizzaiolo só montagem". O pizzaiolo consegue gerar perda e baixa de estoque de pizza que é do acabamento, e isso cancela o andamento do pedido.
- **Correção:** no servidor, mapeie situação para permissão:
  - "em montagem" exige producao.montagem e ser o responsável;
  - "no forno", "saiu do forno" e "acabada" exigem producao.forno ou producao.acabamento.
  Faça isso com uma função pura `pode_perder(perms, situacao, responsavel, usuario)` testada em tests_unidade.

### A3. Gerente ou subgerente bloqueia o login de qualquer usuário que não seja dono, passando pelo RH (CONFIRMADO)
- **Onde:** api/routers/rh.py:136 e 153 aceitam qualquer usuario_id ativo ao criar ou alterar funcionário. Depois, desligar (rh.py:162-178) faz `UPDATE usuario SET ativo = false`. Só administrador e proprietário são poupados (linha 171).
- **Reprodução:** test_repro_a.py::test_subgerente_bloqueia_login_de_gerente_via_rh. O subgerente recebe 403 em PATCH /usuarios/{id}, mas faz o seguinte:
  1. cria um funcionário ligado ao usuario_id de um gerente;
  2. desliga esse funcionário e recebe 200;
  3. a sessão do gerente passa a dar 401 e o login do gerente falha.
- **Impacto:** usuarios.gerir é só do dono (security.py:28), mas rh.operar vira um caminho lateral para desativar qualquer login de gerente, atendente ou produção, inclusive o de um superior.
- **Correção:**
  - ao vincular usuario_id, exija usuarios.gerir, ou que o usuário ainda não tenha vínculo e tenha sido criado para aquele funcionário;
  - no desligamento, só bloqueie o login se quem desliga tiver usuarios.gerir; caso contrário, gere uma pendência para o dono;
  - recuse o vínculo com perfil igual ou superior ao de quem opera.

### A4. Pedido de entrega do balcão é despachado sem caixa aberto e sem entregador (CONFIRMADO)
- **Onde:** api/routers/vendas.py:294. A exigência de entregador, que obriga a ter caixa aberto por `_atribuir`, vale só para `p["canal"] != "balcao"`. A rota /pedidos/{pid}/situacao (vendas.py:311) deixa o atendente marcar "despachado ou retirado".
- **Reprodução:** test_repro_c.py. Sem nenhum caixa aberto, o atendente cria um pedido de entrega pago em dinheiro, a gerência o leva a "acabado" e o atendente o marca como despachado. A resposta é 200, e não há linha em `entrega`.
- **Impacto:**
  - fura a regra "despacho exige caixa aberto";
  - o dinheiro que está com o motoboy não entra em `com_entregador` (services/caixa.py:132-134), então o esperado da gaveta fica inflado e aparece como falta na contagem;
  - a entrega nunca é acertada nem paga ao entregador.
- **Correção:** para `tipo == 'entrega'`, qualquer canal, só deixe ir a "despachado ou retirado" se existir linha em `entrega`. Essa linha já exige caixa aberto. Escreva a regra numa função pura de transição, `pode_avancar(pedido, nova, tem_entrega)`, e teste as combinações.

## Média

### A5. Transferência entre locais deixa o local de origem negativo (CONFIRMADO)
- **Onde:** api/services/estoque.py:120 confere o saldo GLOBAL do item. A escolha dos lotes (linha 133) olha só lotes com saldo positivo no local e ignora o saldo negativo sem lote que a baixa automática deixou no mesmo local.
- **Reprodução:** test_repro_a.py::test_transferencia_deixa_local_negativo. A tem lote L1 = 10, perde 15 (A fica em -5) e recebe L2 = 10, então A = 5. B tem 10. A transferência de 10 de A para B devolve 201, e o saldo por local fica `{A: -5, B: 20}`.
- **Impacto:** fura a regra "estoque pode ficar negativo, transferência não". O inventário por local deixa de ser confiável.
- **Correção:** na saída do tipo transferência, confira `qtd <= sum(quantidade) WHERE item_id AND local_id` (saldo líquido do local, com e sem lote) antes de escolher os lotes, sob a mesma trava `trava_item`. O teste existente em tests/test_estoque_compras.py:95 aceita `in (201, 400)` e por isso não pegou o caso (ver A17).

### A6. Limites acumulados de sangria e de título manual furados por concorrência (CONFIRMADO para sangria, LEITURA para título)
- **Onde:** caixa.py:259 soma as sangrias sem autorização e depois insere. A única trava é `FOR SHARE` em caixa_dia (services/caixa.py:117), que não serializa duas sangrias. O mesmo padrão está em contas.py:200-202 (`conta_valor_aprovacao` acumulado do dia, sem trava).
- **Reprodução:** test_repro_b.py::test_sangria_concorrente_fura_limite_acumulado. O limite é R$ 100 e dois atendentes fazem sangria de R$ 90 ao mesmo tempo. Para alargar a janela que já existe entre o SELECT e o INSERT, outra conexão segura `LOCK TABLE movimento_caixa IN SHARE MODE` por 0,8 s. As duas respostas são 201, ou seja, R$ 180 sem gerente.
- **Impacto:** a proteção "conta o acumulado do dia, para não fatiar a retirada" (comentário em caixa.py:256) é contornável com dois terminais.
- **Correção:** serialize por loja e dia com `pg_advisory_xact_lock` antes da soma, como já é feito em banco de horas (rh.py, `pg_advisory_xact_lock(7101, fid)`), ou use `SELECT ... FOR UPDATE` no caixa_dia. A documentação do PostgreSQL sobre travas explícitas (Explicit Locking, advisory locks) descreve exatamente esse uso.

### A7. Pedido de compra digitado direto passa do valor de aprovação sem ninguém aprovar (CONFIRMADO)
- **Onde:** api/routers/compras.py:355 (`criar_pedido`). O texto da função admite: "só quem tem poder de aprovar emite (todos os compradores têm, por ora)". Não há nenhuma checagem. O caminho pela lista (compras.py, `definir` e `aprovar`) exige outra pessoa acima de `compra_valor_aprovacao`.
- **Reprodução:** test_repro_a.py::test_compra_direta_acima_do_limite_sem_aprovacao. Com limite de R$ 100, o gerente emite direto um pedido de R$ 5.000,00 e recebe 201 com situação "emitido".
- **Impacto:** a regra de quatro olhos da compra é contornada trocando de tela.
- **Correção:** acima do limite, crie o pedido em situação "aguardando aprovação" e reaproveite a mesma regra pura de `definir`, `precisa_aprovacao(total, limite)`, com aprovação por outra pessoa.

### A8. Subgerente perde mais do que "aprovar diferença de caixa" (CONFIRMADO)
- **Onde:** api/security.py:31 e 37 tiram do subgerente também `rh.aprovar`, e tests_unidade/test_permissoes.py:18 crava essa decisão. Além disso, caixa.py:20 (`APROVADORES` sem subgerente) e caixa.py:255 (`_aprova` = caixa.aprovar) fazem o subgerente precisar de gerente para sangria acima do limite e o impedem de autorizar a sangria de outro.
- **Reprodução:** os testes de unidade passam com `PERMISSOES["gerente"] - PERMISSOES["subgerente"] == {"caixa.aprovar", "rh.aprovar"}`, e tests/test_rh.py:144 confirma 403 do subgerente em banco de horas.
- **Impacto:** diverge da regra do dono, que é "subgerente tem as permissões do gerente exceto aprovar diferença de caixa". Banco de horas e sangria acima do limite ficam travados sem gerente.
- **Correção:**
  - deixe `_GERENCIA = _TODAS - _SO_DONO - {"caixa.aprovar"}`;
  - separe uma permissão `caixa.sangria_autorizar`, dada a gerente e subgerente, da `caixa.aprovar`, usada só no fechamento;
  - ajuste o teste de unidade para a regra do dono.

### A9. Pizza perdida de pedido já acabado: o pedido sai sem a pizza e não há como refazer (CONFIRMADO)
- **Onde:** producao.py:250 deixa perder uma pizza enquanto o pedido não está despachado nem cancelado, inclusive "acabado". Mas refazer (producao.py:271) só aceita pedido "recebido" ou "em producao".
- **Reprodução:** test_repro_a.py::test_perder_pizza_de_pedido_acabado_deixa_pedido_sem_pizza:
  1. o pedido fica acabado;
  2. a pizza é perdida (200);
  3. refazer devolve 409;
  4. o atendente despacha (200) o pedido com a única pizza perdida.
- **Impacto:** o cliente recebe o pedido incompleto, e o sistema mostra o pedido como concluído.
- **Correção:** escolha uma das duas regras e escreva-a numa função pura. Ou perder em pedido "acabado" é recusado, ou perder reabre a refação: aceite refazer com pedido "acabado" e bloqueie o despacho enquanto `pizzas_pendentes > 0`, também na transição para "despachado ou retirado".

### A10. A contagem cega do caixa não é cega para quem conta (LEITURA)
- **Onde:** caixa.py:61-83 esconde o esperado antes da contagem. Mas quem conta tem caixa.operar, e o atendente também tem vendas.ver. Com isso:
  - GET /pedidos (vendas.py:250) devolve o `total` de cada pedido do dia;
  - GET /pedidos/{id} (vendas.py:271) devolve os pagamentos por forma e o troco.
- **Raciocínio:** basta somar os pedidos do dia por forma para reconstruir o esperado antes de contar.
- **Impacto:** o controle de "contagem cega" perde o efeito antifraude.
- **Correção:** quando a sessão tem caixa.operar e o caixa está "aberto", devolva os pedidos sem valores (como já se faz para o acabamento), ou separe vendas.ver de vendas.ver_valores.

### A11. Venda feita num dia sem caixa cai no último caixa já fechado e nunca é contada (LEITURA)
- **Onde:** services/caixa.py:110-113 (`faixa` vai da data do caixa até a abertura do próximo), services/caixa.py:188-196 e vendas.py:194. Com o parâmetro `venda_exige_caixa_aberto` vazio, que é o padrão, a venda é aceita sem caixa.
- **Raciocínio:**
  1. o caixa de D fecha;
  2. em D+1 a loja vende sem abrir caixa;
  3. em D+2 abre caixa.
  Nesse cenário a faixa de D passa a ser [D, D+2) e inclui as vendas de D+1 num caixa cuja contagem já foi feita. A faixa de D+2 começa em D+2. O dinheiro de D+1 não entra em contagem nenhuma, e o relatório do caixa D muda depois de fechado.
- **Correção:** recuse a venda quando o último caixa está fechado e é de data anterior, independentemente do parâmetro, ou grave em pedido o `caixa_id` do momento em vez de deduzir a faixa por data.

### A12. Funções de segurança comitam a transação de quem as chama e soltam as travas (LEITURA)
- **Onde:**
  - security.py:111 e 116 (`registrar_falha_login` e `limpar_falhas_login` fazem `commit`);
  - security.py:99 e 104 (`rollback`);
  - chamadas dentro de rotas que já travaram linhas: vendas.py:177 e 191 (as avulsas são travadas com FOR UPDATE e depois `autorizar` comita); caixa.py:246, 262 e 312; vendas.py:352.
- **Raciocínio:** cada rota precisou reler e retravar depois de autorizar (vendas.py:353, caixa.py:263 e 315). Em `criar` pedido a trava das avulsas se perde, e quem segura a integridade é só a chave primária de pizza_avulsa_destino. A documentação do psycopg 3 (Transactions management) diz que um bloco interno "leaves the caller to deal with the main transaction": a transação é de quem a abriu.
- **Impacto:** qualquer rota nova que use `autorizar` sem reler herda uma condição de corrida silenciosa.
- **Correção:** grave as falhas de login numa conexão própria do pool, ou ao fim do request, e não comite a conexão do request dentro de `autorizar` e `exigir_login_liberado`.

## Baixa

### A13. O relatório de uma data sem caixa mostra o dia de hoje (CONFIRMADO)
- **Onde:** caixa.py:445-447 chama `_status(conn, None)`, e caixa.py:63 usa `(hoje(), FIM)` quando não há caixa.
- **Reprodução:** test_repro_a.py::test_relatorio_de_data_sem_caixa_mostra_o_dia_de_hoje. O pedido para `GET /caixa/2020-01-01/relatorio` devolve `data: 2026-11-06`.
- **Correção:** quando a data pedida não tem caixa, use a faixa `(data, data + 1 dia)`, ou devolva 404.

### A14. Erros dos gatilhos do banco viram 500 (LEITURA)
- **Onde:** database.py:80-94 traduz só as classes de integridade e dado. Os gatilhos (004_vendas.sql, 006_caixa.sql, 001_nucleo.sql `recusar_alteracao`) usam `RAISE EXCEPTION` sem ERRCODE, ou seja, SQLSTATE P0001 `raise_exception`, conforme a documentação do PostgreSQL ("Errors and Messages"). Esses erros caem em `_erro_geral` como "Erro interno".
- **Correção:** declare `ERRCODE = 'check_violation'` (ou um código próprio da classe 23 ou P0) nos gatilhos, ou mapeie `psycopg.errors.RaiseException` para 409 em `traduzir_erro`.

### A15. Rotas GET que gravam e serializam (LEITURA)
- **Onde:**
  - canais.py:42-44 faz INSERT e commit em GET /canais;
  - contas.py:160 e 351 rodam `svc.sincronizar` em cada GET de títulos e de fluxo, com `pg_advisory_xact_lock(loja, 7001)` (services/contas.py:38).
- **Impacto:** toda leitura de Contas espera as outras e escreve títulos. Isso contraria a semântica de métodos seguros do HTTP (RFC 9110, 9.2.1).
- **Correção:** semeie os canais na migration, rode a sincronização no POST /contas/sincronizar e no varredor, e deixe os GET só lendo.

### A16. A idempotência por `chave` devolve o pedido antigo mesmo com o corpo diferente (LEITURA)
- **Onde:** vendas.py:171-175 e 241. Um reenvio com a mesma chave e outros itens ou outro valor recebe 200 com o pedido anterior, sem aviso. A chave também não é ligada a quem criou o pedido.
- **Correção:** grave um hash do corpo normalizado junto com a chave e responda 409 quando o hash for diferente.

### A17. Testes que aceitam qualquer resultado e testes que cravam desvio de regra (LEITURA)
- **Onde:**
  - tests/test_estoque_compras.py:95 faz `assert r.status_code in (201, 400)` e por isso não detectou A5;
  - tests_unidade/test_permissoes.py:18 crava A8;
  - não há teste de ação de produção por id fora da tela (A2) nem de despacho de entrega do balcão (A4).
- **Correção:** monte o cenário determinístico (saldo por local conhecido) e afirme um único resultado. Inclua os quatro reprodutores de qa_cego_repro como testes de regressão.

### A18. Duplicação e código morto em torno de transação e constantes (LEITURA)
- **Onde:**
  - há cinco formas de gravar: `transacao`, `gravar_um`, `run` (usado uma vez, para um SELECT, em usuarios.py:28), try/except manual (vendas.py, caixa.py:392-402) e `conn.commit()` solto;
  - `contas_svc._novo` é privado e usado em rh.py:201;
  - `ZERO = Decimal(...)` aparece em 11 módulos e `_mes` em 4 (rh, bi, custos, imobilizado);
  - `EM_ANDAMENTO` (services/producao.py:17) nunca é usado;
  - `vigentes()` é chamado 3 a 4 vezes no mesmo request de criação de pedido (vendas.py).
- **Correção:**
  - deixe um único `transacao` e remova `run` e `gravar_um`;
  - exponha `novo_titulo` como função pública;
  - mova `ZERO` e `_mes` para services/dinheiro.py e um módulo de datas;
  - leia `vigentes` uma vez por request.

### A19. /health abre conexão nova fora do pool e sem autenticação (LEITURA)
- **Onde:** main.py:118-127.
- **Impacto:** uma rajada de GET /health abre uma conexão PostgreSQL por chamada (até o tamanho do threadpool) e esgota `max_connections`, contornando o limite que o pool impõe.
- **Correção:** use `pool.connection()` com timeout curto, ou guarde em cache o último resultado por alguns segundos.
