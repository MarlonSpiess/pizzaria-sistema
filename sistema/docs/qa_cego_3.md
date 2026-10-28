# QA cego 3: Contas a Pagar/Receber e Fluxo de Caixa

Escopo lido: migrations_pg/009_contas.sql, api/routers/contas.py, api/services/contas.py, schemas de contas, abaContas em app.js, tests/test_contas.py, e os pontos de origem (caixa.py, compras.py).
Testes próprios (fora do projeto): /tmp/qa3/test_qa3.py, rodados com TEST_DB_HOST=/tmp/pgtest TEST_DB_PORT=5433 TEST_DB_NAME=qa3_teste. Nada do projeto foi alterado.
Legenda: CONFIRMADO POR TESTE ou POR LEITURA.

Pontos que resistiram: baixas simultâneas (4 threads, parcial e total) respeitam o saldo graças ao FOR UPDATE mais o gatilho; baixa não passa do título; conciliação 1 para 1 é protegida por UNIQUE; valores de entrada (1e3, +5, 5.555, dígitos árabes) são recusados; o front usa h() e textos (descrição com HTML foi aceita na API, mas só é renderizada como nó de texto, sem XSS); gatilhos de só inserção funcionam.

## Alta

### A1. Fracionar lançamentos foge do limite de aprovação (CONFIRMADO POR TESTE)
O limite `conta_valor_aprovacao` olha o valor de cada lançamento (valor x parcelas), não o acumulado. Cinco lançamentos de R$ 999,00 com limite de R$ 1.000,00 saíram todos com `aprovado=true`. Um gerente ou subgerente lança e paga R$ 5.000,00 sem segundo par de olhos. Agravantes: com o parâmetro vazio (padrão) nenhuma conta precisa de aprovação; recorrências, notas de compra e sincronizações nascem sempre aprovadas.
Sugestão: somar por fornecedor/tipo/criador numa janela (dia ou mês), e tratar recorrente acima do limite como pendente.

### A2. Mesma despesa vira dois títulos quando a nota é registrada depois da tela abrir (CONFIRMADO POR TESTE)
`sincronizar` roda a cada GET /titulos e /fluxo. A exclusão "sangria que pagou nota" só vale se o recebimento já existir. Fluxo real: o caixa faz a sangria de despesa para compra urgente, alguém abre Contas a Pagar (sincroniza e cria o título `sangria` baixado), depois a nota é registrada com `movimento_caixa_id`. Resultado no teste: 2 títulos de R$ 80,00 (origem sangria e origem recebimento), ambos baixados, despesa contada em dobro em relatórios e no realizado. Os índices únicos não pegam porque as origens diferem.
Sugestão: ao criar o título de recebimento com `movimento_caixa_id`, cancelar/absorver o título `sangria` existente (ou impedir a sangria de gerar título se ela ainda puder ser vinculada), e/ou índice que ligue as duas origens.

### A3. Listagem corta em 500 pelos mais antigos, e a tela esconde os títulos em aberto (CONFIRMADO POR TESTE)
GET /titulos faz `ORDER BY vencimento, id LIMIT 500` sem filtro de situação, e o front chama sem filtro e separa "abertos" no cliente. Cada sangria, nota, acerto e venda em cartão gera um título baixado por dia; em poucos meses os 500 mais antigos (já baixados) ocupam a lista. Com 520 baixados antigos, nenhum título em aberto apareceu: a tela mostra "Nada em aberto", total errado, e contas a pagar passam despercebidas.
Sugestão: a tela deve pedir `situacao=aberto` e `situacao=parcial` (e pendente) separadamente, ordenar o aberto por vencimento e os feitos por vencimento descendente com limite; o servidor deve devolver aviso quando truncar.

## Média

### M1. Desconto de 100% (e juros ilimitado) sem controle (CONFIRMADO POR TESTE)
`desconto <= valor` é permitido: um subgerente baixou um título de R$ 500,00 com desconto de R$ 500,00, movimento R$ 0,00, título "baixado" sem sair dinheiro. Também aceita juros de R$ 99.999.999,00 (movimento de R$ 100.000.009,00 num título de R$ 50). Não há limite, motivo, nem aprovação para desconto, juros ou multa. É a mesma brecha de perdão que o limite de aprovação deveria cobrir.
Sugestão: teto de desconto (parâmetro ou percentual), motivo obrigatório acima dele, aprovação para desconto em contas a pagar, e juros/multa com teto razoável.

### M2. Baixa de movimento zero fica eternamente pendente na conciliação (CONFIRMADO POR TESTE)
A baixa do M1 (valor_movimento 0,00) aparece na lista de baixas a conciliar, mas `extrato_linha.valor <> 0` impede casar. Fica como pendência para sempre.
Sugestão: não listar baixas de movimento zero, ou conciliá-las automaticamente.

### M3. Baixa parcial repetida (duplo clique) paga duas vezes (CONFIRMADO POR TESTE no nível da API, 3 de 4 chamadas simultâneas de R$ 100,00 em título de R$ 300,00 passaram; os valores são válidos, então não há erro)
Não há chave de idempotência nem o botão é desabilitado após o clique. Se o usuário digita um valor parcial e clica duas vezes, duas baixas são lançadas e o saldo da conta cai o dobro. Baixa total é protegida (só uma passa).
Sugestão: desabilitar o botão durante a requisição e enviar uma chave de idempotência por tentativa.

