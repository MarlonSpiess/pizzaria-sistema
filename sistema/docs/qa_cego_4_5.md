# QA cego das fatias 4 (Custos) e 5 (Imobilizado)

Escopo lido: migrations 010 e 011, services e routers de custos e imobilizado, schemas, funções `abaCustos` e `abaImobilizado` do app.js, tests/test_custos.py e tests/test_imobilizado.py.
Nenhum arquivo do projeto foi alterado. Os testes próprios ficaram em /tmp/qa45 (cópia dos testes do projeto com links para o código), rodando com `TEST_DB_HOST=/tmp/pgtest TEST_DB_PORT=5433 TEST_DB_NAME=qa45_teste`.

Legenda: CONFIRMADO = reproduzido por teste; LEITURA = visto no código, não reproduzido.

## Resumo

| # | Gravidade | Tema | Situação |
|---|-----------|------|----------|
| 1 | Alta | Uma data ou taxa extrema derruba Bens e Resultado do mês para todos | CONFIRMADO |
| 2 | Alta | Aprovação da ordem de serviço não fica presa ao valor | CONFIRMADO |
| 3 | Média | NaN nas entradas gera erro 500 (fator, taxa, peça, leitura, limite) | CONFIRMADO |
| 4 | Média | Manutenção de terceiro sem tipo de despesa some do resultado | CONFIRMADO |
| 5 | Média | Baixa com data retroativa mantém a depreciação dos meses seguintes | CONFIRMADO |
| 6 | Média | CMV real fica negativo com estoque inicial lançado no mês | CONFIRMADO |
| 7 | Média | Peça de manutenção cai dentro do CMV real | LEITURA |
| 8 | Média | Baixa corre contra abertura de ordem: ordem aberta em bem baixado | CONFIRMADO |
| 9 | Média | Margem e preço sugerido com insumo sem custo ou produto sem ficha | CONFIRMADO |
| 10 | Média | PATCH de início de uso já informado devolve 500 | CONFIRMADO |
| 11 | Média | Taxa de cartão do resultado usa a regra de hoje, não a da data da venda | LEITURA (e fonte inspecionada) |
| 12 | Média | Fechamento do CMV sem trava de inventário nem de ordem de meses | CONFIRMADO |
| 13 | Média | Fator de correção e perda da ficha somam efeitos; baixa de estoque não usa o fator | LEITURA |
| 14 | Baixa | Soma das parcelas passa do valor depreciável em bens de valor pequeno | CONFIRMADO |
| 15 | Baixa | Duas ordens abertas para o mesmo plano | CONFIRMADO |
| 16 | Baixa | Início de uso retroativo lança depreciação em meses passados | CONFIRMADO |
| 17 | Baixa | Compra de bem lançada como título entra em duplicidade com a depreciação | LEITURA |
| 18 | Baixa | Auto-aprovação parcial: quem fecha pode aprovar | LEITURA |
| 19 | Baixa | Mês 9999-12 devolve 500 em CMV, resultado e custos de manutenção | CONFIRMADO |
| 20 | Baixa | Condição de corrida entre PATCH de parâmetros e geração de depreciação | LEITURA |
| 21 | Baixa | Detalhes de tela e de arredondamento | LEITURA |

Sem achado: XSS (nenhum innerHTML, href, eval ou insertAdjacent no código das duas abas; todo texto passa por `h()` e `createTextNode`; CSP `script-src 'self'`), divisão por zero em margem e preço sugerido (tratada), permissões de leitura e escrita (atendente 403, gerente não baixa nem aprova, quem abriu não aprova a própria ordem), baixa duplicada simultânea (4 chamadas paralelas: 1 x 201 e 3 x 409), fuso (limites do mês usam o fuso de Brasília e a sessão do banco também), dupla contagem de nota de compra, sangria que pagou nota e acerto de entregador no resultado (ver "Dupla contagem" ao fim).

## Alta

### 1. Data ou taxa extrema derruba Bens e Resultado do mês (CONFIRMADO)
`api/services/imobilizado.py`, `_prox` e `parcelas`. `gerar_depreciacao` roda em todo GET de `/imobilizado/bens`, `/imobilizado/bens/{id}` e em `resultado_mes` (via `depreciacao_mes`). Se algum bem produzir parcelas depois do ano 9999, `_prox` levanta `ValueError: year 10000 is out of range` e todas essas rotas devolvem 500, para todos os usuários, e não há como corrigir: bem não apaga (trigger), `inicio_uso` não muda depois de informado e a categoria não tem rota de edição de taxa.

