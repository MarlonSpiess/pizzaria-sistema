# QA não cego: revisão ub-mode

**Escopo:** commits 08522c7..c0b385f (12 commits) em `sistema/`, no worktree `qa_nao_cego` (HEAD c0b385f, nenhum arquivo do worktree alterado).
**Método:** leitura do diff inteiro; varredura por AST de todos os 69 blocos `with transacao(conn)` e conferência linha a linha dos 69 `conn.commit()` removidos; comparação da matriz de permissões antiga com a nova; suíte completa com cobertura (314 passed em 9 min 31 s, banco `qa_nao_cego_teste`); `tools/crapper.py`, `pylint duplicate-code` e `pyflakes`; 5 testes de reprodução em `qa_nao_cego_repro/test_repro_ub.py` (banco `qa_nao_cego_repro_teste`, 5 passed); documentação do psycopg 3 e do PostgreSQL.
**Legenda:** CONFIRMADO = reproduzido; LEITURA = visto no código, não reproduzido.

## Regressões

Não achei nenhuma regressão de comportamento nas refatorações. O que foi conferido:

- **(a) transacao:** cada um dos 69 `conn.commit()` removidos vinha logo antes do `except psycopg.Error`. Nenhum corpo convertido tem `return`, `break`, `continue`, `commit` ou `try` no meio. O único `rollback` que sobrou dentro de um bloco (`rh.py:503`, antes de uma HTTPException) era igual antes. Uma HTTPException no meio do bloco segue o mesmo caminho de antes: o `except psycopg.Error` não a pega, não há commit e o `get_db` desfaz a transação. Os 3 `_grava` e os 3 `_ex` eram idênticos a `gravar_um`/`transacao`. Os blocos com tratamento próprio (`caixa.py:397`, `compras.py:164`, `vendas.py:228`, `producao.py:378`, `imobilizado.py:386`, `usuarios.py:40`) ficaram intactos.
- **(b) permissões:** a matriz nova é idêntica à antiga em todos os 8 perfis (conferi carregando os dois arquivos). `requer = requer_alguma(permissao)` tem a mesma semântica.
- **(c), (d), (e):** `normalizar`, `preco_pizza`/`conferir_sabores`, `criar`, `receber` e `alterar_bem` mantêm a ordem dos passos e as mensagens. A única troca de ordem está em `_mudancas_do_bem`: a conferência da vida útil agora roda antes do `if not campos`. Ela não muda nada observável, porque a `ck_bem_metodo` (`migrations_pg/011_imobilizado.sql:39`) impede o estado que a dispararia.
- **(g):** é uma mudança de regra intencional e coerente com o comentário original. Tem teste que falhava antes.

## Alta

### A1. Custos calcula o preço da Grande meio a meio com outra regra, diferente da do dono (CONFIRMADO)
- **Onde:** `api/routers/custos.py:69-71`: `preco = ((preco + p2) / 2).quantize(Decimal("0.01"))`.
- **Evidência:** `test_R1`. Com sabores de R$ 35,01 e R$ 50,00, `/api/pedidos/calcular` devolve **42.51** (17,51 + 25,00, cada metade arredondada para cima), mas `/api/custos/produtos/{id}?sabor2_id=` devolve **42.50**. Custos tira a média e arredonda pelo modo bancário (ROUND_HALF_EVEN). A rota também não recusa o segundo sabor igual ao primeiro.
- **Impacto:** a margem e o preço sugerido da tela de Custos partem de um preço que o caixa nunca cobra. A regra "Grande com 2 sabores = metade de cada, arredondada para cima" ficou em dois lugares, e um deles está errado. O ub-mode pedia exatamente isto ("one decision lives in one place"), e o commit 9e1676d isolou a regra pura sem procurar a cópia.
- **Correção:** em Custos, montar os dois sabores e chamar `preco.preco_pizza("grande", [s1, s2], [])` (ou `metade_para_cima(p1) + metade_para_cima(p2)`), reaproveitar `conferir_sabores` e criar um teste com valores ímpares em centavos.

