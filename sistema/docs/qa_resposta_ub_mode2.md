# Respostas à segunda rodada ub-mode (23/11/2026)

Base: código do PR #4 (nenhum PR mesclado em 23/11/2026). Dois revisores com o método ub-mode: o cego (`qa_cego_ub_mode2.md`) viu só o código e as regras de `planejamento/`; o não cego (`qa_nao_cego_ub_mode2.md`) leu os QA anteriores e conferiu cada correção.

Suíte completa depois das correções e das 5 decisões: 342 passed e 1 falha (`test_varredor::test_entrega_de_canal_so_sai_com_entregador`, que forçava pedido acabado com pizza pendente, estado que agora o despacho recusa). O teste passou a acabar as pizzas antes; o arquivo voltou a passar (7 passed).

## Corrigidos

| Achado | O que foi feito | Teste que pega |
|---|---|---|
| N1 (alta) | Regra única `_ve_folha` em Contas. Baixa, aprovação, cancelamento e conciliação respondem 404 para o título ou a baixa da folha a quem não tem `rh.salarios` (igual a "não existe", sem revelar valor) | `test_qa_ub_mode2.py::test_N1_*`, `test_N1b_*` |
| N2 (alta) | Regra única `_mexe_em_login_da_gerencia` no vínculo e no desligamento. Desligar quem tem login da gerência sem `usuarios.gerir` é recusado (403). Decisão de Marlon em 23/11/2026: recusar | `test_N2_*` |
| N3 e C5 (média) | Trava consultiva por usuário (`pg_advisory_xact_lock(7202, usuario)`) antes de somar o acumulado do dia do título a pagar | `test_N3_*` |
| N4 | `preco_pizza` tira o total de `preco_meio_a_meio`; `metade_para_cima` só descreve as metades | `tests_unidade/test_preco.py` |
| N5 | `statement_timeout` (57014) vira 504 sem Retry-After, com a pilha no log; 503 com Retry-After fica só para trava, deadlock e serialização | `tests_unidade/test_banco_demorado.py` |
| N6 | `tools/crapper.py` conta cada função uma vez. Nova medida: 48 de 681 funções com CRAP 10 ou mais (antes 63 de 855, inflado) | saída do crapper |
| N8 | `404 ou 409` virou `409`; 4 variáveis mortas removidas dos testes | pyflakes |
| C1 (alta) | `services/caixa.data_do_lancamento`: venda, estorno, lista de pedidos do dia, sangria, suprimento e acerto gravam a data do caixa em uso (que segue aberto depois da meia-noite), não a do relógio. A venda das 00h30 fica só no caixa de ontem | `test_qa_cego_ub2.py::test_c1_*` |
| C4 (média) | A diária do entregador vale uma vez por caixa (faixa do caixa), não por data do relógio | `test_qa_cego_ub2.py::test_c4_*` |
| C3 (baixa) | Parcela mensal truncada ao centavo e a última absorve o resto: a soma nunca passa do valor depreciável | `tests_unidade/test_depreciacao.py` |
| C7 e resto do A1 (média) | Decisão de Marlon em 23/11/2026: a folha fica somada às outras saídas do dia, sem linha nem descrição própria; o saldo projetado do gerente continua verdadeiro. O fluxo já agrupava por dia, então não mudou código; o teste fixa a regra. Num dia em que só a folha vence, o total ainda a revela (risco aceito) | `test_qa_cego_ub2.py::test_c7_*` |
| C8 (média) | Decisão de Marlon em 23/11/2026: ingrediente da ficha base em falta fecha toda pizza daquele tamanho; ingrediente de adicional ou borda fecha só aquele adicional naquele tamanho. Balcão recusa (409), a tela de vendas fechadas mostra o que fechou e o aceite automático do canal recusa enquanto houver base ou borda fechada (o mapa do canal liga só o produto, sem tamanho). A pausa no canal continua por produto | `test_qa_cego_ub2.py::test_c8_*` |
| C2 (= A9, média) | Decisão de Marlon em 23/11/2026: perda ou refação em pedido acabado devolve o pedido para "em produção" (migração 024, antes numerada 022, libera só esse retorno no gatilho); o balcão não entrega com pizza pendente. O teste antigo `test_refacao_so_enquanto_o_pedido_esta_em_producao` fixava a regra anterior e foi reescrito | `test_qa_cego_ub2.py::test_c2_*`, `test_producao.py::test_refacao_ate_o_pedido_sair_*` |
| C6 (média) | Decisão de Marlon em 23/11/2026: no cancelamento, cada saída de venda do pedido é estornada no mesmo lote, local e custo (`estoque.estornar_baixas_do_pedido`, idempotente). Bebida e acompanhamento voltam ao estoque; o consumo das pizzas feitas sai da venda e entra como perda. O CMV teórico deixa de contar a venda que não houve | `test_qa_cego_ub2.py::test_c6_*` |
| Suíte | `tests_unidade/conftest.py` deixava a senha falsa `sem-banco` quando as duas pastas rodavam juntas (`python -m pytest`), e todos os testes com banco davam erro de senha. Agora usa o mesmo padrão de `tests/conftest.py` | suíte completa |

## Decisões de regra de negócio (para Marlon, uma a uma)

1. **C9 a C15** (por leitura): pedido agendado (C9), contagem cega contornável (C10, = A10), chave contra reenvio em sangria, título e massa (C11), gerência zera taxa de entrega fora do limite (C12), frete fora do custo médio (C14, = 2AB M13), folha sem proporcionalidade no mês (C15).

## Fica para a próxima rodada (técnico)

- C13: `except Exception` amplos em estoque e canais; trocar pelos erros esperados.
- N7 e CRAP: `bi._alertas` (63,6), `estoque.saida`, `compras.receber`, `vendas.criar`, `producao.perder`, `custos.produto`, `_mudancas_do_bem`.
- `canais.pode_aceitar_sozinho` ainda exige caixa com a data de hoje; com o C1 corrigido, depois da meia-noite o aceite automático pararia. O aceite ainda não existe no código (depende da API do Anota Ai); rever junto.
- Pendências técnicas antigas listadas no fim de `qa_nao_cego_ub_mode2.md` (A12, A15, A16, M3, M4 e outras).

## Recomendação

Mesclar os PRs na ordem #2, #3, #4 e depois este, e decidir os itens C9 a C15 quando houver tempo; nenhum deles trava a operação hoje.
