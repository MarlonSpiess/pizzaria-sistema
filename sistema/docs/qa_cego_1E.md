# QA cego da fatia 1E, Fechamento de Caixa

Revisor independente, sem contexto prévio. Os 5 testes de `tests/test_caixa.py` passam. Escrevi 5 sondas novas em `/tmp/qa_1E/test_qa.py` (nenhum arquivo do projeto foi alterado). Cada achado marcado "confirmado" foi reproduzido contra o Postgres de teste; os demais vêm de leitura de código.

Resumo: 4 altas, 6 médias, 7 baixas. O cálculo do esperado por forma está correto nos cenários que verifiquei (fundo, suprimento, sangria, estorno, troco, entregador antes e depois do acerto). O ponto fraco é o que cerca o cálculo: virada de dia, valores livres para o atendente e contagem cega que vaza.

## Altas

### A1. Caixa de um dia nunca pode ser contado nem fechado depois da meia-noite (confirmado)
- `api/routers/caixa.py:272` (contar), `:298` (fechar), `:93-94` (pendentes). Todos usam `quando.date()`/`hoje()`. Nenhum endpoint recebe a data.
- Cenário: a pizzaria vende até 00:30 (comum). O atendente conta às 00:15: o sistema procura o caixa da nova data e responde 409 "O caixa de hoje não foi aberto". O caixa do dia anterior fica `aberto` para sempre. `/caixa/pendentes` o lista, mas nada o fecha. As entregas daquele dia também ficam sem acerto para sempre, porque `acertar` filtra `e.data = hoje` (linhas 376-378), e o dinheiro delas permanece como "com entregador".
- Sonda `test_04`: com o relógio adiantado um dia, a contagem devolve 409 e `/pendentes` mostra o caixa anterior.
- Correção: contar, fechar e acertar aceitarem a data (ou o id) de um caixa aberto, restritos a gerente para dias passados. Vendas, movimentos e estornos poderiam gravar na data do caixa aberto mais recente (conceito de turno), em vez de na data do calendário. Alternativa mínima: endpoint `POST /caixa/{data}/contagem` e `/fechar` para caixas anteriores.

### A2. Atendente define livremente o valor da entrega e a diária (confirmado)
- `api/routers/caixa.py:353` (atribuir_entrega) e `:388` (acertar). `EntregaIn.valor_entrega` e `AcertoIn.diaria` aceitam qualquer valor até 99.999.999,99, com `caixa.operar`, sem teto e sem autorização.
- Cenário (sonda `test_02`): o atendente atribui entrega com valor R$ 9.999,00 e acerta com diária de R$ 5.000,00. O sistema aceita e grava `saldo_gaveta = -14958,00`. O esperado em dinheiro cai R$ 14.999, o atendente retira esse dinheiro da gaveta e a contagem "bate". É uma sangria sem limite, sem motivo e sem autorização, disfarçada de pagamento a entregador.
- Correção: o atendente só usa os padrões dos parâmetros. Valor diferente do padrão (ou acima de um teto) exige `caixa.aprovar`/autorização de gerente, como já existe para sangria. Validar também que `saldo_gaveta` negativo não passe do dinheiro disponível na gaveta.

### A3. Limite de sangria não definido significa "sem limite" (por leitura de código)
- `api/routers/caixa.py:250-251`: `if limite is not None and valor > ...`. Com o parâmetro `sangria_limite_gerente` vazio (estado inicial do catálogo, padrão `None`), nenhum perfil precisa de autorização para qualquer valor.
- Cenário: instalação nova ou parâmetro limpo. O atendente lança sangria de R$ 5.000 "Depósito" e leva o dinheiro; o esperado cai igual e nada acusa. Em Vendas o critério é o oposto e correto ("limite não definido vale 0", `services/vendas.py:26`).
- Agravante: o limite é por lançamento, não acumulado no dia. Dez sangrias de R$ 49,99 passam sem gerente.
- Correção: parâmetro ausente vale 0 (tudo exige autorização), igual a Vendas. Considerar limite acumulado por dia e por usuário.
- Obs.: a sonda `test_05` não conseguiu exercitar o caminho porque o caixa do teste já estava contado; a conclusão vem do código, que é inequívoco.