Dois caminhos reproduzidos:
- Categoria com taxa fiscal `0,01` (a validação aceita qualquer valor maior que 0): vida = 120000 meses. Um bem com início de uso hoje quebra `GET /imobilizado/bens` e `GET /custos/resultado`.
- Bem com `data_aquisicao` 9999-01-01 e `inicio_uso` 9999-06-01 (`DataISO` aceita qualquer data válida): mesmo efeito.

Quem pode provocar: perfil com `imobilizado.operar` (gerente e subgerente), por erro de digitação. Correção sugerida: limitar taxa a um mínimo (por exemplo 1%), limitar datas (aquisição e início de uso entre 1990 e hoje mais 1 ano) e tratar o laço de `parcelas` sem estourar a data.

### 2. Aprovação da ordem de serviço não fica presa ao valor (CONFIRMADO)
`api/routers/imobilizado.py`, `aprovar_os` e `fechar_os`. A aprovação só grava `aprovado_por`; no fechamento, `precisa and not aprovado_por` é a única checagem, e `mao_obra` é informada de novo em cada tentativa de fechar. Reproduzido:
- Ordem com custo de R$ 350 (limite R$ 300) aprovada pelo administrador; depois o gerente fechou a mesma ordem com mão de obra de R$ 50.000,00 e o fechamento passou (200, `custo_total` 50000.00).
- Ordem aprovada antecipadamente, sem nenhum custo estimado (`aprovar` aceita ordem em execução mesmo sem `precisa_aprovacao`), fechada depois com R$ 9.999,00.
- Peças lançadas depois da aprovação (R$ 2.500 em estoque) fecham sem nova aprovação.

Efeito: o controle de alçada vale só para quem não sabe do truque. Sugestão: gravar o valor aprovado (`valor_aprovado`) e exigir nova aprovação se `custo_total` passar dele; recusar `aprovar` quando `precisa_aprovacao` for falso.

## Média

### 3. NaN nas entradas gera 500 (CONFIRMADO)
`Decimal("NaN")` não passa por `except Exception` quando a comparação vem fora do `try`, e gera `InvalidOperation` (500):
- `PUT /custos/fatores/{id}` com `"NaN"` (schema `FatorCorrecaoIn`, comparação `x < 1`).
- `GET /custos/produtos/{id}?margem_desejada=NaN` (comparação `den <= 0`; não chegou a ser exercitada no teste porque o produto de teste não existia, mas o código é o mesmo padrão; classificar como LEITURA).
- `POST /imobilizado/categorias` com taxa `NaN` ou `sNaN` (`x <= 0`).
- `POST /imobilizado/os/{id}/pecas` com quantidade `NaN` (`x <= 0`).
- `POST /imobilizado/bens/{id}/leituras` com valor `NaN`: o `quantize` do NaN passa, o valor `NaN` é gravado no banco (tabela insert-only, não se apaga) e, se existir limite, a comparação levanta 500.
- `PUT /imobilizado/bens/{id}/limites` com mínimo `NaN`: o limite NaN é gravado e a leitura seguinte dessa grandeza devolve 500 até alguém regravar o limite.
Correção: usar `x.is_finite()` antes de comparar, ou regex como em `parse_reais`.

### 4. Manutenção de terceiro sem tipo de despesa some do resultado (CONFIRMADO)
`fechar_os` busca o tipo `manutenção` por nome; se não existir (tipos padrão não iniciados, ou tipo renomeado ou inativado) o título nasce com `tipo_despesa_id` nulo. `resultado_mes` agrupa por natureza e ignora títulos sem natureza. Teste: ordem de terceiro fechada com R$ 400 de mão de obra, `outras_variaveis` do mês continuou 0,00. A despesa existe em Contas, mas não entra em margem, resultado nem ponto de equilíbrio, sem aviso. Sugestão: exigir tipo de despesa ao fechar ordem de terceiro com mão de obra, ou cair em uma natureza padrão e avisar.

