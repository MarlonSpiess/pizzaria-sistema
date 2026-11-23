# QA não cego, segunda rodada ub-mode

> Nota (23/11/2026): os caminhos em /tmp são da máquina da revisão. Os reprodutores viraram `tests/test_qa_ub_mode2.py` e as respostas estão em `qa_resposta_ub_mode2.md`.

**Escopo:** branch atual de /home/user/pizzaria-sistema (HEAD 1db22cf), código em `sistema/`, conferido contra `docs/qa_*`, `docs/ub_mode_revisao.md` e `planejamento/`. Nenhum arquivo do repositório foi alterado.
**Método:** leitura dos 24 relatórios e respostas de QA; conferência no código de cada item dado como corrigido na rodada ub-mode (commits 4eb3a4d, 1faef59, d45e407); leitura das áreas menos cobertas (conciliação, baixa de títulos, vínculo de login no RH, venda avulsa, canais, varredor, frontend); suíte completa com cobertura (324 passed em 9 min 55 s, banco `naocego_teste`); pyflakes, dryer e crapper; reprodutores em `/tmp/claude-0/qa/test_qa_nao_cego_ub2.py` (4 testes, todos FALHAM hoje, ou seja, o defeito acontece).
**Legenda:** CONFIRMADO = reproduzido por teste que falha; LEITURA = visto no código.

Observação sobre a rodada de base: `/tmp/claude-0/qa/base.log` terminou com `59 passed, 265 errors` (falha de senha do PostgreSQL), então `/tmp/claude-0/qa/cobertura.json` só mede os testes de unidade e não serve para o CRAP. Rodei a suíte de novo e a cobertura válida está em `/tmp/claude-0/qa/cobertura_naocego.json` (log em `/tmp/claude-0/qa/naocego_suite.log`).

## Conferência das correções anteriores

| Achado | Situação no código | Teste que pega |
|---|---|---|
| Não cego A1 (meio a meio em Custos) | Corrigido. Custos usa `preco_meio_a_meio` (custos.py:74). Mas `preco_pizza` (preco.py:47) recalcula a regra no laço em vez de chamar a função: a "única definição" é falsa (ver N4) | test_preco.py:57 |
| Não cego M1 (503 após commit) | Corrigido como mitigação: Retry-After só em GET e HEAD, gravação pede conferência (main.py:107) | test_robustez.py:184 |
| Não cego M2 (log e QueryCanceled) | Parcial: o log tem SQLSTATE e mensagem, mas segue sem `exc_info`, e o `statement_timeout` continua 503 com Retry-After (ver N5) | nenhum para QueryCanceled |
| Não cego M5 (residual nulo) | Corrigido (imobilizado.py:131) | test_imobilizado.py:75 |
| Não cego B1 (asserções fracas) | Parcial: funcionário e bem conferem o dado; `test_edicoes_cadastro.py:56` ainda aceita `404 ou 409` | |
| Não cego B2, B3, B4 | Corrigidos (`_NUMERO.fullmatch`, docstring, log da revisão) | test_parametros_normalizar.py |
| Cego A1 (folha para a gerência) | Parcial: conciliação (GET) e auditoria filtram; a baixa e a conciliação (POST) ainda revelam e deixam pagar a folha (ver N1). Saldo e fluxo seguem pendentes por decisão | test_qa_ub_mode.py:96 |
| Cego A2 (pizzaiolo perde pizza no forno) | Corrigido (producao.py:255). A regra não virou função pura, como o próprio QA pedia, e `perder` passou a CRAP 10,2 | test_qa_ub_mode.py:33 |
| Cego A3 (RH bloqueia login da gerência) | Incompleto: só o vínculo foi travado; o desligamento continua bloqueando o login de um gerente vinculado pelo dono (ver N2) | test_edicoes_cadastro.py:59 só cobre o vínculo |
| Cego A5 (transferência negativa) | Corrigido (estoque.py:121) | test_qa_ub_mode.py:46 |
| Cego A6 (limites acumulados em corrida) | Incompleto: a sangria tem trava (caixa.py:260); o título manual, citado no mesmo achado, não (ver N3) | test_qa_ub_mode.py:64 só sangria |
| Cego A13, A14, A18 (parte), A19 | Corrigidos | test_qa_ub_mode.py:122, test_erros_e_senha.py:26 |

