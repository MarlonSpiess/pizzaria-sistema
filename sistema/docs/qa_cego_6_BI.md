# QA cego 6: RH e BI

Escopo: api/routers/rh.py, migrations_pg/012_rh.sql, schemas de RH, abaRh e abaMeusDados, api/routers/bi.py e abaBi (frontend/static/app.js).
Método: leitura do código e testes próprios em /tmp/qa67 (banco qa67_teste, servidor uvicorn separado para as corridas). Nenhum arquivo do projeto foi alterado, fora este relatório.
Legenda: CONFIRMADO = reproduzido; LEITURA = visto no código, não reproduzido.

## Alta

### A1. Salário vaza para o gerente e o subgerente por três caminhos fora do RH (CONFIRMADO)
O BI esconde pessoal, EBITDA e resultado sem rh.salarios, mas o mesmo dado sai por outros endpoints que o gerente e o subgerente podem chamar.
1. GET /api/custos/resultado (custos.ver) devolve `fixos_detalhe.pessoal`, `custos_fixos`, `resultado_operacional` e `ponto_equilibrio` sem filtro. Reprodução: admin lança a folha do mês (POST /rh/folha/lancar), gerente chama /custos/resultado e vê `pessoal: 11333.32` e `resultado_operacional: -11333.32`. O endpoint reconstrói exatamente o que o DRE do BI oculta.
2. GET /api/contas/titulos e /contas/fluxo (contas.ver) mostram o título "Folha 10/2026 (prévia gerencial)" com o valor total. O alerta do painel BI ("saldo previsto fica negativo... menor: R$ -11333.32") também carrega o efeito da folha.
3. GET /api/auditoria (auditoria.ver, que o gerente tem) mostra o salário individual: a ação `contrato` grava `depois: {valor: "7777.77"}`, `beneficio` grava o valor do benefício, `folha_resumo` grava `bruto` e `lancar_folha` grava o total. Reprodução: admin cadastra contrato de 7777.77, gerente lista /auditoria e lê o valor junto do id do funcionário.
Correção sugerida: aplicar `_pode_salarios` em /custos/resultado (como em `_dre`); tirar valores de `depois` na auditoria de contrato, benefício e folha (ou filtrar essas entidades em /auditoria sem rh.salarios); ocultar títulos com origem_tipo = 'folha' para quem não tem rh.salarios.

### A2. Quem tem rh.operar desativa qualquer login, inclusive administrador e proprietário (CONFIRMADO)
`criar_funcionario` e `alterar_funcionario` aceitam qualquer `usuario_id` ativo (sem checar perfil) e `desligar` faz `UPDATE usuario SET ativo = false`. Reprodução: gerente ou subgerente cria funcionário com `usuario_id` de um administrador e chama POST /rh/funcionarios/{id}/desligar. O administrador passa a receber 401 na hora ("Sessão inválida ou expirada"). Também o subgerente vinculou o login de um proprietário a um funcionário (PATCH 200). Não há proteção de "último administrador" nem de "não desativar a si mesmo". Impacto: um gerente tranca o dono para fora do sistema. Correção: só vincular usuário de perfil operacional (ou exigir usuarios.gerir para vincular perfis acima de gerente) e, no desligamento, não desativar login de administrador/proprietário nem o último administrador.

## Média

### M1. Folha lançada em Contas usa só o resumo do contador, mesmo que cubra uma pessoa (CONFIRMADO)
`lancar_folha` troca a prévia pelo resumo se existir qualquer linha (`r["n"]` maior que zero). Reprodução: dois funcionários ativos (1000 e 2000), POST /rh/folha/resumo só para um (1500), POST /rh/folha/lancar cria título de 1500.00 "resumo do contador"; a prévia da mesma competência mostra 17333.32. A despesa de pessoal do mês e o DRE ficam subestimados sem aviso. Correção: usar o resumo por funcionário e completar com a prévia dos que não têm resumo, ou recusar quando o resumo estiver incompleto.

### M2. Resumo da folha digitado errado não tem correção (CONFIRMADO)
folha_resumo é só inserção (trigger) e tem UNIQUE (competencia, funcionario). Segundo POST do mesmo par dá 409 e não há endpoint de estorno. Um erro de digitação trava a competência ou obriga a lançar a folha com valor errado. Correção: estorno/versão (linha de ajuste) ou campo "vigente".

### M3. Contrato e admissão com data errada não têm saída (CONFIRMADO)
- Contrato novo precisa começar depois do vigente (400 "precisa começar depois do contrato vigente") e o contrato é imutável pelo trigger. Valor errado cadastrado no mesmo dia não pode ser corrigido. Cadastrar com `vigente_desde = 9999-12-31` é aceito, vira o "contrato atual" na listagem (mostrou valor 9.00 como vigente) e não pode mais ser trocado nem encerrado (só o desligamento encerra).
- Admissão aceita 0001-01-01, 2062-01-01 e 9999-12-31 (POST /rh/funcionarios 201) e o trigger proíbe alterá-la; a única saída é desligar. Falta limite de data (ex.: não depois de hoje e não antes de 1950) e um caminho de correção para o administrador.

