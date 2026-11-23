# QA da integração dos Checklists com os PRs #2 a #5 (23/11/2026)

Base: main depois dos PRs #2, #3, #4 e #5, mais o trabalho feito direto na pasta do mh-spiess em 16/11/2026 (módulo de Checklists, melhorias M1 e M2), que nunca tinha ido para o git. Marlon decidiu em 23/11/2026 trazer esse trabalho por PR.

## O que a integração fez

- Conflitos resolvidos em `canais.py` (imports), `security.py` (permissões de checklist na matriz nova: `checklist.gerir` em `_SO_DONO`; `checklist.executar` para todas as funções; gerência com executar, ver e resolver) e `parametros.py` (tipo `temperatura` virou a regra `_temperatura` em `_REGRAS`, com `fullmatch`).
- Migração do PR #5 renumerada de 022 para `024_pedido_volta_para_producao.sql`: a pasta do PC já usa `022_checklists` e `023_pedido_controle`, e o `aplicar_migrations_pg.py` controla por número e checksum.
- `tests_unidade/test_permissoes.py` ajustado à matriz com checklists.
- Suíte completa no estado integrado: 370 passed.

## Revisor cego: achados e o que foi feito

| # | Achado | Situação |
|---|---|---|
| 1 (alta) | Banco que já aplicou a 022 da main (pedido volta) trava com a renumeração | Nenhum banco persistente rodou a main com o PR #5 (o PC tem a base de 04/11 mais Checklists). Só bancos de teste, recriados a cada execução. Se aparecer um, apagar a linha 22 de `schema_version` com o checksum antigo e rodar de novo (022, 023 e 024 são idempotentes). |
| 2 (alta) | Checklists e a trava da loja usavam `hoje()`, não a data do caixa em uso | Corrigido: `/checklists/hoje`, iniciar execução e a trava da loja aberta usam `caixa.data_do_lancamento`. Teste `test_checklist_usa_a_data_do_caixa_aberto_depois_da_meia_noite` |
| 3 (média) | Item periódico sumia por um "conforme" já corrigido | Corrigido: só vale a resposta vigente de cada execução. Teste `test_item_periodico_corrigido_para_nao_conforme_continua_vencido` |
| 4 (média) | A tela não pedia o motivo para liberar a loja nem mostrava o aviso | Corrigido em `app.js`: no 409 pede o motivo e reenvia; mostra `aviso_checklist` |
| 5 (média) | Item numérico ignorava "não conforme" explícito | Corrigido: fora do limite ou marcado não conforme vira não conforme, com ação obrigatória. Teste `test_item_numerico_aceita_nao_conforme_explicito` |
| 6 (média) | Duas execuções do mesmo modelo, dia e turno com versão nova publicada no mesmo instante | Corrigido: `iniciar` trava a linha do modelo (`FOR UPDATE`) |
| 7 a 11 (baixa) | Modelos e itens editáveis no banco sem gatilho; pontos de controle sem validação de situação; motivo de liberação de 1 caractere; aderência com muitas consultas; testes fracos em `test_checklists.py` | Pendentes. Dependem das decisões do pacote de aprovação de 16/11 (M4-1 a M4-10) ou ficam para a próxima rodada |

## Revisor não cego

Ver seção abaixo (preenchida quando o revisor terminar).