### A4. Contagem cega vaza o esperado por vários caminhos (confirmado)
- `api/routers/caixa.py:66-72` mascara só `recebido_por_forma`, `vendas`, `descontos`, `acrescimos` e `acertos`. Continuam abertos antes da contagem:
  1. `pedidos_sem_cf` com o `total` de cada pedido (`services/caixa.py:48`). Antes de informar os CFs, a soma é o total vendido do dia. Sonda `test_01`: 2 pedidos de R$ 35, soma vazada R$ 70,00 enquanto `vendas` vinha `None`.
  2. `pedidos` (quantidade) em `_status`, sem máscara.
  3. `GET /pedidos?data=` e `GET /pedidos/{id}` (permissão `vendas.ver`, que o atendente tem) mostram total e pagamento por forma de cada pedido. Sonda: `detalhar` devolve `forma`, `valor` e `troco`. Somando os pedidos o atendente obtém o recebido exato por forma.
  4. A resposta de `POST /caixa/acertos` devolve `dinheiro_recebido` e `saldo_gaveta` (linhas 401-402) antes da contagem. Parte disso é inerente ao acerto físico, mas conta como vazamento do dinheiro de entregas.
- Impacto: o atendente que quer desviar informa exatamente o esperado e fica abaixo da tolerância. A "cegueira" só protege contra erro, não contra má-fé.
- Correção: mascarar `pedidos`, `pedidos_sem_cf[].total` e `cancelamentos.valor` antes da contagem. Para Vendas, restringir a listagem de pedidos do dia por forma a gerente, ou aceitar que o recurso é cosmético e documentar. Para o acerto, mostrar ao atendente só o que o entregador deve devolver se isso for indispensável.

## Médias

### M1. Forma de pagamento removida dos parâmetros some da conferência (confirmado)
- `api/routers/caixa.py:273-276`: a contagem exige exatamente as formas hoje aceitas. Sonda `test_03`: com `pix` retirado da lista depois de vender em Pix, a contagem aceita só dinheiro/crédito/débito (200). O Pix do dia não é contado nem confrontado. Se `dinheiro` fosse removido, a gaveta inteira escaparia.
- Correção: exigir a união das formas aceitas com as formas que tiveram qualquer movimento no dia (venda, estorno), e sempre dinheiro.

### M2. Fundo de troco declarado livremente na abertura
- `api/routers/caixa.py:224`: o atendente informa qualquer valor, inclusive diferente do padrão ou do que sobrou no dia anterior, sem autorização. O fundo entra direto no esperado (`services/caixa.py:28`).
- Cenário: a gaveta tem R$ 100, o atendente abre com fundo R$ 0, e ao final retira R$ 100; esperado e contado coincidem.
- Correção: se diferir do padrão (ou do dinheiro retido no fechamento anterior), exigir autorização de gerente ou registrar a divergência. Com Contas/Fluxo, ligar o fundo ao dinheiro que ficou no caixa anterior.

### M3. Gerência cancela pedido pago sem segunda pessoa, e o estorno sai sem autorização (por leitura de código)
- `api/routers/vendas.py:250-264` e `api/security.py:30-35`. Gerente e subgerente têm `vendas.gerir`; `_gerencia` dispensa autorização e `estorno.autorizado_por` fica NULL. O subgerente, que a regra proíbe de aprovar diferença de caixa, consegue gerar estorno em dinheiro sozinho, o que reduz o esperado do mesmo jeito que uma sangria.
- Planejamento I10: "estorno com motivo e autorização". Hoje só o atendente é conferido.
- Correção: estorno em dinheiro acima do limite exige outro aprovador (diferente de quem cancela), e `caixa.aprovar` ou o limite de sangria deveria valer para estorno também.