### 5. Baixa com data retroativa mantém a depreciação posterior (CONFIRMADO)
`baixar_bem` aceita qualquer data entre a compra e hoje, mas as parcelas dos meses seguintes à data da baixa já podem ter sido lançadas por um GET anterior (tabela insert-only). Teste: bem com 6 parcelas lançadas (R$ 600), baixa datada 40 dias após o início de uso (deveria parar em R$ 200); depois da baixa o acumulado continuou R$ 600. `gerar_depreciacao` só impede novas parcelas; não há estorno. Sugestão: recusar baixa em data anterior à última competência depreciada, ou exigir que a data da baixa seja do mês corrente ou do último mês depreciado.

### 6. CMV real negativo com estoque inicial lançado no mês (CONFIRMADO)
`cmv_mes`: `real = inicial + compras - final`, e só `entrada_compra` conta como compra. Uma `entrada_inicial` dentro do mês aumenta o estoque final sem aparecer em compras: lançar R$ 1.000 de estoque inicial moveu o CMV real de -2.500,00 para -3.500,00 (inicial 0, compras 0, final 3.500). O mesmo vale para `devolucao_fornecedor` (sai do estoque sem abater as compras, infla o CMV) e para ajustes de inventário positivos. No primeiro mês de uso do sistema o CMV real fica inválido, e o resultado do mês usa esse valor (`cmv_valor`) até o fechamento. Sugestão: tratar `entrada_inicial` como parte do estoque inicial e `devolucao_fornecedor` como redução de compras; mostrar aviso quando o CMV real for negativo.

### 7. Peça de manutenção entra no CMV real (LEITURA)
`peca()` baixa o estoque como `consumo_interno`. O CMV real é derivado da variação de estoque, então esse consumo vira CMV; o teórico (só `saida_venda`) não o inclui e a "diferença real menos teórico" (lida como desperdício e desvio) fica poluída. O custo da peça também não aparece no resultado como manutenção, apesar de constar em `custos-manutencao`. Sugestão: separar consumo interno e peças de manutenção do CMV real (somar como outra linha), ou mostrar no relatório quanto do CMV real é consumo interno.

### 8. Corrida entre baixa e abertura de ordem (CONFIRMADO)
`abrir_os` não trava a linha do bem; `baixar_bem` trava (FOR UPDATE) e checa ordens abertas, mas uma ordem inserida logo depois da checagem passa. Em 5 de 5 tentativas com as duas chamadas em paralelo, baixa e abertura devolveram 201 juntas, deixando ordem aberta num bem baixado (que então não depreciaria mais, não aparece em `_planos` e o bem não pode ser alterado). Sugestão: `SELECT ... FOR SHARE` ou `FOR UPDATE` no bem em `abrir_os`, `conferir`, `criar_plano`, `definir_limite` e `leitura`.

### 9. Margem e preço sugerido com insumo sem custo ou produto sem ficha (CONFIRMADO)
- Produto com insumo sem custo médio: a lista mostra custo 0,00, margem 35,00 e margem 100,00%, só com a observação "(insumo sem custo)" na célula de porcentagem. O preço sugerido para 50% de margem saiu R$ 0,00.
- `GET /custos/produtos/{id}` para produto sem ficha devolve `margem` calculada (50,00 com custo 0,00); a lista esconde a margem em `sem_ficha`, o detalhe não.
- `/custos/produtos/{id}` e `_margem` ignoram taxa de canal (iFood e similares) e a taxa média de cartão inclui regras de Pix, enquanto o resultado do mês só cobra crédito e débito. Margem do produto fica mais otimista que a do resultado.
Sugestão: suprimir margem e sugestão quando `sem_ficha` ou `itens_sem_custo` não estiver vazio, e usar a mesma definição de taxa nos dois relatórios.

### 10. PATCH de início de uso já informado devolve 500 (CONFIRMADO)
`alterar_bem` só barra mudança de `inicio_uso` quando já existe depreciação. Bem com início de uso no futuro (sem parcelas) aceita a primeira alteração (200) e a segunda cai no trigger `bem_regra`, cuja `RaiseException` não é tratada por `traduzir_erro`: 500 (`psycopg.errors.RaiseException`). Também ocorre com outras violações de trigger. Sugestão: checar `b["inicio_uso"]` no router (409) e tratar `RaiseException` como 409 ou 400.