Não achei regressão de comportamento nas correções: a suíte inteira passa e as mudanças de cada commit fazem o que o commit diz. Os problemas são de correção incompleta (N1, N2, N3) e de qualidade (N4 a N8).

## Alta

### N1. O gerente descobre o valor da folha e consegue pagá-la pelas rotas de baixa e de conciliação (CONFIRMADO, correção incompleta do cego A1)
- **Onde:** `api/routers/contas.py:268` (`dar_baixa`) usa `_travar` (contas.py:230), que não filtra `origem_tipo = 'folha'`, e responde com o saldo em `contas.py:286` ("A baixa passa do saldo do título (R$ 4321.00)"). `api/routers/contas.py:329` (`conciliar`) põe o valor da baixa na mensagem de recusa em `contas.py:339`.
- **Reprodução:**
  - `test_N1_gerente_nao_descobre_nem_paga_a_folha_pela_baixa`: o gerente (sem rh.salarios) manda baixa de R$ 99.999.999 no id do título da folha e recebe o saldo exato; mandando sem valor, recebe 201 e `valor_movimento: 4321.00`, ou seja, paga a folha que não pode ver.
  - `test_N1b_gerente_nao_descobre_a_folha_pela_conciliacao`: o gerente lança uma linha de extrato de R$ -1,00 e tenta casá-la com o id da baixa da folha; a recusa diz "a baixa R$ -7538.00".
  - Os ids são sequenciais, então basta percorrê-los.
- **Impacto:** fura a regra "salário só com rh.salarios" que o A1 dizia ter fechado. Com poucos funcionários, o total da folha revela os salários.
- **Correção:** uma função única, por exemplo `filtro_folha(sessao)` ou `exigir_visivel(titulo, sessao)`, aplicada em `_travar` e na leitura da baixa em `conciliar` (responder 404 para quem não tem rh.salarios). Teste que percorre todas as rotas de contas com o perfil gerente procurando o valor da folha, como o QA cego já sugeria.
- **Classificação:** DEFEITO confirmado (correção anterior incompleta).

### N2. Subgerente bloqueia o login de um gerente desligando o funcionário que o dono vinculou (CONFIRMADO, correção incompleta do cego A3)
- **Onde:** `api/routers/rh.py:172-188`. A correção pôs a exigência de `usuarios.gerir` só no vínculo (`_conferir_vinculo`, rh.py:132). O desligamento continua fazendo `UPDATE usuario SET ativo = false` (rh.py:187) para qualquer perfil, exceto administrador e proprietário, sem olhar a permissão de quem desliga.
- **Reprodução:** `test_N2_subgerente_nao_bloqueia_login_do_gerente_ao_desligar`. O administrador cadastra o funcionário com o login do gerente (o caso normal: o gerente também é funcionário). O subgerente desliga e recebe 200; o gerente passa a receber 401. O mesmo vale para um login de atendente vinculado e depois promovido a gerente.
- **Impacto:** o caminho lateral do A3 continua aberto; o vínculo legítimo é justamente o caso comum.
- **Correção:** no desligamento, bloquear o login de perfil da gerência só se quem desliga tiver `usuarios.gerir`; caso contrário, recusar (409) ou desligar sem bloquear e registrar pendência para o dono. Regra numa função pura `pode_bloquear_login(perfil_alvo, permissoes)` com teste de unidade.
- **Classificação:** DEFEITO confirmado (correção anterior incompleta). A escolha entre recusar e gerar pendência é DECISÃO do dono.

## Média

### N3. Dois títulos manuais simultâneos furam o limite acumulado de aprovação (CONFIRMADO, parte não corrigida do cego A6)
- **Onde:** `api/routers/contas.py:200-202`. A soma do dia de quem lança é lida sem trava e o INSERT vem depois. A resposta do QA dá o A6 como corrigido, mas a trava entrou só na sangria.
- **Reprodução:** `test_N3_titulos_simultaneos_nao_furam_o_limite_acumulado`. Limite de R$ 100, o mesmo gerente lança dois títulos de R$ 90 em dois terminais ao mesmo tempo (a janela é alargada com `LOCK TABLE titulo IN SHARE MODE` por 0,8 s): os dois voltam `aprovado: true`, R$ 180 sem aprovação.
- **Correção:** `pg_advisory_xact_lock(<chave>, usuario_id)` antes da soma, como em `caixa.movimentar`, e o mesmo teste de corrida.
- **Classificação:** DEFEITO confirmado (correção anterior incompleta).

