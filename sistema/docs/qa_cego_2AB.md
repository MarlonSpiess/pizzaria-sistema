# QA cego das fatias 2A (Estoques) e 2B (Compras)

Revisão independente, sem contexto prévio além do código e do documento 04_Estoques_e_Compras.md.
Suíte existente: 11 testes passando (banco pizzaria_qa_teste). Testes próprios: 17, todos passando, cada um **confirma** um defeito descrito abaixo. Estão em
`/tmp/claude-0/-home-claude-pizzaria-sistema/90d7f4eb-e4ea-550a-a4e4-568a2c0c6d69/scratchpad/qa/test_qa_2ab.py` (nenhum arquivo do projeto foi alterado, só este relatório foi criado).
Comando: `TEST_DB_NAME=pizzaria_qa_teste TEST_DB_HOST=/tmp/pgtest TEST_DB_PORT=5433 python3 -m pytest -q -s <arquivo> --rootdir=/home/claude/pizzaria-sistema/sistema`

Resumo: 5 achados de severidade alta, 13 médios, 12 baixos. Nenhum problema de XSS ou de CSP.

Legenda de caminhos: `S/estoque.py` = api/services/estoque.py; `S/compras.py` = api/services/compras.py; `R/estoque.py` e `R/compras.py` = api/routers; `app.js` = frontend/static/app.js.

---

## ALTA

### A1. Preço do recebimento pré-preenchido pelo front é dividido de novo pelo fator e corrompe o custo médio
- Onde: `app.js:1277` (pré-preenche `preco` com `i.preco_unit` do pedido) contra `R/compras.py:452` (`converter_preco` divide `preco` pelo `fator_compra`). Agravante: `app.js:1273` usa o rótulo "Preço por unidade de compra", mas o valor vem por unidade do item.
- Cenário (teste E): item em kg com saco de 25 kg, pedido de 50 kg a R$ 100,00 por saco, o pedido guarda `preco_unit = 4` (R$/kg). O operador escolhe o pedido no Recebimento, o front preenche `preco = 4`. A API calcula 4 / 25 = 0,16, recusa por "preço diferente do pedido"; o operador digita um motivo qualquer e a entrada passa. Custo médio gravado: **R$ 0,16/kg em vez de R$ 4,00**. O CMV e o custo da ficha ficam 25 vezes menores, sem alerta.
- Cenário B (teste F): fator 3, `preco_unit = 3.333333`; o front manda 6 casas e a validação `PrecoUnit` (4 casas, `schemas.py` `_PRECO4`) responde 422. O pedido com fator não divisível por 10 **não pode ser recebido pela tela** sem digitar o preço à mão.
- Correção: o front deve pré-preencher `preco_unit * fator` (preço por embalagem), arredondado a 2 casas; ou a API deve aceitar `preco_unitario_item` explícito. Melhor ainda: o recebimento aceitar quantidade e preço na unidade de compra e converter só no servidor, com os dois rótulos claros. Além disso, bloquear (ou exigir confirmação de gerente) quando o preço unitário novo divergir mais de, por exemplo, 50% do último custo médio.

### A2. Saída manual (perda, consumo, transferência) passa do saldo real depois de uma baixa automática negativa
- Onde: `S/estoque.py:131-152` (`saida`) e `S/estoque.py:103-110` (`entrada`).
- Cenário (teste A): ficha cadastrada e estoque ainda não lançado (situação normal no início). Duas meias saem, saldo -200 em linha sem lote. Chega uma compra de 300 (lote positivo 300). O saldo real é 100, mas `lotes_com_saldo` enxerga 300 e o -200 sem lote nunca é compensado. Uma **perda manual de 300 é aceita** (201) e o saldo vai a -200. O mesmo vale para transferência e consumo interno. A trava "Saldo insuficiente" só olha lotes + saldo sem lote positivo, nunca `saldo_item`.
- Efeito colateral: a soma por lote nunca fecha com o saldo do item, e o PEPS por lote fica inflado para sempre.
- Correção: em `saida` com `permitir_negativo=False`, recusar quando `qtd > saldo_item(local)`; na `entrada`, se houver saldo sem lote negativo no local, gerar um movimento de compensação sem lote (+) e o resto no lote, ou lançar a entrada já abatendo o negativo do lote NULL.