## Média

### M1. O 503 diz "tente novamente" mesmo quando a gravação já foi comitada, e repetir duplica (CONFIRMADO)
- **Onde:** `api/main.py:102-110`, em conjunto com as 36 rotas de gravação que comitam e só depois leem a resposta (por exemplo `compras.py:117` `return _detalhe(...)`, `caixa.py:234` `_status(...)`, `imobilizado.py:392`).
- **Evidência:**
  - `test_R5`: com `cotacao_resposta` travada (só é lida depois do commit), `POST /api/compras/listas` responde 503 "Tente novamente". O usuário repete, recebe 201, e ficam **2 listas** gravadas.
  - `test_R3`: `POST /caixa/abrir` responde 503 com o caixa já aberto. A repetição dá 409 "ainda não foi fechado", que confunde.
- **Impacto:** o commit 6ff27d5 parte da premissa de que a falha é sempre momentânea e segura de repetir. Isso só vale se nada foi comitado. Antes a mensagem genérica de 500 também dizia "tente novamente", mas agora há `Retry-After`, um sinal que proxy ou cliente podem seguir sozinhos. Na peça de manutenção (`imobilizado.py:392`), a repetição tiraria a peça do estoque duas vezes.
- **Correção:**
  - montar a resposta dentro do `with transacao` (antes do commit) nas rotas que criam;
  - ou marcar no `request.state`, dentro de `transacao`, que houve commit, e nesse caso responder 500 ou 200 com o recurso, nunca 503;
  - a longo prazo, aplicar a chave de idempotência que `vendas.criar` já tem nas outras criações.
- **Referência:** a documentação do PostgreSQL (13.5, Serialization Failure Handling) manda "retry the complete transaction, including all logic". Isso vale para a transação desfeita, não para a que já foi comitada.

### M2. QueryCanceled no 503 esconde consulta lenta e tem outras origens (LEITURA, com log CONFIRMADO)
- **Onde:** `api/main.py:103` e `:107`.
- **Evidência:**
  - `test_R2` mostra que o rollback acontece: a maquininha não fica gravada sob trava, e a conexão volta boa ao pool, como o teste do próprio commit também prova.
  - Mas o log fica em WARNING, só com o nome da classe ("Banco ocupado em POST /api/caixa/maquininhas: LockNotAvailable"), sem `exc_info`, sem `diag.message_primary` e sem SQL.
  - O SQLSTATE 57014 (QueryCanceled) vem tanto do `statement_timeout` quanto de `pg_cancel_backend()` (um administrador cancelando a consulta) e de `Connection.cancel()`. Um relatório que sempre passa de 30 s vai responder 503 "tente novamente" para sempre, e o log não diz qual consulta foi.
- **Impacto:** perde-se o diagnóstico que o `log.exception` dava antes. Esse diagnóstico é a causa raiz que o ub-mode manda corrigir ("a guard that only hides the crash is not a fix").
- **Correção:** logar `exc.diag.message_primary` e `exc.diag.sqlstate`. Para QueryCanceled, manter `log.exception` ou responder 504/500 quando a mensagem for "statement timeout". Deixar o 503 com Retry-After só para 55P03, 40001 e 40P01, que a documentação do PostgreSQL (13.5) recomenda repetir.

### M3. A regra "quem aprova" continua fora da matriz de permissões (LEITURA)
- **Onde:**
  - `api/routers/caixa.py:20` `APROVADORES = ("gerente", "proprietario", "administrador")`;
  - `api/services/vendas.py:17` `AUTORIZADORES = (...)`;
  - `api/services/vendas.py:27` `if perfil in ("administrador", "proprietario")`.