### N4. A regra do meio a meio continua em dois lugares (LEITURA)
- **Onde:** `api/services/preco.py:47-50`. `preco_pizza` soma `metade_para_cima` de cada sabor no laço, e `preco_meio_a_meio` (preco.py:38) repete a conta. Custos chama a segunda; o caixa, a primeira.
- **Impacto:** hoje dão o mesmo número (o teste da linha 59 compara as duas), mas a frase "única definição da regra" do docstring e da resposta ao QA não é verdade. Uma mudança futura numa só reabre o A1.
- **Correção:** `preco_pizza` calcula o total com `preco_meio_a_meio` e usa `metade_para_cima` só para descrever cada metade.
- **Classificação:** DEFEITO de qualidade (duplicação), sem efeito hoje.

### N5. Consulta lenta continua respondendo 503 "tente novamente" (LEITURA, correção parcial do não cego M2)
- **Onde:** `api/main.py:95-104`. `QueryCanceled` (57014) do `statement_timeout` em GET recebe Retry-After e "Tente novamente", e o log é `log.error` sem `exc_info`.
- **Impacto:** um relatório que sempre passa de 30 s fica em laço de "tente novamente" e o log não traz a pilha. É o que o M2 apontava; só a parte do log com SQLSTATE foi feita.
- **Correção:** para 57014 com "statement timeout", 504 ou 500 com `log.exception`; 503 com Retry-After só para 55P03, 40001 e 40P01. Teste com `SET statement_timeout` curto.
- **Classificação:** DEFEITO (correção anterior incompleta).

## Baixa

### N6. O crapper conta métodos de classe duas vezes (CONFIRMADO pela saída)
- **Onde:** `tools/crapper.py:26-34`. `radon.cc_visit` já devolve cada método como bloco próprio, e `funcoes()` devolve de novo os métodos da classe. Na saída aparecem em dobro `scripts/carregar_ficha_tecnica.py:30 chamar` e `api/schemas.py:252 _por_tipo`.
- **Impacto:** os totais "63 de 855" do `ub_mode_revisao.md` estão inflados (contagem e denominador).
- **Correção:** ignorar os blocos `Class` (usar só os de função), ou desduplicar por `(arquivo, linha)`.

### N7. As correções aumentaram a complexidade sem extrair a regra (LEITURA, medido)
- `producao.perder` passou a cc 10, CRAP 10,2 (a sugestão do A2 era `pode_perder(...)` pura).
- `custos.produto` está em cc 17, CRAP 18,3.
- `_mudancas_do_bem` está em cc 16, CRAP 18,0 (M4 continua pendente).
- A regra do vínculo de login (A3) também ficou dentro da rota.
- Nada disso entra no mutmut, que só olha funções puras.

### N8. Testes e código morto (LEITURA)
- `tests/test_edicoes_cadastro.py:56` aceita `404 ou 409` (resto do B1).
- O pyflakes acusa 4 variáveis mortas em testes: `test_rh.py:71` (`c1`), `test_rh.py:162` (`base_dia = ini if ini < date.today() else ini`, tautológica), `test_sistema.py:50` (`antes` nunca é conferido) e `test_permissoes_usuarios.py:57`.
- Os 25 "imported but unused" são importações de fixture do pytest; trocar por `conftest` ou `pytest_plugins`.
- Os testes de regressão não cobrem as rotas POST de contas com perfil gerente (por isso N1 passou) nem o desligamento com vínculo legítimo (N2).

## Ferramentas