### A3. Aprovação por segunda pessoa tem dois furos
- Onde: `R/compras.py:306-308` (`auto = limite is None or total <= limite`) e `R/compras.py:382-404` (`criar_pedido`).
- Cenário 1 (teste H): o parâmetro `compra_valor_aprovacao` nasce `None` (`parametros.py:35`). Enquanto ninguém configura, **uma lista de R$ 5.000.000,00 foi aprovada pelo próprio comprador**. Falha aberta: o padrão seguro seria exigir aprovação sempre.
- Cenário 2 (teste H): o pedido digitado direto (`POST /compras/pedidos`) não consulta o limite nem exige segunda pessoa. Gerente emite sozinho um pedido de R$ 5.000,00 com limite de R$ 100,00. O comentário do código admite ("todos os compradores têm, por ora"), mas o documento (J8e) pede aprovação acima do limite.
- Cenário 3: fracionar a compra em várias listas abaixo do limite não é detectado (o limite é por lista).
- Correção: limite ausente = tudo exige segunda pessoa; pedido direto acima do limite nasce "aguardando aprovação" (nova situação) e só vira "emitido" na aprovação por outro usuário; somar as listas e pedidos do mesmo fornecedor no dia para o teste do limite.

### A4. Inventário: o "esperado" e a diferença são congelados na conferência, não na contagem
- Onde: `R/estoque.py:330-332` (`conferir`) e `R/estoque.py:356-363` (`fechar`).
- Cenário (teste I2): operador conta 100 g às 10h (certo). Às 11h acontece uma perda legítima de 40 g. O gerente confere às 12h: esperado 60, **diferença +40**. No fechamento o ajuste soma 40 g e o saldo volta a 100, apagando a perda registrada (saldo errado por 40). Em dia de movimento, toda contagem demorada gera diferenças falsas, que depois são justificadas com motivo inventado. O inverso também vale: diferença real escondida pelas vendas.
- Correção: gravar `esperado` (saldo no instante) por linha **no momento em que o `contado` é salvo** (`contar`), calcular a diferença ali, e no fechamento gerar o ajuste como delta (contado menos esperado do instante) sobre o saldo corrente. Alternativa: bloquear baixas durante a contagem de itens críticos (não recomendado).

### A5. Recebimento bloqueado quando duas entregas do mesmo item no mesmo dia têm validades diferentes
- Onde: `S/estoque.py:92-96` (código de lote padrão `L%Y%m%d`, e 409 "lote já existe com outra validade").
- Cenário (teste B): duas notas do mesmo insumo no dia, sem código de lote digitado, validades diferentes: a segunda dá 409 e o produto que chegou não pode ser lançado. O operador contorna digitando código qualquer, mas o erro é no meio do processamento da nota (`HTTPException` depois do INSERT de `recebimento`, desfeito só pelo rollback do `get_db`).
- Contraparte pior (teste C, severidade média, ver M2): se a primeira entrada não tinha validade, a segunda **atribui validade ao lote inteiro** (10 un recebidas, todas passam a vencer em 3 dias).
- Correção: código padrão deve incluir a validade ou o id do recebimento (`L{data}-R{recebimento_id}`); nunca reaproveitar lote automaticamente com validade diferente; nunca preencher a validade de um lote que já teve saldo.

---

## MÉDIA

### M1. Baixa automática perdida por timeout de trava, deadlock ou erro, e nunca reexecutada
- Onde: `S/estoque.py:231-233` (`except Exception` grava `erro_baixa`) com `api/database.py` (`lock_timeout` de 10 s, `DB_LOCK_TIMEOUT`).
- Cenário (teste O): outra transação segura a trava do item por mais de 10 s (recebimento grande, inventário, fechamento). A tablet da produção espera 10 s, a pizza acaba, a pendência `erro_baixa` é gravada e o **estoque nunca baixa**. A pendência aparece na aba Alertas, mas não há botão "refazer baixa". A produção segue (bom), o estoque diverge (ruim).
- Deadlock possível: `_gravar_baixa` ordena os itens por id **dentro de cada chamada**, mas a trava é de transação. `cancelar_pizzas` (`producao.py:94-102`) chama várias baixas na mesma transação: pizza A trava {10,20}, pizza B precisa de {5,10}. Duas transações de cancelamento com ordem cruzada travam uma na outra; a vítima vira `erro_baixa`.
- Correção: (1) rotina "refazer baixa" que reprocessa pendências `erro_baixa` (a `baixa_origem` já garante a idempotência, pois o INSERT é desfeito junto); (2) em `cancelar_pizzas` e `baixar_itens_do_pedido`, juntar o consumo de todas as pizzas e travar a união de itens em ordem crescente antes de qualquer `saida`; (3) trava com `pg_advisory_xact_lock` curta e retentativa antes de desistir.