- **Evidência:** o commit 1e7bd50 diz "uma regra num lugar só", mas "subgerente não aprova diferença de caixa" vive em dois lugares: `caixa.aprovar` em `PERMISSOES` e a tupla `APROVADORES`. O teste `test_permissoes.py` fixa só a matriz.
- **Impacto:** se alguém mudar uma das duas cópias, a outra fica para trás sem nenhum aviso. Hoje as duas estão coerentes.
- **Correção:** `APROVADORES = tuple(p for p in PERFIS if "caixa.aprovar" in PERMISSOES[p])` e o mesmo para `AUTORIZADORES`, ou passar a autorização por permissão (`tem_permissao({"perfil": u["perfil"]}, "caixa.aprovar")`). Um teste de unidade amarra as duas pontas.

### M4. A complexidade de alterar_bem só mudou de lugar, e a parte nova está sem teste (CONFIRMADO pela medida)
- **Onde:** `api/routers/imobilizado.py:128` `_mudancas_do_bem`, com cc 15, cobertura 76,9% e **CRAP 17,8**.
- **Evidência:** o commit 5b79fd1 anuncia "alterar_bem() caiu de 23 para 7", mas a regra foi para uma função ainda acima de 10, que mistura regra com consulta (`SELECT 1 FROM depreciacao_bem`).
- **Correção:** passar `ja_depreciou: bool` como argumento e deixar a função pura em `services/imobilizado.py`, com testes de unidade. Assim ela entra no mutmut.

### M5. PATCH do bem com `valor_residual: null` dá 500 (CONFIRMADO, já existia antes, no código movido)
- **Onde:** `api/routers/imobilizado.py:131`. `parse_reais(None)` levanta ValueError, que ninguém trata.
- **Evidência:** `test_R4` recebe 500 "Erro interno".
- **Correção:** recusar o `null` no schema `BemUpdate` (ou tratá-lo como zero) e converter ValueError em 400.

## Baixa

### B1. Testes que passam mesmo sem o comportamento que anunciam (LEITURA)
- `tests/test_edicoes_cadastro.py:49-54`: o commit c0b385f diz que testa "troca de função e vínculo de login", mas o teste confere só `nome`. Se o UPDATE ignorasse `funcao_id` e `usuario_id`, o teste passaria. A linha 56 aceita `404 ou 409` sem decidir qual é a regra.
- `tests/test_imobilizado.py:76`: confere só o 200. Não confere que `responsavel` virou "Ana" nem que o valor residual ficou igual.
- `tests_unidade/test_permissoes.py:38` (`isinstance(p, frozenset)`) testa a implementação. Melhor tentar `PERMISSOES["administrador"].add(...)` e esperar AttributeError, ou nem testar.
- `tests_unidade/test_transacao.py` usa uma conexão falsa (aceitável para o helper), mas não tem teste de `gravar_um`.
- **O resto é comportamento verdadeiro:** preço, normalizar com status e mensagem, traduzir_erro e o teste de 503. Nenhum desses passaria com funções que devolvem nada. A única exceção é `test_um_sabor_em_qualquer_tamanho_passa`, e por definição, porque a função não devolve nada.

### B2. O docstring do teste de catálogo diz o contrário do comportamento novo (LEITURA)
- `tests_unidade/test_parametros_normalizar.py:96` diz "seria recusado sempre". Com a saída do ramo "Tipo de parâmetro não suportado", um tipo sem regra agora gera KeyError e **500**, não 400.
- O teste protege, mas o comentário engana. Trocar por `_REGRAS.get(tipo)` com 400 custaria uma linha e manteria o comportamento antigo.

### B3. `_NUMERO` aceita quebra de linha no fim (LEITURA, verificado no interpretador)
- `api/services/parametros.py:54` usa `^...$`. `normalizar("limite_desconto_atendente_pct", "5\n")` devolve `'5.00'`.
- Usar `re.fullmatch` ou `\Z`. Isso mostra que o argumento de "ramo inalcançável" do commit c7f2e84 depende de o `Decimal` aceitar espaço em volta.

### B4. O log da revisão citado no commit não existe (LEITURA)
- O commit 744de0e diz "resultados em docs/ub_mode_revisao.md", e o arquivo não está em nenhum commit.
- O ub-mode pede "Keep a Log". Sem ele, as medidas de CRAP e de mutação não podem ser auditadas.