- **pyflakes** (`api scripts tests_unidade`): limpo. Em `tests/`: 88 avisos (25 imports de fixture, 59 redefinições de fixture, 4 variáveis mortas listadas em N8).
- **dryer** (pylint duplicate-code, 6 linhas): 1 trecho, `scripts/carregar_cardapio.py:20-27` igual a `scripts/carregar_ficha_tecnica.py:60-67` (argparse e senha). O app está 10/10. Duplicações abaixo de 6 linhas que o dryer não pega: a regra do meio a meio (N4), `APROVADORES` e `AUTORIZADORES` (M3) e os 14 PATCH com `model_dump(exclude_unset=True)`.
- **crapper** (cobertura nova, 87% das linhas): 63 de 855 funções com CRAP >= 10 (com a contagem dupla de N6). Fora os scripts de carga sem teste:

| CRAP | cc | Cobertura | Função |
|---|---|---|---|
| 63,6 | 23 | 57,5% | api/routers/bi.py:62 `_alertas` |
| 27,2 | 23 | 80,0% | api/services/estoque.py:112 `saida` |
| 23,4 | 23 | 91,2% | api/routers/compras.py:435 `receber` |
| 23,2 | 20 | 80,0% | api/routers/vendas.py:170 `criar` |
| 21,0 | 21 | 95,8% | api/routers/vendas.py:52 `_resolver_avulsas` |
| 20,1 | 20 | 93,8% | api/routers/estoque.py:135 `config` |
| 19,2 | 18 | 84,4% | api/routers/contas.py:187 `criar_titulo` |
| 19,0 | 19 | 95 a 100% | `cardapio.alterar_produto`, `imobilizado.fechar_os`, `producao.fila`, `services/contas.sincronizar`, `services/canais.pode_aceitar_sozinho` |
| 18,3 | 17 | 83,3% | api/routers/custos.py:56 `produto` |
| 18,0 | 16 | 80,0% | api/routers/imobilizado.py:128 `_mudancas_do_bem` |
| 18,0 | 18 | 95,8% | api/routers/estoque.py:323 `fechar` |
| 17,6 | 17 | 87,5% | api/routers/usuarios.py:49 `alterar` |
| 17,0 | 17 | 100% | api/routers/caixa.py:61 `_status` |
| 16,8 | 16 | 85,2% | api/routers/estoque.py:177 `movimentar` |
| 15,6 | 13 | 75,0% | api/services/estoque.py:220 `baixar_pizza` |
| 14,2 | 13 a 14 | 80 a 90% | `contas.titulos`, `contas.dar_baixa` |
| 14,0 | 14 | 95% | `compras.definir` |
| 13,4 e 13,3 | 12 e 13 | 78 a 88% | `caixa._atribuir`, `caixa.fechar` |
| 10 a 12,1 | 10 a 12 | 79 a 100% | `imobilizado.criar_bem`, `vendas.precificar_item`, `backup._executar`, `vendas.totais`, `receitas._salvar`, `imobilizado.alertas`, `estoque.abrir_inventario`, `estoque.entrada`, `producao.montagem_errada`, `varredor.ciclo`, `cardapio.alterar_adicional`, `caixa.movimentar`, `compras.sugestoes`, `schemas._por_tipo`, `vendas._sabor_fechado`, `vendas.mudar_situacao`, `rh.turnos` (25% de cobertura), `receitas._dono`, `producao.perder`, `vendas._conferir_entrega_e_cliente`, `rh.lancar_banco`, `vendas.repartir_pagamentos`, `vendas.autorizar`, `contas._titulo_out` |

  - Scripts acima de 10: `aplicar_migrations_pg.main` (702), `carregar_ficha_tecnica.main` (600), `carregar_cardapio.main` (600), `criar_admin.main` (72), `restaurar_em_teste.main` (56), `aplicar_migrations_pg.listar_migrations` (56), `carregar_ficha_tecnica.chamar` (42, contado duas vezes), `conectar_com_retry` (30), `ler_csv` (20), `adquirir_lock` (20), `sem_acento`, `backup.main` e `conectar` (12).
  - Lista completa: `/tmp/claude-0/qa/crap.txt`.

## Pendências antigas ainda abertas (só lista, sem decisão)