### 11. Taxa de cartão do resultado usa a regra vigente de hoje (LEITURA, verificado pelo código-fonte)
`resultado_mes` e `taxa_cartao_media` buscam a regra de recebimento mais recente (`ORDER BY vigente_desde DESC`) sem `vigente_desde <= data do pedido`. Mudar a taxa da maquininha reescreve as taxas de todos os meses passados e uma regra com vigência futura já vale hoje. O mês fechado do CMV congela o CMV, mas não essa taxa. Sugestão: filtrar por `vigente_desde <= d.data`.

### 12. Fechamento do CMV sem trava (CONFIRMADO)
`fechar_cmv` só confere se o mês terminou. O subgerente fechou o mês anterior vazio e o mês 2000-01 (201 nos dois). Como a tabela é insert-only, o valor é definitivo, e o texto "depois do inventário completo" não é verificado. Sugestão: exigir inventário concluído no mês (ou confirmação explícita registrada), exigir ordem cronológica (mês anterior fechado) e limitar a meses com movimentação; considerar restringir o fechamento a quem tem `aprovar`.

### 13. Fator de correção e perda da ficha (LEITURA)
`custo_unidade` multiplica a quantidade da ficha (que já tem `perda_pct`) pelo fator de correção. No teste do próprio projeto 100 g com 10% de perda e fator 1,2 resultam em custo 13,20 (1,10 x 1,20). Se perda e fator representam a mesma limpeza, o custo conta duas vezes. Além disso a baixa de estoque (`consumo_ficha`) não aplica o fator, então o CMV teórico ficará abaixo do custo do produto mostrado. Vale definir qual dos dois é a regra e documentar na tela.

## Baixa

### 14. Parcelas passam do valor depreciável em bens de valor pequeno (CONFIRMADO)
`parcelas` arredonda a parcela mensal e só o último mês absorve a diferença; se o arredondamento para cima acumular mais que o valor, a última parcela fica negativa e é descartada (`if v > 0`), e a soma excede a base. Teste: R$ 10,00 em 600 meses somam R$ 11,98; R$ 1,00 pela taxa de 10% soma R$ 1,19 (valor contábil negativo). O mínimo de bem vem do parâmetro `bem_valor_minimo`, que por padrão é nulo. Sugestão: parar a série quando o acumulado chegar à base.

### 15. Duas ordens abertas para o mesmo plano (CONFIRMADO)
Nada impede abrir duas ordens preventivas com o mesmo `plano_id`; a tela mostra o plano vencido até o fechamento de uma delas, o que convida a abrir a segunda. Sugestão: recusar nova ordem se já existir ordem aberta ou em execução para o plano.

### 16. Início de uso retroativo lança depreciação em meses passados (CONFIRMADO)
`alterar_bem` aceita `inicio_uso` em qualquer data a partir da compra. Bem comprado em 2000 com início de uso em 2000-01-01 foi depreciado de uma vez, R$ 12.000,00 acumulados, espalhados por 20 anos de competências já encerradas (o resultado de meses passados muda e o de hoje ainda recebe só a parcela atual). Sugestão: exigir confirmação e/ou limitar a retroatividade ao mês corrente.

### 17. Compra de bem lançada como título (LEITURA)
`criar_bem` não gera título e o enum `tipo_despesa.natureza` não tem "investimento". Se a compra do bem for lançada em Contas com natureza `outra` (que entra nos custos fixos) ou `fixa`, ela é despesa integral no mês e depois depreciação todo mês. Sugestão: natureza própria "investimento" fora do resultado, ou ligar o título ao bem (`titulo.bem_id` já existe) e excluir esses títulos.

### 18. Auto-aprovação parcial (LEITURA)
Só se impede que quem abriu a ordem a aprove. Quem executa, lança as peças e informa a mão de obra pode aprovar (administrador ou proprietário que não abriu). Para separação real de funções, comparar também com `fechada_por` e com quem lançou as peças (`os_peca` não guarda o usuário).

### 19. Mês 9999-12 devolve 500 (CONFIRMADO)
`_mes()` de custos e a conversão de `custos-manutencao` aceitam ano 9999; `limites_mes` e `prox` estouram em 10000. Sem consequência de dados.