### M2. Validade retroativa em lote existente
- Onde: `S/estoque.py:98-99`. Teste C: lote do dia sem validade recebe a validade da entrada seguinte, e a comparação do trigger `lote_nao_apaga` permite. O comentário da migração diz "validade corrigida enquanto o lote não teve saída (regra no serviço)", mas o serviço **não verifica saída alguma**.
- Correção: só atualizar validade se o lote não teve saída e se o saldo atual do lote for zero; senão criar outro lote.

### M3. Preço do pedido gerado da lista é derivado do valor arredondado, e o recebimento exato exige "motivo da diferença"
- Onde: `R/compras.py:270` (`x["v"] / x["q"]` com `v` já arredondado a centavos) contra `R/compras.py:459` (compara `unit != preco_unit` exato).
- Cenário (teste D): fator 3, 7 kg a R$ 10,00 o saco. Preço real 3,333333, valor 23,33, o pedido grava 3,332857. Recebimento fiel ao pedido dá 400 "informe o motivo". Em toda compra com fator que não divide 10 o controle de diferença vira ruído e os operadores passam a digitar "ok".
- Correção: gravar em `pedido_compra_item` o `preco_unit` da escolha (média ponderada dos preços originais, não de `valor/q`), e comparar com tolerância de 0,5 centavo por linha, não igualdade de 6 casas.

### M4. Lista nasce com quantidade sugerida substituída, sem motivo
- Onde: `R/compras.py:113-117`. Teste G: item sugerido pelo sistema (mínimo, 100 sugeridos); o operador manda o mesmo item em `itens` com quantidade 1; a lista nasce com `origem = minimo`, `sugerida = 100`, `quantidade = 1`, `motivo = NULL`. Fura a regra "mudar ou remover o que o sistema sugeriu exige motivo" (documento 3.2) sem passar por `ajustar`.
- Correção: se o item já vem das sugestões e a quantidade difere, exigir `motivo` no corpo (`ItemQtd.motivo`) ou ignorar a quantidade e deixar `ajustar` fazer o trabalho.

### M5. Estoque sem custo conhecido dilui o custo médio da primeira compra
- Onde: `S/estoque.py:105-109`, `R/estoque.py:360`. Teste K: o inventário gera ajuste positivo de 100 sem custo (item nunca teve custo); depois chega uma compra de 100 a R$ 10: custo médio gravado **R$ 5,00**. Vale também para qualquer entrada sem custo seguida de compra.
- Correção: se não houver custo anterior, o custo médio é o da entrada e o ajuste sem custo não entra na média (peso zero), ou exigir custo estimado no ajuste positivo de item sem histórico. `saldo_apos` também fica incoerente quando o saldo era negativo (`saldo_antes` usa `max(...,0)` mas registra `saldo_antes + qtd`).

### M6. Nota duplicada: proteção fraca
- Onde: `migrations_pg/008_compras.sql` índice `uq_recebimento_nota` e `R/compras.py:480`. Teste L: "NF1" e "nf1" e "0NF1" passam como notas diferentes; sem número de nota (campo opcional, `schemas.py` `RecebimentoIn.numero_nota`) o **duplo clique** lança a entrada duas vezes (a interface não desabilita o botão, `app.js:1279`).
- Correção: normalizar (maiúsculas, tirar espaços e zeros à esquerda) antes de comparar; exigir número de nota exceto em "compra sem nota" confirmada; chave de idempotência no recebimento (token enviado pelo front) e botão desabilitado durante o envio.

### M7. Item com lote entra sem validade
- Onde: `S/estoque.py:91-102` e `RecebItemIn.validade` opcional. Teste M. A decisão J4 pede lote e validade em todos os insumos de pizza e calzone. Lote sem validade é consumido por último (`NULLS LAST`) e nunca aparece nos alertas.
- Correção: exigir `validade` quando `controla_lote` e a classe for insumo/preparo, com opção explícita "não perecível" por item.

### M8. Cancelar pedido não devolve a baixa das bebidas
- Onde: `R/vendas.py:198-210` (baixa ao acabar) e `cancelar` (sem estorno de estoque). Teste N: pedido de 3 latas acabado e depois cancelado (permitido até "despachado"): as latas ficam no freezer, mas o saldo continua 17. Pizza cancelada depois de acabada corretamente permanece baixada (foi desperdício).
- Correção: no cancelamento de pedido já baixado (`baixa_origem` presente) lançar entrada de estorno `ajuste` com a origem; para pizza manter a regra atual.

### M9. Estoque inicial pode ser lançado a qualquer hora, quantas vezes quiser, com custo livre
- Onde: `R/estoque.py:192-207`. Quem tem `estoque.gerir` (gerente, subgerente) cria saldo e **altera o custo médio** de qualquer item com "Estoque inicial" repetido, sem segunda pessoa; combinado com `perda` (só `estoque.mover`) esconde desvio.
- Correção: permitir `entrada_inicial` só em item sem nenhum movimento (ou até uma data de corte nos parâmetros), exigir aprovação do proprietário depois disso, e alerta de variação de custo.

