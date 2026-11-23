# Resposta aos QA da revisão ub-mode (06/11/2026)

Relatórios: [qa_cego_ub_mode.md](qa_cego_ub_mode.md) (sem ver o que foi feito) e [qa_nao_cego_ub_mode.md](qa_nao_cego_ub_mode.md) (vendo o diff). O QA não cego não achou regressão nas refatorações. Toda correção abaixo tem teste que falhava antes (tests/test_qa_ub_mode.py, tests/test_edicoes_cadastro.py, tests/test_robustez.py, tests/test_imobilizado.py e tests_unidade/).

## Corrigido

QA não cego:
- A1 preço da Grande meio a meio em Custos usava a média com arredondamento bancário: agora `preco_meio_a_meio()` é a única definição e Custos a usa (recusa também o segundo sabor igual ao primeiro).
- M1 503 com "tente de novo" depois de um commit: Retry-After só em leitura (GET e HEAD); na gravação a mensagem pede para conferir na tela antes de repetir.
- M2 log do 503 passa a registrar SQLSTATE e mensagem, em nível de erro.
- M5 PATCH do bem com valor residual nulo: 400 em vez de 500.
- B1 testes de funcionário e de imobilizado conferem o dado alterado, não só o status.
- B2 docstring corrigido. B3 `_NUMERO` com fullmatch ("5\n" recusado). B4 log em [ub_mode_revisao.md](ub_mode_revisao.md).

QA cego:
- A1 (parte) baixa do título da folha some da conciliação e da auditoria para quem não tem rh.salarios.
- A2 perda de pizza depois da montagem exige forno, acabamento ou gerência (pizzaiolo só montagem).
- A3 ligar o login de alguém da gerência a um funcionário exige usuarios.gerir (só administrador e proprietário).
- A5 transferência confere o saldo líquido do local de origem.
- A6 sangria sem autorização: trava consultiva por loja antes da soma do acumulado.
- A13 relatório de data sem caixa: 404. A14 RAISE dos gatilhos: 409 com a mensagem do gatilho.
- A18 (parte) `run()` e `EM_ANDAMENTO` removidos. A19 /health pelo pool.

## Não é defeito

- A8 (cego) subgerente sem rh.aprovar: está documentado em planejamento/modulos/08_RH.md ("o subgerente não aprova no RH") e na estrutura de menus. Mantido.

## Pendente, decisão de Marlon (recomendação entre parênteses)

- A4 entrega do balcão despachada sem entregador e sem caixa aberto: hoje a exigência vale só para canal externo, de propósito. (Recomendo exigir o entregador também no balcão, porque o dinheiro com o motoboy fica fora do esperado da gaveta; muda a rotina do atendente.)
- A1 (resto) saldo bancário e fluxo do gerente incluem o pagamento da folha. (Recomendo mostrar ao gerente o saldo sem a linha da folha só no detalhe, mantendo o saldo total, porque o saldo real é necessário para pagar contas.)
- A7 pedido de compra digitado direto não passa pela aprovação acima do limite ("todos os compradores aprovam, por ora"). (Recomendo aplicar a mesma regra da lista de compras.)
- A9 pizza perdida em pedido já acabado não pode ser refeita. (Recomendo aceitar refazer com o pedido acabado e bloquear o despacho enquanto houver pizza pendente.)
- A10 contagem cega: quem conta pode somar os pedidos do dia. (Recomendo esconder os valores dos pedidos de quem tem caixa.operar enquanto o caixa está aberto e sem contagem.)
- A11 venda num dia sem caixa cai no caixa anterior já fechado. (Recomendo ligar `venda_exige_caixa_aberto` = sim nos Parâmetros.)

## Pendente técnico (próxima rodada)

- A12 `autorizar()` e o login comitam a transação de quem chama; A15 rotas GET que gravam (canais, sincronização de contas); A16 chave de idempotência sem conferir o conteúdo; A18 restante (ZERO e _mes repetidos, `contas_svc._novo` privado usado no RH).
- M3 `APROVADORES` e `AUTORIZADORES` fora da matriz de permissões; M4 `_mudancas_do_bem` ainda mistura banco e regra.
- CRAP: `bi._alertas`, `estoque.saida`, `compras.receber`, `vendas.criar`, `vendas._resolver_avulsas` e os scripts de carga sem teste.
- Teste `test_ordem_de_servico_completa` depende de não existir o tipo de despesa "Manutenção" (passa na ordem normal da suíte).
