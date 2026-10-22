# Resposta ao QA cego da fatia 1B

QA cego em docs/qa_cego_1B.md (15 achados, nenhum de severidade alta). Situação após as correções, com 81 testes passando.

## Corrigidos
- 500 com caractere NUL na busca de clientes: o NUL é removido antes da consulta.
- Telefone: aceita só números, espaço, parênteses, hífen e +; o DDI 55 é removido (12 ou 13 dígitos), então "+55 11..." e "11..." são o mesmo cliente. A busca por telefone usa a mesma regra.
- Histórico de preço de produto e de adicional agora é só de inserção, por gatilho no banco (002_cadastros.sql).
- Tela de clientes: busca com resposta fora de ordem descartada, limite subiu para 200 e o título avisa quando chega ao limite.
- Preço zero recusado em todo o cadastro.
- Nomes em NFC e NFD passam a ser o mesmo nome (normalização NFC).
- Simulador não envia mais id 0 quando falta o sabor.
- Descrição da meia a meia no simulador com vírgula.

## Aceitos como estão
- Inativar categoria não inativa os sabores: decisão de operação, o gerente inativa um a um (confirmar com Marlon).
- Corrida no PATCH de preço: o resultado fica consistente, só o "antes" da auditoria pode ficar defasado. Risco baixo com uma loja.
- 409 genérico para telefone de cliente inativo: mensagem pode melhorar na 1C.
- Telefone na URL pode ir ao log de acesso: o servidor é só da rede local; reavaliar na nuvem.
- Trocar a categoria no formulário refaz os preços sugeridos: comportamento intencional.
- Busca que trata dígitos do nome como telefone e emoji com ZWJ recusado: efeito pequeno.

## Lacunas de teste que ficam
Multi-loja (há uma loja só), concorrência, limites exatos de 8 e 15 dígitos, rotas de atendente por completo e testes automáticos do front (coberto por teste manual no navegador).