### M4. A tela de configuração "Canais de repasse" não tem efeito (CONFIRMADO POR LEITURA)
`canal_repasse` (taxa e prazo por canal: Anota Aí, iFood) é gravada, mas nenhum código a lê. A sincronização só usa `regra_recebimento` por forma (crédito, débito, pix). Vendas de aplicativo não geram título a receber, e o texto da tela e da migração promete "prazo e taxa vão para os títulos a receber".
Sugestão: gerar a receber por canal ou remover a promessa até a fatia existir.

### M5. Regra de recebimento aplicada pela mais nova, não pela vigente na data (CONFIRMADO POR LEITURA)
A consulta usa `ORDER BY id DESC LIMIT 1` e ignora `vigente_desde`. Como o título só é criado no primeiro acesso à tela, um fechamento de dias atrás recebe a taxa e o prazo da regra criada depois. O vencimento e a taxa esperada (base da taxa real) saem errados.
Sugestão: filtrar `vigente_desde <= fim do dia do caixa` e ordenar por vigente_desde.

### M6. Fluxo de caixa: projeção ignora pagamentos pendentes de aprovação e ignora taxa esperada (CONFIRMADO POR TESTE para pendentes, POR LEITURA para taxa)
Um título a pagar de R$ 5.000,00 pendente não alterou o menor saldo previsto, então o fluxo mostra folga que não existe se o pagamento for aprovado. Do outro lado, títulos a receber entram pelo valor bruto, sem descontar `taxa_pct`, o que superestima as entradas.
Sugestão: mostrar pendentes numa linha separada (ou dentro do cenário) e projetar o receber líquido da taxa esperada.

### M7. Saldo das contas mente em duas situações (CONFIRMADO POR TESTE e LEITURA)
a) Conta inativada some do saldo atual do fluxo: o teste mostrou o total caindo R$ 700,00 depois de inativar uma conta com esse saldo.
b) `saldo_conta` só soma baixas com `data >= saldo_inicial_data`. O front preenche a data com `new Date().toISOString()`, que é UTC; depois das 21h em Brasília o default vira amanhã. Conta criada à noite com a data sugerida ignora as baixas de hoje até o dia seguinte. A API ainda aceita baixas retroativas a qualquer data (antes do saldo inicial elas somem do saldo sem aviso). No teste, a data inicial de amanhã deixou o saldo em R$ 100,00 mesmo após pagar R$ 30,00 hoje.
Sugestão: no front gerar a data local; na API recusar baixa com data anterior ao saldo inicial da conta; manter contas inativas no saldo total (ou avisar).

### M8. Conciliação só casa 1 para 1, e não desfaz (CONFIRMADO POR LEITURA)
Um depósito de maquininha que liquida vários títulos, ou um pagamento em lote, não concilia. Não existe desfazer um casamento errado (conciliacao é só inserção sem rota de estorno). Também não há comparação do saldo calculado com o saldo do extrato.
Sugestão: casamento N para 1 e estorno com motivo.

## Baixa

### B1. Exceção não tratada (500) com vencimento no ano 9999 e parcelas (CONFIRMADO POR TESTE)
`_soma_meses` estoura `ValueError: year 10000 is out of range`. A validação de data só usa `date.fromisoformat`. Sugestão: limitar datas a um intervalo razoável (por exemplo hoje - 5 anos até hoje + 10 anos) em DataISO de contas.

### B2. Parcelas com dia 29 a 31 desalinham (CONFIRMADO POR TESTE)
Vencimento 31/01 com 3 parcelas gerou 31/01, 02/03 e 01/04 (mês pulado). Para dia até 28 usa mês calendário, acima disso soma 30 dias. Sugestão: usar o último dia do mês.

### B3. Divisão em muitas parcelas pequenas dá erro genérico (CONFIRMADO POR TESTE)
R$ 1,00 em 60 parcelas gera parcela de R$ 0,02 e a última negativa, resultando em 400 "Valor fora do domínio permitido". Sugestão: validar que valor >= 0,01 x parcelas com mensagem clara.

### B4. Sincronização escreve em requisições GET e roda a recorrência inteira a cada acesso (CONFIRMADO POR LEITURA)
Um perfil só com `contas.ver` dispara inserções. A cada abertura de tela são percorridos até 25 meses por recorrente, com INSERT ... ON CONFLICT para cada mês, sob lock consultivo da loja. Cresce com o número de recorrentes e serializa telas concorrentes. Sugestão: sincronização em rotina agendada ou só no POST /sincronizar.

### B5. Gatilho do título permite transições que a API proíbe (CONFIRMADO POR LEITURA)
`titulo_regra` aceita direto no banco 'aberto' para 'cancelado' com baixas existentes e 'aberto' para 'baixado' sem baixa; `comprovante`, `grupo_id` e `cancelado_motivo` ficam fora da lista imutável. `baixa_titulo_regra` não trava o título (depende do FOR UPDATE da aplicação). Risco só para acesso direto ao banco ou código futuro.

### B6. Cancelamento por qualquer operador (CONFIRMADO POR LEITURA)
Quem tem `contas.operar` cancela qualquer título manual, parcela ou recorrente aberto, inclusive de outro usuário, só com um motivo livre (auditado). Sem aprovação.

## Sem achado
Auto-aprovação direta: `aprovar` bloqueia criador igual a aprovador, inclusive em parcelas (o grupo herda o criador). Concorrência de baixa e de aprovação: serializadas por FOR UPDATE. XSS: todo texto vai por h()/createTextNode, sem innerHTML nem onclick inline.