### M4. Auto-aprovação do gerente e aprovação por quem contou
- `api/routers/caixa.py:308-309`: quem tem `caixa.aprovar` aprova a própria diferença. O gerente pode contar e aprovar o resultado dele (`contado_por == aprovado_por`). Uma contagem do gerente fechada por um atendente com a senha dele também passa (linha 311; `autorizar` só barra `u.id == quem fecha`, não quem contou).
- Planejamento I5: "atendente contando e gerente aprovando".
- Correção: aprovador diferente de `contado_por`, ao menos para diferença acima da tolerância, com exceção explícita para proprietário se desejado.

### M5. Depois da contagem o dia acaba para a loja, sem reabertura nem correção
- `services/caixa.py:76-82` bloqueia toda venda, cancelamento e movimento depois de `contado`; `abrir` devolve 409. Contagem é única e imutável (`UNIQUE (caixa_id, forma)`, gatilhos).
- Cenários: (a) contagem às 21h numa loja que fecha às 23h: nenhuma venda mais é possível, nem com `venda_exige_caixa_aberto = não`. (b) campo em branco no front vira "0" (`app.js`, ação de contagem, `i.value.trim() || "0"`), grava falta enorme irreversível. (c) venda registrada entre a contagem física e o clique de registrar entra no esperado e gera falta falsa.
- Correção: estado `reaberto` por gerente com auditoria (nova contagem como linha nova, mantendo a anterior), e o front deve exigir todos os campos preenchidos em vez de assumir 0.

### M6. Cadastro de motivo é mutável e reescreve o passado
- `migrations_pg/006_caixa.sql:24-32` não protege `motivo_movimento` com gatilho; `PATCH /caixa/motivos/{id}` (linhas 134-152) altera `nome` e `vira_despesa`. O relatório faz JOIN com o motivo atual (`services/caixa.py:36-38`).
- Cenário: alterar `vira_despesa` ou o nome depois dos lançamentos muda retroativamente quais sangrias seguem para Contas a Pagar e como aparecem nos relatórios de dias já fechados.
- Correção: gravar `motivo_nome` e `vira_despesa` no `movimento_caixa` no momento do lançamento (ou tornar nome e `vira_despesa` imutáveis após o primeiro uso). Planejamento I9 também pede comprovante para despesa; hoje é texto opcional, mesmo com `vira_despesa` (`routers/caixa.py:257`).

## Baixas

- **B1. Entrega sem entregador atribuído conta como dinheiro na gaveta.** `services/caixa.py:24-26` e `routers/caixa.py:277`: só entregas atribuídas entram em `com_entregador`/pendências. Pedido de entrega pago em dinheiro e nunca atribuído gera falta esperada na contagem, sem aviso. Correção: a contagem exigir que todo pedido `tipo = entrega` ativo tenha entregador.
- **B2. Atribuição de entregador não tem correção.** `entrega` só aceita preencher `acerto_id` (gatilho, `006_caixa.sql:131-146`); `UniqueViolation` impede nova atribuição (`routers/caixa.py:359`). Entregador ou valor errado só se desfaz cancelando o pedido. Correção: reatribuição com auditoria antes do acerto, em linha nova.
- **B3. Esperado negativo.** Cancelar hoje um pedido pago ontem em Pix gera estorno de hoje sem recebimento de hoje: `esperado[pix] < 0`, contado `>= 0` e a diferença sai como sobra acima da tolerância. O dinheiro continua certo, mas o relatório de hoje fica estranho. Correção: ligar o estorno ao caixa do dia da venda ou sinalizar.
- **B4. Estouro numérico trava a contagem.** `contagem_caixa.diferenca` é NUMERIC(10,2). Com `contado` e `esperado` extremos (sangrias sem limite, A3) o INSERT falha com DataError, vira 400 genérico e o caixa não pode mais ser contado. Correção: teto nas entradas, ou NUMERIC maior.
- **B5. Gatilhos aceitam saltos e não amarram as tabelas filhas.** `caixa_so_avanca` (`006_caixa.sql:152-169`) permite `aberto -> contado` sem nenhuma linha em `contagem_caixa`, `contado -> fechado` sem `fechado_por`, e reescrever `contado_por`/`contado_em` enquanto a situação não muda. `contagem_caixa` não tem `CHECK (diferenca = contado - esperado)`. Nada no banco impede INSERT em `movimento_caixa`, `estorno` ou `pagamento` de uma data já contada; a garantia é só da aplicação. `entrega.acerto_id` (linha 103) não tem FK. Correção: CHECK, FK e validação no gatilho (contagens presentes ao ir para `contado`; campos de fechamento ao ir para `fechado`).
- **B6. Lock expirado vira 500.** `exigir_aberto` e `exigir_nao_encerrado` ficam fora do `try` em vários pontos (`routers/caixa.py:243,272`); um `LockNotAvailable` (lock_timeout de 10 s, venda lenta segurando FOR SHARE) escapa de `traduzir_erro` e responde 500 genérico. Correção: capturar e responder 409/503 "tente novamente".
- **B7. Detalhes menores.** (a) `PATCH /pedidos/{id}/cf` permite sobrescrever o CF a qualquer momento, inclusive em dia fechado, só com auditoria (`routers/vendas.py:232-241`). (b) Regra de recebimento aceita maquininha inativa (`routers/caixa.py:206-210`) e `pagamento.maquininha` nunca é gravado em Vendas, então a conferência por maquininha da I7 não é possível ainda. (c) Falha de validação 422 no front aparece como mensagem do handler (ok), mas o botão de contagem não desabilita após o clique: o segundo envio retorna 409 e a mensagem de sucesso é trocada por erro. (d) `APROVADORES` está fixo em `routers/caixa.py:20` em paralelo à permissão `caixa.aprovar`; os dois podem divergir. (e) Subgerente também não autoriza sangria acima do limite (usa `APROVADORES`); coerente com a decisão, só vale confirmar que é intencional.