### M10. Inventário mensal: guarda de "itens não contados" é desligada pela própria tela
- Onde: `app.js:1166` envia sempre `confirmar_nao_contados: true`. A tela nunca mostra ao gerente que há itens sem contar; fecha o mensal com itens esquecidos sem aviso.
- Correção: o front deve mostrar a contagem de não contados e só enviar `true` após confirmação explícita.

### M11. Contagem "cega" não é cega
- Onde: `R/estoque.py:94-138` expõe `saldo` a quem tem `estoque.ver`, e quem conta tem `estoque.mover`, que implica ver. Basta abrir a aba Saldos para saber o esperado de cada item e digitar o esperado como contado. Fraude de contagem pelo próprio contador.
- Correção: durante inventário aberto, esconder `saldo` (ou perfil de contador sem `estoque.ver`) e registrar no log quem consultou saldo em inventário aberto.

### M12. Ficha de preparo sem rendimento
- Onde: `S/estoque.py:165-176` (`_expandir`). Teste P: preparo com ficha "10 g de Z", pizza usa 50 g do preparo com 10% de perda, o consumo de Z foi **550 g** (10 × 55). A ficha do preparo é tratada como "por 1 unidade do preparo", sem campo de rendimento do lote (uma ficha de molho para 10 kg gera 10 kg de ingrediente por kg de molho consumido).
- Correção: confirmar com Marlon o significado da ficha do preparo; se for por lote, acrescentar `rendimento` na ficha e usar `qtd / rendimento`. Cuidado também com o ciclo A→B→A: o laço para em `nivel < 5` e consome o próprio preparo sem avisar (deveria virar `erro_baixa`).

### M13. Recebimento com sangria: vínculo fraco
- Onde: `R/compras.py:472-478`. Verifica só tipo `sangria` e valor igual. Não verifica data (qualquer sangria antiga serve), nem `vira_despesa` (o mesmo dinheiro conta como despesa e como compra, duplicando no CMV), nem o motivo (sangria de depósito servindo de compra). Igualdade de centavos estrita: arredondar linha a linha (valor = qtd × preço unitário arredondado por linha) pode diferir 1 centavo do valor sacado, impedindo o vínculo legítimo.
- Correção: exigir mesma data (ou janela), `vira_despesa = false` ou marcar a despesa como paga por compra, aceitar diferença de centavos justificada, mostrar a sangria na tela (hoje o operador digita o número do movimento à mão, `app.js:1270`).

---

## BAIXA

- **B1. Sugestão de validade soma só um lote.** `S/compras.py:286-289` agrupa por (item, lote) mas o dicionário guarda só o último lote. Teste J: lotes 10 e 7 perto de vencer, sugestão sai 7 (saldo 17). E sugerir comprar mais de um item que está vencendo só faz sentido se o consumo futuro cobrir; revisar a regra.
- **B2. Sugestões ignoram o que já foi pedido.** `S/compras.py:296-298` não desconta pedidos emitidos/parciais, e duas listas abertas repetem os mesmos itens (nenhuma trava). Risco de compra em dobro.
- **B3. `saldo_apos` do custo_item** usa o saldo positivo (ver M5). Informação de apoio incorreta.
- **B4. Frete e desconto não entram no custo** (`R/compras.py:464-466`). O custo médio fica abaixo do real; ratear frete/desconto proporcionalmente ao valor dos itens, ou decidir e documentar.
- **B5. Pedido parcial não pode ser encerrado.** `cancelar_pedido` só aceita "emitido" (`R/compras.py:412`) e o gatilho do pedido não deixa fechar o saldo pendente; fica "parcial" para sempre. Falta "encerrar com o que chegou".
- **B6. Fornecedor do pedido sobrescreve em silêncio.** `R/compras.py:439`: se o corpo traz `fornecedor_id` diferente do pedido, ele é ignorado sem erro.
- **B7. Quem montou a lista.** `R/compras.py:333` só compara `definida_por`. `criado_por` (quem montou de fato) pode aprovar. Comparar com os dois.
- **B8. Truncamento de lote.** `S/estoque.py:92` corta o código em 40 caracteres, enquanto o esquema aceita 120; dois códigos longos podem colidir e misturar lotes.
- **B9. Arredondamento por pizza.** `S/estoque.py:84` e `q4` na `saida`: soma por item por pizza arredondada a 4 casas, em kg/l com perda_pct pequena (por exemplo 3 g de orégano) acumula erro sistemático. Preferir acumular em mais casas e arredondar no fim do dia, ou usar g.
- **B10. Locais.** `S/estoque.py:48` devolve local inativo quando não há ativo (entrada num local inativado). `alterar_local` (`R/estoque.py:67-71`) não trava contra movimento simultâneo.
- **B11. Itens "sem estoque" ruído.** `R/estoque.py:84-91`: item que nunca teve saldo (ex.: os cerca de 100 materiais de limpeza) aparece como "sem estoque" e entra em `atencao`; mínimo 0 faz o item entrar na sugestão com saldo 0.
- **B12. Banco.** (a) Os gatilhos de `lista_compra_filhos` só cobrem UPDATE e DELETE: INSERT de item, cotação ou escolha em lista já aprovada passa se o serviço não barrar (hoje barra). (b) Tabelas sem gatilho de TRUNCATE: `inventario_linha`, `lote_estoque` (protegido só por FK), `lista_compra*`, `pedido_compra`, `fornecedor`. (c) `movimento_estoque.lote_id` não tem FK composta com item (um lote de outro item é aceito por SQL direto). (d) Gatilho do pedido permite voltar de "parcial" a "emitido".