### M4. Limite de hora extra do gerente contornável com data retroativa (CONFIRMADO)
O limite (rh_limite_extra_min_mes = 600) é somado por mês da `data` informada, e a data só não pode ser futura (pode ser 0001-01-01 ou anterior à admissão). Reprodução: gerente lançou +600 em cada um de 12 meses retroativos mais 500 hoje: saldo do banco 7700 min, quando o mesmo gerente leva 403 ao tentar +500 duas vezes no mês atual. Correção: exigir data dentro da admissão e de uma janela curta (ex.: 62 dias) para quem não tem rh.salarios, ou limitar também o saldo total.

### M5. Turno e ponto que viram a meia-noite são impossíveis (CONFIRMADO)
PUT /rh/turnos com 22:00 às 02:00 dá 400 "O fim do turno precisa ser depois do início"; 24:00 é recusado pelo schema; ponto tem CHECK (saida > entrada). Numa pizzaria que fecha de madrugada o turno noturno não pode ser lançado, e o ponto de quem sai depois das 00:00 precisa virar dois lançamentos (a tabela só admite um por dia). Correção: permitir fim menor que início como virada de dia (somar 24h) em turno, ponto e saldo.

### M6. Deadlock entre desligar e novo contrato gera 500 (CONFIRMADO)
`desligar` trava funcionario (FOR UPDATE) e depois atualiza contrato; `novo_contrato` trava contrato (FOR UPDATE) e depois insere (a FK segura funcionario). Disparados juntos para o mesmo funcionário, o desligar levou `psycopg.errors.DeadlockDetected` e voltou 500; o outro passou e o funcionário ficou ativo com contrato novo. `_ex` e `traduzir_erro` não tratam DeadlockDetected nem SerializationFailure (re-lançam). Correção: travar sempre na mesma ordem (funcionario FOR UPDATE primeiro em novo_contrato) e traduzir deadlock para 409.

### M7. Banco de horas: compensação concorrente deixa o saldo negativo (CONFIRMADO, intermitente)
`lancar_banco` lê o saldo e insere sem travar o funcionário. 16 requisições simultâneas de -100 sobre saldo 100: em uma das 3 rodadas duas passaram e o saldo ficou em -100 (a regra "compensação não passa do saldo" quebrou). O mesmo padrão vale para o limite mensal (LEITURA; não consegui estourar nas rodadas). Correção: `SELECT ... FOR UPDATE` no funcionário antes de calcular saldo e limite.

### M8. Mês 9999-12 na prévia e no lançamento da folha dá 500 (CONFIRMADO)
GET /rh/folha/previa?mes=9999-12 retorna 500 (`ini.replace(year=10000)` em `_previa`). O mesmo cálculo está em `lancar_folha` (vencimento padrão) e em `lancar_banco`. O `_mes` do RH não tem a faixa 2000 a 2100 que o BI tem. Só atinge quem tem rh.salarios, por isso média/baixa. Correção: reaproveitar o `_mes` do BI (ou calcular o mês seguinte com timedelta).

### M9. Perdas do painel do dia usam o fuso do banco (CONFIRMADO no SQL; depende do TimeZone do servidor)
`perda WHERE criado_em::date = %s` converte pelo TimeZone da sessão do PostgreSQL (aqui UTC; o app usa Brasília). `SELECT ('2026-10-21 22:00-03'::timestamptz)::date` devolve 2026-10-22. Perdas registradas depois das 21h entram no painel do dia seguinte. As demais consultas do BI usam `pedido.data` ou limites com tzinfo e estão certas. Correção: comparar com intervalo `[dia 00:00 -03, dia+1 00:00 -03)` ou `(criado_em AT TIME ZONE 'America/Sao_Paulo')::date`.

## Baixa

