# Documentação do Sistema Integrado da Pizzaria

Versão 2.0, 04/11/2026. Fiel ao código do PR #2 (commit `a55b10d`). Comece por aqui.

## Para quem instala e mantém

- [Manual Técnico](tecnico/Manual_Tecnico.md): arquitetura, banco e migrações (até a 018), API, segurança, instalação, operação, integração Anota Ai, testes e pendências.
- [Apêndice A: rotas da API e permissão](tecnico/Apendice_A_Rotas_da_API.md) e [Apêndice B: permissões por perfil](tecnico/Apendice_B_Permissoes_por_Perfil.md), gerados do código.
- [Roteiro de instalação na loja](../instalacao/Roteiro_de_Instalacao_Loja.md).

## Para quem usa (um manual por função, em .md e .docx)

| Função | Manual |
|---|---|
| Todos | [00 Comum a todos](usuario/00_Comum_a_Todos.md) |
| Pizzaiolo | [01 Pizzaiolo](usuario/01_Pizzaiolo.md) |
| Massa | [02 Massa](usuario/02_Massa.md) |
| Acabamento e despacho | [03 Acabamento e Despacho](usuario/03_Acabamento_e_Despacho.md) |
| Atendente | [04 Atendente](usuario/04_Atendente.md) |
| Caixa (atendente e gerência) | [05 Caixa](usuario/05_Caixa.md) |
| Gerente e subgerente | [06 Gerência](usuario/06_Gerencia.md) |
| Administrador e proprietário | [07 Administrador](usuario/07_Administrador.md) |

## Apresentações e fluxogramas (PDF)

- [Apresentação do sistema v2](../apresentacao/Apresentacao_do_Sistema_v2.pdf)
- [Apresentação comercial v2](../apresentacao/Apresentacao_Comercial_v2.pdf)
- [Fluxogramas v2](../apresentacao/Fluxogramas_v2.pdf): 3 áreas, ciclo do pedido, importação do Anota Ai, produção por função, caixa do dia, estoque e vendas fechadas.

## Planejamento (registro das decisões)

- [Plano Macro v2.0](../00_Plano_Macro.md): a seção 0 mostra o estado atual (9 módulos viraram 3 áreas).
- [Módulos 01 a 09](../modulos/): cada um abre com a situação em 04/11/2026.
- [Estrutura de menus](../menus/01_Estrutura_de_Menus.md), [Plano de aplicações e servidores](../arquitetura/Plano_Aplicacoes_e_Servidores.md), [Fatos do manual do Anota Ai](../arquitetura/Anota_Ai_Fatos_do_Manual.md).

## Como manter esta documentação atualizada

1. Quando uma rota ou permissão mudar, na raiz do repositório: `python planejamento/documentacao/fonte/gerar_apendice_rotas.py` e `python planejamento/documentacao/fonte/gerar_apendice_permissoes.py`.
2. Nova migração: acrescentar a linha na seção 3.2 do Manual Técnico.
3. Manuais de usuário em Word: `python planejamento/documentacao/fonte/gerar_docx.py` (usa o pandoc).
4. Apresentações: em `planejamento/apresentacao/fonte_v2`, `python gen_v2.py` e depois `node render.js`.