### B5. Ferramentas (LEITURA)
- O `crapper.py` usa cobertura de linhas, não de ramos. Nos números de CRAP, isso pesa a favor das funções com `if` de uma linha.
- O `pyflakes` ainda acusa imports e variáveis mortos em `tests/` (`test_custos.py:9`, `test_bi.py:9`, `test_rh.py:71`, entre outros). O commit só limpou `api` e `scripts`.

## O que está certo

- **`transacao()` próprio em vez de `conn.transaction()`:** foi a escolha certa. Segundo a documentação do psycopg 3 (Transactions management), com transação implícita já aberta (as rotas leem e travam com FOR UPDATE antes de gravar), `conn.transaction()` só cria e libera um SAVEPOINT e **não comita**. O helper preserva o commit explícito. A troca foi mecânica e segura: 389 linhas a menos e nenhuma regressão.
- **Permissões:** a matriz é imutável, a gerência é derivada, e um teste procura erro de digitação em `requer(...)`. A exclusão de `rh.aprovar` do subgerente está documentada em `planejamento/modulos/08_RH.md`. As regras do dono continuam valendo: canal, mapa e aceitar sozinho exigem `canais.configurar`, que só administrador e proprietário têm.
- **Funções puras:** preço e parâmetros viraram funções puras com testes de unidade rápidos e mutmut configurado. A correção de `alterar_bem` (precedência do `if ... else`) tem teste que falhava antes.
- **Rollback no 503:** o rollback acontece (em `transacao` ou no `finally` do `get_db`) e a conexão volta utilizável ao pool. Os testes R2 e o de robustez provam isso.
- **Suíte completa:** verde (314 passed).

## Próximas 5 ações

1. **Uma só regra de preço meio a meio (A1):** Custos passa a chamar `preco_pizza`/`metade_para_cima`, com teste de centavos ímpares. Custo baixo e corrige número de dinheiro.
2. **503 só quando nada foi comitado (M1, M2):** montar a resposta antes do commit nas rotas que criam (ou marcar o commit no `request.state`). Logar `diag.message_primary` e `sqlstate`, e tirar o statement timeout do "tente novamente".
3. **Aprovador derivado da matriz (M3):** `APROVADORES`, `AUTORIZADORES` e o `perfil in (...)` de `vendas.py:27` derivados de `PERMISSOES`, com teste.
4. **Atacar o topo do CRAP, separando regra de banco:**
   - `bi._alertas` (CRAP 63,6, cobertura 57%);
   - `estoque.saida` (23,7);
   - `vendas.criar` (23,2): o `try` de gravação ainda tem cc 20, e `_gravar_itens` e pagamentos poderiam ir para `services/vendas.py`;
   - `_mudancas_do_bem` (17,8): torná-la pura (M4).

   Hoje são 48 de 834 funções com CRAP >= 10.
5. **Fechar a duplicação mecânica que sobrou e reforçar os testes:**
   - os 14 PATCH repetem `model_dump(exclude_unset=True)`, "Nenhum campo para alterar." e `sets = ", ".join(...)`: um helper `campos_para_update(d)` resolve;
   - completar as asserções de B1 (função e login do funcionário, responsável do bem);
   - escrever `docs/ub_mode_revisao.md` com as medidas (B4).

**Referências consultadas:**
- psycopg 3, Transactions management: https://www.psycopg.org/psycopg3/docs/basic/transactions.html
- PostgreSQL 16, 13.5 Serialization Failure Handling: https://www.postgresql.org/docs/16/mvcc-serialization-failure-handling.html
- PostgreSQL, Appendix A (códigos 55P03, 57014, 40001, 40P01): https://postgresql.org/docs/8.0/errcodes-appendix.html

**Reprodução:** `cd <worktree>/sistema && TEST_DB_NAME=qa_nao_cego_repro_teste python -m pytest -q -p no:cacheprovider -s --rootdir <repro> <repro>/test_repro_ub.py`