**Decisão do dono (Marlon):**
- **ub-mode cego:**
  - A1 resto: saldo bancário, fluxo, painel do BI (`saldo_contas`) e projeção incluem a folha para o gerente;
  - A4: entrega do balcão despachada sem entregador nem caixa;
  - A7: pedido de compra direto sem aprovação acima do limite;
  - A9: pizza perdida em pedido acabado sem refação;
  - A10: contagem cega reconstruível pelos pedidos;
  - A11: venda sem caixa cai no caixa anterior fechado.
- **1A:** cifrar o backup enviado ao Drive.
- **1B:** inativar categoria não inativa sabores.
- **1D:** reclamação depois de acabado vira novo pedido.
- **1E:**
  - M2: fundo de troco livre;
  - M3: gerência cancela pedido pago sem segunda pessoa;
  - M5: reabertura de caixa;
  - B1: contagem com entrega em dinheiro sem entregador;
  - B2, B3, B5 a B7.
- **2AB:**
  - A3: limite de aprovação vazio;
  - M1: refazer baixa travada;
  - M4 a M13: nota duplicada, custo médio diluído, estorno de bebida, estoque inicial repetível, inventário mensal, contagem cega do inventário, rendimento do preparo, sangria e nota, validade, frete;
  - M12: rendimento na ficha.
- **3:**
  - M4: canais de repasse nos relatórios;
  - M5: regra de recebimento vigente na data;
  - M7: saldo sem conta;
  - B4 a B6.
- **4 e 5:**
  - 6 e 7: CMV com entrada inicial, devolução e peças;
  - 9: insumo sem custo;
  - 11: taxa de cartão de hoje;
  - 13: fator de correção em dobro com a perda;
  - 14 a 21.
- **6 (RH e BI):**
  - M2: correção de resumo e de contrato;
  - M3: hora extra retroativa;
  - M4: turno que passa da meia-noite;
  - M5 e M6: corridas do desligamento e do banco de horas;
  - baixas.
- **Ainda sem resposta:** a descrição do parâmetro `sangria_limite_gerente` diz "sangria ou suprimento", mas o código limita só a sangria (caixa.py:254).

**Técnicas, já reconhecidas como próxima rodada:**
- A12: `autorizar` e login comitam a transação de quem chama e soltam as travas;
- A15: GET que gravam (GET /canais, sincronização de contas em GET);
- A16: idempotência por chave sem conferir o corpo;
- A18 resto: `ZERO` e `_mes` repetidos, `contas_svc._novo` privado usado no RH;
- M3: `APROVADORES` (caixa.py:20), `AUTORIZADORES` e `perfil in (...)` (services/vendas.py:17 e 27) fora da matriz;
- M4: `_mudancas_do_bem` mistura banco e regra;
- CRAP dos itens da tabela acima;
- `test_ordem_de_servico_completa` depende da ordem da suíte;
- rotas com commit manual sem tradução de erro do banco (1D, 13), hoje cerca de 120 `conn.commit()` fora de `transacao`.

## Recomendação

Não dar a rodada ub-mode por fechada ainda. N1 e N2 reabrem dois achados de severidade alta que a resposta dá como corrigidos: um gerente lê e paga a folha e um subgerente tira o acesso de um gerente. Os dois se corrigem com uma regra pura e um teste cada. Ordem sugerida:

1. **N1:** filtro de folha único em `_travar` e em `conciliar`, com um teste que varre as rotas de contas como gerente.
2. **N2:** no desligamento, a permissão de bloquear login depende de `usuarios.gerir`. O dono escolhe entre recusar e gerar pendência.
3. **N3:** trava consultiva no título manual, com o mesmo teste de corrida da sangria.
4. **N4 e N6:** uma linha cada. Refazer a medida de CRAP depois de N6.
5. **N5:** separar o `statement_timeout` do 503.

Os 4 reprodutores de `/tmp/claude-0/qa/test_qa_nao_cego_ub2.py` devem entrar na suíte como testes de regressão quando cada correção for feita.

**Reprodução:** `cp /tmp/claude-0/qa/test_qa_nao_cego_ub2.py sistema/tests/ && cd sistema && TEST_DB_NAME=naocego_teste /home/user/venv/bin/python -m pytest -q tests/test_qa_nao_cego_ub2.py` (hoje: 4 failed). Depois, apagar a cópia.
