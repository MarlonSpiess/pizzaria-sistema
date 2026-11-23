# Relatório do revisor cego (ub-mode)

> Nota (23/11/2026): os reprodutores C1 e C4 viraram `tests/test_qa_cego_ub2.py`, o C3 virou `tests_unidade/test_depreciacao.py` e o C5 é o mesmo N3 do QA não cego. Respostas em `qa_resposta_ub_mode2.md`.

Escopo: sistema (API FastAPI, migrações 001 a 021, frontend app.js) contra as regras em planejamento. Nenhum outro material foi lido.

Testes que reproduzem os defeitos: `tests/test_qa_cego_ub2.py`. Rodar isolado, num banco recém-criado (os cenários de caixa dependem da ordem do arquivo):

```
cd sistema
TEST_DB_NAME=cego_teste /home/user/venv/bin/python -m pytest -q tests/test_qa_cego_ub2.py
```

Resultado: 8 testes, 8 falham, cada um pelo motivo descrito. A suíte original (324 testes, sem este arquivo) passa inteira.

## Achados confirmados por teste

### C1. Venda depois da meia-noite entra em dois caixas (alta, DEFEITO confirmado)
- Arquivo: `api/services/caixa.py:17-20` (`faixa`), combinado com as datas de calendário gravadas em `api/routers/vendas.py:192` (`dia = hoje()`), `api/routers/caixa.py:268` (movimento), `api/routers/caixa.py:437` (acerto) e `api/routers/vendas.py:361` (estorno).
- Defeito: o caixa não guarda quais lançamentos são seus; ele os deduz por faixa de datas, da sua data até a data do próximo caixa. O próprio sistema admite caixa que atravessa a meia-noite (docstring de `services/caixa.py`). Uma venda às 00h30 recebe a data de hoje, entra na contagem do caixa de ontem (correto) e, quando o caixa de hoje abre, a faixa do caixa de ontem encolhe para [ontem, hoje) e a do caixa de hoje começa em hoje: a mesma venda entra no esperado de hoje. Resultado: falta fictícia no caixa de hoje igual às vendas da madrugada, e o relatório de ontem (`GET /caixa/{data}/relatorio`) passa a mostrar valores diferentes dos que foram contados. Vale também para sangrias, suprimentos, estornos e acertos feitos depois da meia-noite. No próprio teste, um acerto do caixa de anteontem (feito "hoje") apareceu no esperado do caixa de ontem, outra manifestação da mesma causa.
- Reproduzir: `test_c1_venda_depois_da_meia_noite_entra_em_dois_caixas`.
- Correção sugerida (causa raiz): gravar `caixa_id` em pedido/pagamento, estorno, movimento_caixa e acerto_entregador no momento do lançamento (o caixa aberto, com FK e NOT NULL quando houver caixa) e calcular esperado e relatório por `caixa_id`, não por data. Alternativa menor: usar como "data operacional" a data do caixa aberto, nunca a do relógio.

### C2. Pizza perdida em pedido já acabado: refação recusada e pedido entregue incompleto (média, DEFEITO confirmado)
- Arquivo: `api/routers/producao.py:250` (`perder` aceita pedido `acabado`), `api/routers/producao.py:274` (`refazer` exige `recebido` ou `em producao`), `api/routers/vendas.py:292-297` (`mudar_situacao` só confere pizzas pendentes na ida para `acabado`).
- Defeito: o acabamento registra a perda de uma pizza de pedido acabado (caiu ao embalar), a refação é recusada e o balcão marca o pedido como retirado com uma pizza a menos. O invariante "pedido acabado = nenhuma pizza pendente" é quebrado e a pizza perdida nem aparece em `/producao/perdidas` (que filtra pedidos em produção).
- Reproduzir: `test_c2_pizza_perdida_em_pedido_acabado_sai_incompleta`.
- Correção sugerida: ou recusar `perder` em pedido acabado, ou permitir `refazer` nesse caso e voltar o pedido para `em producao` (o gatilho `pedido_so_situacao` hoje só deixa avançar; seria preciso permitir esse retorno), e conferir pizzas pendentes também na ida para `despachado ou retirado`.

### C3. Depreciação total passa do valor depreciável (baixa, DEFEITO confirmado)
- Arquivo: `api/services/imobilizado.py:32-38`.
- Defeito: a parcela mensal é `base / n` arredondada (meio para o par). Quando arredonda para cima, n-1 parcelas já passam da base; a última fica negativa e é descartada (`if v > 0`). Ex.: bem de R$ 13,00 em 120 meses deprecia R$ 13,09; R$ 100,00 em 600 meses deprecia R$ 101,83. O saldo contábil fica abaixo do residual.
- Reproduzir: `test_c3_depreciacao_total_passa_do_valor_depreciavel` (função pura).
- Correção sugerida: parcela arredondada para baixo (`ROUND_DOWN`) com a última absorvendo o resto, ou cada parcela = `round(base*(i+1)/n) - round(base*i/n)`, que soma exatamente a base. Teste de propriedade: soma das parcelas == base para vários (base, n).