- B1. Folha prévia sem pró-rata (LEITURA): admitido ou desligado no meio do mês entra com o mensal cheio; troca de contrato no meio do mês usa o novo valor para o mês inteiro (`ORDER BY vigente_desde DESC LIMIT 1`). Aviso na tela ajudaria; a folha legal é do contador.
- B2. Ponto fora de regra (CONFIRMADO): aceita ponto depois do desligamento (funcionário desligado há 10 dias teve ponto lançado hoje) e em dia de férias; `banco-horas` aceita `data` anterior à admissão (ano 2000 para quem entrou há 100 dias).
- B3. Ausências: férias e atestado no mesmo dia são aceitos (CONFIRMADO; a checagem de sobreposição é só do mesmo tipo). Duas requisições simultâneas de falta no mesmo dia passaram (CONFIRMADO, 2 de 8); falta UNIQUE ou trava.
- B4. Turno aceita datas absurdas como 9999-12-31 (CONFIRMADO) e `lancar_turno` sobrescreve o turno do dia sem gravar o valor anterior na auditoria (LEITURA); o ponto grava `antes`.
- B5. `horas_semana` aceita "1e1" e dígitos não ASCII ("٤٠" virou 40.00) (CONFIRMADO, inofensivo, grava normalizado). "0.001" passa no schema e cai no CHECK do banco com 400 genérico.
- B6. BI `_mes` aceita " 2026-10" e dígitos largos "２０２６-10" (CONFIRMADO, inofensivo).
- B7. `competencia` da prévia para o ano 1 sai como "1-01" (`strftime('%Y')` sem zeros), cosmético.
- B8. abaMeusDados: banco de horas negativo exibe horas erradas (LEITURA): `Math.floor(-90/60)` = -2, mais abs(min)%60 = 30, mostra "-2h30" em vez de "-1h30". Só aparece se o saldo ficar negativo (ver M7). A aba também mostra erro 404 "Seu login não está ligado..." para gerente e administrador, que têm rh.proprio mas não são funcionários.
- B9. Lucratividade (LEITURA): `por_sabor` agrupa só pelo primeiro sabor (`p.nome`), então pizza meio a meio atribui toda a receita ao sabor 1 (a query agrupa por sabor2_id, mas o acumulador não usa). A receita é `preco_unit * quantidade` sem desconto nem taxa de entrega, então não bate com a receita do DRE.
- B10. DRE do gerente (LEITURA): `fixas` e `outras_fixas` ficam visíveis. Se o tipo "Folha de pagamento" for criado com natureza diferente de `pessoal` (o `lancar_folha` busca pelo nome, não pela natureza), a folha entra em `fixas` e vaza no BI. Vale validar a natureza do tipo usado pela folha.
- B11. `/rh/ausencias` expõe `motivo` (pode ser dado de saúde) a todo rh.ver, e /rh/escalados expõe nome e horário dos colegas a qualquer producao.ver (inclusive atendente). Decisão de privacidade, não bug.

## O que foi testado e está correto
- Permissões: atendente e pizzaiolo recebem 403 em todo /rh (menos meus-dados e escalados) e em /bi; subgerente e gerente não veem `valor` do contrato em /rh/funcionarios e levam 403 em /contratos, /beneficios, /folha/*; subgerente leva 403 em banco-horas (sem rh.aprovar). DRE, DRE em série e dre.csv do gerente omitem pessoal, EBITDA, resultado e ponto de equilíbrio.
- Entradas extremas: valor "100000000", "NaN", "1e5", "0", "-5", "0,001" recusados (422); 99999999,99 aceito sem erro; ids enormes (10**30) dão 404 ou lista vazia, sem 500; minutos 10**30 e 1.5 dão 422; nome com 121 caracteres, NUL e telefone de 30 dígitos dão 422; escala 7+7 dá 400; horas_semana NaN/Infinity/-1/60.004 recusados.
- BI com mês/data extremos: 9999-12 dá 400; 2100-12, painel de 2000 e 2100, lucratividade e produção fora do mês corrente dão 200.
- Triggers: admissão, contrato, banco_horas e folha_resumo imutáveis como projetado; unicidade de função, de usuario_id por funcionário (409) e do lançamento de folha (apenas 1 de 6 simultâneos passou).
- UI: `h()` monta com createTextNode e setAttribute, sem innerHTML; nome com `<img onerror>` foi gravado e é renderizado como texto. CSP `script-src 'self'` sem inline; o app.html só troca versões de css e js. Sem XSS achado em abaRh, abaMeusDados e abaBi.
- Banco de horas: limite mensal sob 16 requisições simultâneas segurou (1 de 16), embora sem trava explícita (ver M7).

## Resumo dos achados principais
1. Alta: o salário vaza para o gerente por /custos/resultado, /contas/titulos e pelo próprio /auditoria (valores de contrato, benefício e folha), contornando a proteção do BI.
2. Alta: quem tem rh.operar vincula o login de um administrador a um funcionário e o desligamento desativa a conta do dono do sistema.
3. Média: lançar folha com resumo parcial do contador ignora os demais funcionários; resumo e contrato errados não têm correção; admissão e contrato com data absurda são irreversíveis.
4. Média: limite de hora extra do gerente se contorna com datas retroativas; turno que passa da meia-noite é impossível; deadlock desligar x contrato e corrida de compensação no banco de horas.
5. Média/baixa: mês 9999-12 na folha dá 500; perdas do painel usam o fuso do banco.