---

## Interface (frontend) e segurança

- Sem XSS: `h()` (`app.js:7-16`) só usa `createElement`, `setAttribute` e `createTextNode`; nenhum `innerHTML`. Textos vindos da API (nomes, motivos, lote, fornecedor) são sempre nó de texto. `onclick` por propriedade, sem atributo inline: compatível com o CSP (`script-src 'self'`, `api/main.py`). Nenhuma violação encontrada nas abas abaEstoque e abaCompras.
- `app.js:1269`: `new Date().toISOString().slice(0,10)` usa UTC. Depois das 21h (Brasília) a "Data da nota" padrão já é o dia seguinte, e a nota fica no dia errado.
- `app.js:1246` e `1248`: a tela não permite dividir um item entre fornecedores (a API permite). O texto da tela admite ("use a API").
- `app.js:1279-1285`: botão "Registrar recebimento" sem trava de duplo envio (ver M6).
- `R/compras.py:211-217` (`por-fornecedor`) não separa por fornecedor: devolve um texto único com todos os itens, ao contrário do que o nome diz.
- Permissões: `estoque.*` e `compras.*` estão corretas e negam por padrão para atendente/produção. Todas as permissões de custo e estoque ficam nos quatro perfis de gerência (J7). Não há segregação entre quem lança perda, estoque inicial e fecha inventário (`estoque.gerir`). Apagar histórico: gatilhos de só inserção cobrem `movimento_estoque`, `custo_item`, `preco_compra`, `recebimento`, `baixa_origem`; correto.
- Não há limite de valor nem aprovação para `perda` e `consumo_interno` (apenas motivo livre de 200 caracteres). Recomendo limiar parametrizado acima do qual um segundo usuário confirma.

---

## O que foi verificado e está correto

- Grande de um sabor consome o dobro, grande com dois sabores consome cada sabor uma vez, base da ficha por tamanho uma vez (teste P: 100 g e 60 g conferem); perda_pct, adicional por tamanho, preparo com ficha própria expandido.
- Perda de pizza só consome a montagem; idempotência por `baixa_origem` (acabada duas vezes, retrocesso e acabada, perdida depois de acabada).
- Pizza sem ficha vira pendência sem travar a produção; falha da baixa não aborta o movimento da pizza.
- Saldo vem da soma dos movimentos; PEPS por validade, depois entrada, sem validade por último; transferência não cria nem perde saldo.
- Custo médio móvel: sem divisão por zero (`qtd > 0` e `saldo_antes >= 0`); saldo negativo tratado como zero na média.
- Soma das escolhas por item igual à quantidade da lista; divisão do item entre fornecedores; lista só avança; aprovação por outro usuário quando há limite; vínculo único da sangria (`UNIQUE movimento_caixa_id`); nota duplicada exata barrada; trava `FOR UPDATE` no pedido e ordem fixa de itens no recebimento.
- Inventário só avança, contagem não muda depois da conferência, linhas e inventário não se apagam; movimentos e custos só com inserção.

## Ordem sugerida de correção

1. A1 (custo 25 vezes errado) e A2 (saldo e PEPS).
2. A3 e M9 (controles de fraude), A4 (inventário), A5/M2 (lote e validade).
3. M1 (refazer baixa e travas), M3, M4, M5, M6, M7, M8, M10 a M13.
4. Baixas e interface.