### C4. Diária do entregador paga de novo no mesmo caixa depois da meia-noite (média, DEFEITO confirmado; regra "diária por dia" a confirmar)
- Arquivo: `api/routers/caixa.py:425`.
- Defeito: a diária "uma vez por entregador por dia" é decidida pela data do relógio (`quando.date()`), não pelo caixa/turno. Turno que atravessa a meia-noite com acerto parcial antes e acerto final depois paga duas diárias. Mesma causa raiz do C1.
- Reproduzir: `test_c4_diaria_do_entregador_paga_de_novo_no_mesmo_caixa_depois_da_meia_noite`.
- Correção sugerida: verificar a diária por `caixa_id` (ou pela data operacional do caixa) e criar índice único parcial que impeça duas diárias > 0 do mesmo entregador no mesmo caixa. Confirmar com o dono que "dia" significa turno/caixa (decisão F2).

### C5. Dois títulos simultâneos furam o limite de aprovação do dia (média, DEFEITO confirmado)
- Arquivo: `api/routers/contas.py:195-201`.
- Defeito: o acumulado do dia de quem lança é lido com um SELECT e o título é gravado depois, sem trava. Dois lançamentos ao mesmo tempo leem o mesmo acumulado e saem ambos aprovados (R$ 160,00 aprovados com limite de R$ 100,00). A sangria tem a trava equivalente (`pg_advisory_xact_lock(7201, ...)`); contas não.
- Reproduzir: `test_c5_dois_titulos_simultaneos_furam_o_limite_de_aprovacao_do_dia` (trava externa só para tornar a corrida determinística).
- Correção sugerida: `pg_advisory_xact_lock` por (loja, usuário) antes de somar, na mesma transação da gravação.

### C6. Cancelar pedido acabado não devolve a bebida ao estoque (média, DEFEITO confirmado no comportamento; política de devolução a confirmar)
- Arquivo: `api/routers/vendas.py:343-372` (`cancelar`), `api/services/estoque.py:246` (`baixar_itens_do_pedido`), `api/services/producao.py:92-103`.
- Defeito: a bebida sai como `saida_venda` quando o pedido fica acabado; se o pedido é cancelado antes de sair, nada é estornado nem reclassificado. O saldo fica abaixo do físico e o CMV teórico conta venda que não houve. O mesmo ocorre com pizza acabada de pedido cancelado: vira perda na Produção, mas o movimento de estoque continua `saida_venda`, não `perda`.
- Reproduzir: `test_c6_cancelar_pedido_acabado_nao_devolve_bebida_ao_estoque`.
- Correção sugerida: no cancelamento, lançar entrada de estorno da baixa de bebidas e acompanhamentos (origem `pedido`) e reclassificar como perda o consumo das pizzas já feitas.

### C7. Fluxo de caixa revela o valor da folha a quem não vê salários (média, DEFEITO de autorização confirmado)
- Arquivo: `api/routers/contas.py:359-363` (projeção) e `:370-372` (realizado 30 dias).
- Defeito: a regra é folha só para administrador e proprietário, e o código esconde títulos de origem `folha` em `/contas/titulos` (linha 174) e na conciliação (linha 323). Mas `/contas/fluxo` (contas.ver, que gerente e subgerente têm) soma o título da folha nas saídas do dia do vencimento; no teste o gerente lê R$ 4.321,09 exatos. O realizado dos últimos 30 dias também inclui a baixa da folha.
- Reproduzir: `test_c7_fluxo_de_caixa_revela_o_valor_da_folha_a_quem_nao_ve_salarios`.
- Correção sugerida: para quem não tem `rh.salarios`, agrupar a folha com outras saídas sem revelar a linha, ou mostrar apenas o saldo projetado sem detalhar entradas e saídas do dia. Decidir com o dono o grau de agregação aceitável.

### C8. Ingrediente da ficha base (ou de borda) em falta não fecha venda nenhuma (média, DEFEITO confirmado)
- Arquivo: `api/services/ingredientes.py:9-19` (`_USO` parte só de fichas com `produto_id`).
- Defeito: fichas base por tamanho (`produto_id`, `adicional_id` e `item_id` nulos) e fichas de adicional não entram no cálculo de "quem usa o ingrediente". Marcar em falta o molho da Grande responde "nenhum sabor afetado" e o balcão vende a pizza normalmente. O canal também não recebe a pausa.
- Reproduzir: `test_c8_ingrediente_da_ficha_base_em_falta_nao_fecha_venda_nenhuma`.
- Correção sugerida: incluir a ficha base do tamanho (fecha todos os sabores daquele tamanho) e as fichas de adicional (fecha o adicional/borda) no cálculo; refletir isso em `_sabor_fechado` e em `pode_aceitar_sozinho`.

## Achados por leitura (não testados) e decisões a confirmar