### 20. Corrida entre PATCH de parâmetros e depreciação (LEITURA)
`gerar_depreciacao` não trava a linha do bem. Um `PATCH` de método, vida útil ou residual feito entre a leitura de "ainda sem parcelas" e o commit de uma geração em andamento deixa parcelas calculadas com os parâmetros antigos e o resto com os novos (a soma deixa de fechar com a base). Janela estreita.

### 21. Detalhes
- Tela do resultado: lista "fixas, pessoal, depreciação", mas omite "outras", que entra em `custos_fixos`; a soma da tela não fecha quando existe despesa de natureza `outra`. Rótulo "Receita (produtos + entrega, sem descontos)" contradiz a fórmula (receita líquida de descontos).
- Ponto de equilíbrio nulo aparece como célula vazia, sem explicação (margem de contribuição zero ou negativa).
- `cmv_pct` usa vendas sem taxa de entrega, enquanto a receita do resultado inclui entrega: percentuais diferentes entre abas.
- Preço da Grande de dois sabores no detalhe usa média simples; a venda real arredonda cada metade para cima (`metade_para_cima`); diferença de 1 centavo.
- Peça de item sem custo médio entra na ordem com custo 0, sem aviso.
- Peça: `custo_atual` é lido depois da saída; uma compra simultânea poderia gravar custo diferente do usado na movimentação.
- Vida útil fiscal usa `to_integral_value` (arredondamento bancário): taxa 7% vira 171 meses, sem informar a aproximação.
- `GET` que gravam: `resultado_mes` chama `gerar_depreciacao` em transação que o `get_db` desfaz no fim; funciona, mas o cálculo se repete a cada consulta e segura o lock consultivo da loja.
- `Dar baixa` na tela usa `prompt()` livre para o tipo; erro de digitação cai em 422 com mensagem do servidor (aceitável).

## Itens verificados sem defeito

- Depreciação linha reta: 12000 / 120 meses = R$ 100 por mês, última parcela absorve centavos (3 parcelas 333,33 / 333,33 / 333,34), bem sem início de uso não deprecia, mês do início conta parcela cheia, mês da baixa é depreciado inteiro (comportamento documentado no código), baixa anterior ao início de uso não gera parcela.
- Mudança de parâmetro depois de depreciar: `alterar_bem` devolve 409 para início de uso, método, vida útil e residual quando já existem parcelas; valor, data, categoria e plaqueta são imutáveis por trigger; vida útil fora de 1 a 600, residual maior que o valor e quilometragem negativa ou enorme voltam 400.
- Baixa: só administrador e proprietário; data fora do intervalo devolve 400; bem com ordem aberta devolve 409; baixa dupla simultânea devolve 1 x 201.
- Ordem de serviço: não avança fora da sequência (trigger), ordem fechada ou cancelada não muda, cancelamento com peça lançada é recusado, quem abriu não aprova (403), peça só da classe consumo, com saldo (400 sem saldo).
- Resultado do mês: título de nota de compra (`recebimento`), sangria que pagou nota e acerto de entregador não duplicam despesa (nota fica fora da despesa e vira CMV pelas entradas; o título do acerto não tem tipo de despesa e entra uma vez como `entregas`; sangria de despesa pequena entra uma vez como variável). Mão de obra de funcionário não gera título (folha), manutenção de terceiro gera um título só (com a ressalva do item 4).
- Custo do produto: Grande com dois sabores soma uma meia receita de cada, Grande de sabor único soma duas meias, broto uma, ficha-base de tamanho entra, margem desejada negativa, textual ou 100% volta 400, divisão por zero evitada (`preco > 0`, `den <= 0`).
- Fuso: limites do mês usam o fuso de Brasília e a sessão do banco usa o mesmo fuso, então `fechada_em::date` não desloca a data.
- XSS e CSP: sem sinks perigosos nas duas abas.

## Lacunas de teste

Os testes atuais não cobrem: fechamento do CMV com conteúdo (só status), entrada inicial e devolução no CMV, qualquer dos casos de NaN, bem com data ou taxa extremas, baixa retroativa e acumulado, aprovação vinculada a valor, corrida baixa x ordem, plano com duas ordens, `resultado` com título de manutenção sem tipo, e `PATCH` de início de uso repetido.
