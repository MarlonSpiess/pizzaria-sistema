# Revisão do código com ub-mode (06/11/2026)

Pedido de Marlon: revisar todo o código com a skill ub-mode, conferir boas práticas e passar por dois QA (um cego e um não cego).

Base revisada: commit 08522c7, que é o código instalado no PC da loja (PR #3 sobre o PR #2). O branch main ainda não tem o PR #2, por isso a revisão parte de 08522c7 e não de main.

## Ferramentas

A skill manda usar "crapper", "dryer" e "mutator", mas não traz essas ferramentas. Foram usadas as equivalentes de mercado, guardadas em `tools/` com os comandos em `tools/README.md`:

| Na skill | Usado aqui |
|---|---|
| crapper | `tools/crapper.py`: CRAP = cc² x (1 - cobertura)³ + cc, com radon e coverage.py |
| dryer | `pylint --enable=duplicate-code` |
| mutator | mutmut 3.8.1 nas funções puras, com `tests_unidade/` |
| código morto | pyflakes |

## Medidas

| Medida | Antes (08522c7) | Depois |
|---|---|---|
| Testes | 254 verdes | 324 verdes (testes com banco e de unidade sem banco; 70 novos) |
| Cobertura de linhas (api e scripts) | 85% | 87% |
| Funções com CRAP 10 ou mais | 74 de 842 | 63 de 855 |
| Trechos duplicados (pylint, 6 linhas ou mais) | 4 | 1 |
| Linhas em api/ | 9.476 | 9.296 |
| Mutantes sobreviventes nas funções puras | 105 | 9 (todos equivalentes, ver tools/README.md) |
| Avisos do pyflakes em api e scripts | 7 | 0 |

## Log de ações

| # | Ação | Motivo | Prova |
|---|---|---|---|
| 1 | `normalizar()` de parâmetros virou tabela `_REGRAS` com uma função por tipo | complexidade 27, cadeia de if por tipo | 26 testes de unidade fixaram o comportamento antes; passam depois |
| 2 | Permissões: `_GERENCIA = _TODAS - _SO_DONO - {caixa.aprovar, rh.aprovar}`, matriz em frozenset, `tem_permissao()` e `permissoes_de()` no lugar de 23 consultas repetidas | uma regra num lugar só; set mutável compartilhado por administrador e proprietário | matriz gerada idêntica à anterior (comparação por JSON); teste que confere que toda permissão citada nas rotas existe |
| 3 | Imports sem uso e f-strings sem campo removidos | código morto | pyflakes limpo |
| 4 | `with transacao(conn):` e `gravar_um()` em database.py, no lugar de 60 blocos try/commit/except e de três `_ex()` e três `_grava()` iguais | duplicação; 389 linhas a menos | troca feita por ferramenta que só mexe quando a semântica é idêntica; testes de unidade do helper e suíte completa (291 verdes) |
| 5 | Preço da pizza: `conferir_sabores()` e `preco_pizza()` puras, `calcular_pizza()` só lê o banco | regra de negócio misturada com consulta | testes de unidade da regra (metades arredondadas para cima, somas, recusas) |
| 6 | Testes de mutação: conferem status e mensagem, ordem não alfabética das formas, limite inferior do inteiro, `traduzir_erro`, hash de senha e reais | 105 mutantes vivos | 9 sobreviventes, todos equivalentes |
| 7 | Removidos dois caminhos inalcançáveis em parâmetros ("tipo não suportado" e segundo "Número inválido") | código morto achado pelo mutmut | teste garante que todo tipo do catálogo tem regra |
| 8 | `criar()` do pedido dividida em `_conferir_entrega_e_cliente()`, `_autorizador()` e `_gravar_itens()` | complexidade 35 | suíte de vendas com banco |
| 9 | `receber()` da nota dividida em `_pedido_a_receber()`, `_linha_recebida()` e `_conferir_sangria()` | complexidade 35 | suíte de estoque e compras |
| 10 | Trava presa ou tempo esgotado no banco responde 503 com Retry-After, não 500 | era "Erro interno" para uma falta momentânea | teste novo trava a tabela por outra conexão: antes 500, agora 503 |
| 11 | Bem: valor residual igual ao gravado deixa de contar como mudança | defeito de precedência no `if ... else False` contrariava o comentário da regra | teste novo falhava com 409, agora 200; mudança real continua 409 |
| 12 | Testes das edições de local de estoque, maquininha e funcionário | cobertura de 5%, 7% e 25% | 3 testes novos |
| 13 | Ferramentas em `tools/`, `requirements-dev.txt`, `setup.cfg` do mutmut | a próxima revisão repete as mesmas medidas | rodaram nesta revisão |
| 14 | Correções do QA não cego (preço meio a meio único em Custos, 503 só com Retry-After na leitura, fullmatch, residual nulo) | achados confirmados | testes que falhavam antes |
| 15 | Correções do QA cego (A1 parte, A2, A3, A5, A6, A13, A14, A18 parte, A19) | achados confirmados | `tests/test_qa_ub_mode.py` e `test_edicoes_cadastro.py` |
| 16 | Testes do QA independentes da ordem da suíte | falhavam por estado deixado por outros testes | suíte completa: 324 verdes |

## O que ficou de fora, de propósito

- Frontend (`app.js`): não tem teste automático; a skill pede teste antes de mexer, e um teste honesto de tela não cabe nesta rodada. A leitura não achou HTML montado com texto de usuário (só nós de texto).
- Migrações: já aplicadas no PC da loja; não se reescreve migração aplicada.
- Scripts de carga e instalação (`carregar_cardapio`, `carregar_ficha_tecnica`, `aplicar_migrations_pg`): CRAP alto por falta de teste, mas rodam uma vez e foram conferidos na instalação. Ficam na lista de próximos passos.
- Funções ainda com CRAP acima de 10: a lista completa sai de `python tools/crapper.py cobertura.json 10`. As maiores do app: `bi._alertas` (57% de cobertura), `estoque.saida`, `compras.receber`, `vendas.criar`, `vendas._resolver_avulsas`.
- Nenhuma regra de negócio decidida foi alterada.

## QA

Relatórios em `qa_cego_ub_mode.md` (cego, sem ver o que foi feito; 19 achados), `qa_nao_cego_ub_mode.md` (vendo o diff; nenhuma regressão, 1 alta e 5 médias) e as respostas em `qa_resposta_ub_mode.md`, com o que foi corrigido, o que não é defeito e o que depende de decisão de Marlon.