## Verificado e sem achado

- **Esperado por forma** (`services/caixa.py:14-29`): `valor - troco` por forma, estorno por data do cancelamento, fundo + suprimento - sangria no dinheiro. Entregador: dinheiro de entrega ativa sem acerto sai do esperado, e depois do acerto fica `recebido - total_devido`. Confere com o teste do dia completo. Cancelamento de pedido já atribuído ao entregador não gera dupla subtração.
- **Concorrência**: venda, cancelamento, movimento, atribuição e acerto pegam `FOR SHARE` no caixa; contagem e fechamento pegam `FOR UPDATE`. A contagem espera as vendas em curso e depois rejeita novas. `autorizar` faz commit e solta os locks, mas `movimentar` e `fechar` relocam e revalidam a situação. Não encontrei deadlock: SHARE com SHARE é compatível e nenhum caminho pede lock de pedido depois de segurar o caixa em UPDATE. Abertura simultânea: coberta por `ON CONFLICT` e testada.
- **Permissões**: subgerente sem `caixa.aprovar`; `autorizar` exclui o próprio requerente, usuário inativo, `deve_trocar_senha` e perfil fora da lista; mesma resposta e mesma contagem de falhas para todas as recusas.
- **Front (`abaCaixa`)**: texto de usuário só entra por `createTextNode`; `h()` usa `setAttribute` só com valores do servidor ou do próprio formulário; sem `innerHTML`, sem handler inline; a CSP (`script-src 'self'`, `style-src 'self'`) não é violada. Sem XSS.
- **Valores**: zero e negativo recusados em `Reais`; `ReaisOuZero` só onde zero faz sentido; regex limita a 8 dígitos e 2 casas; Decimal em todo o cálculo; fuso fixo em Brasília no pool.
- **Integridade**: tabelas de movimento, estorno, contagem, acerto e regra são só de inserção, inclusive TRUNCATE; `caixa_dia` não volta de estado nem altera fundo.

## Prioridade sugerida
1. A1 (virada de dia), porque quebra o uso normal.
2. A2, A3 e M2 juntos: tudo que o atendente digita e vira dinheiro saindo da gaveta precisa de teto ou de gerente.
3. A4 e M1, que enfraquecem o controle central do módulo.
4. M3 a M6 e as baixas na fatia seguinte.