### C9. Pedido agendado não existe (baixa, DECISÃO a confirmar)
- Regra 02_Producao 5.4: "Pedido agendado para horário futuro entra na fila só perto da hora". Não há campo nem lógica de agendamento (nenhuma ocorrência de "agendad" no código ou nas migrações). Confirmar se saiu do escopo.

### C10. Contagem cega é contornável pelo próprio operador (baixa, DECISÃO a confirmar)
- `api/routers/caixa.py:61-83` esconde o esperado antes da contagem, mas o atendente (que conta) lê `/pedidos?data=` e `/pedidos/{id}` com pagamentos e troco, e `/caixa/entregas` com totais; somando, obtém o esperado em dinheiro. Se a contagem cega for requisito forte (I5), separar quem conta de quem vê os pagamentos detalhados durante a contagem.

### C11. Gravações sem chave de idempotência (baixa, DECISÃO)
- `POST /caixa/movimentos`, `POST /contas/titulos`, `POST /producao/massa/lote` e `/perda` não têm chave: um reenvio (duplo clique, rede lenta) grava duas vezes. O pedido de venda tem `chave`; sangria em dobro gera diferença de caixa. Sugestão: o mesmo padrão `chave` com índice único parcial.

### C12. Taxa de entrega reduzida pela gerência não conta no limite de desconto (baixa, DECISÃO)
- `api/routers/vendas.py:47-49`: para atendente, taxa abaixo do padrão exige autorização; para gerente e subgerente, zerar a taxa não passa pelo limite percentual dele. Confirmar se é intencional.

### C13. Guardas `except Exception` que engolem erros (baixa, fazer certo)
- `api/services/estoque.py:241` e `:259`, `api/services/canais.py:81` e `:101`. A intenção (não travar a produção) é documentada, mas o `except Exception` também captura erros de programação (KeyError, TypeError) e os transforma em pendência silenciosa. Sugestão: capturar só `psycopg.Error` e `HTTPException` esperadas, e deixar o resto falhar nos testes.

### C14. Frete da nota fora do custo médio (baixa, DECISÃO)
- `api/routers/compras.py:446-466`: frete e desconto da nota entram no título a pagar mas não no custo unitário que alimenta o custo médio e o CMV teórico. Confirmar a política de custeio.

### C15. Folha mensal sem proporcionalidade (baixa, DECISÃO)
- `api/routers/rh.py:454-455`: funcionário admitido ou desligado no meio do mês entra com o salário cheio na prévia gerencial.

## Complexidade sem cobertura suficiente (CRAP > 10)

Medido com `tools/crapper.py` sobre a suíte inteira. Os piores:

| CRAP | cc | Cobertura | Função |
|---|---|---|---|
| 63,6 | 23 | 57,5% | `api/routers/bi.py:62 _alertas` |
| 27,2 | 23 | 80,0% | `api/services/estoque.py:112 saida` |
| 23,4 | 23 | 91,2% | `api/routers/compras.py:435 receber` |
| 23,2 | 20 | 80,0% | `api/routers/vendas.py:170 criar` |
| 21,0 | 21 | 95,8% | `api/routers/vendas.py:52 _resolver_avulsas` |
| 19,2 | 18 | 84,4% | `api/routers/contas.py:187 criar_titulo` (onde está o C5) |
| 15,6 | 13 | 75,0% | `api/services/estoque.py:220 baixar_pizza` |

`criar` (pedido) mistura idempotência, avulsas, preço, autorização, caixa, numeração, produção e auditoria numa função de complexidade 20; vale extrair o cálculo e as validações para funções puras testadas à parte.

## O que foi conferido e está correto

- Toda rota exige permissão no servidor; acabamento não recebe valores (`/caixa/despacho`, `/producao/*`); despacho exige caixa aberto; subgerente não aprova diferença de caixa.
- Dinheiro em `Decimal`/`NUMERIC`, entrada validada por regex, meio a meio arredondado para cima por metade, constraints de total no banco.
- SQL parametrizado; os poucos f-strings montam nomes de coluna vindos do schema.
- app.js monta o DOM só por `createElement`/`textContent`; não há `innerHTML` com dado do usuário; CSP restritiva.
- Numeração do dia por upsert atômico; avulsa vendida protegida por PK em `pizza_avulsa_destino`; sangria sem autorização serializada.

## Recomendação

Corrigir primeiro o C1, pela causa raiz: ligar cada lançamento financeiro ao `caixa_id` em vez de deduzir o caixa pela data do relógio. Isso elimina C1 e C4 juntos e torna os relatórios de caixa imutáveis depois do fechamento. Em seguida, C7 (vazamento de folha) e C5 (trava no limite de aprovação), que são correções pequenas. C2, C6 e C8 pedem uma decisão rápida do dono sobre o comportamento esperado antes do código. Manter os 8 testes de `tests/test_qa_cego_ub2.py` como testes de regressão (ajustando os dois cenários de caixa para não dependerem da ordem quando forem corrigidos).
