# Detalhamento M4: módulo de Checklists

Versão 0.1, 16/11/2026. **PROPOSTA, aguarda a aprovação do Marlon.** Detalha a melhoria M4 de [00_Praticas_e_Melhorias.md](00_Praticas_e_Melhorias.md) e usa os itens de [01_Checklists.md](01_Checklists.md) como conteúdo inicial. Não altera o Plano Macro v2.0, os módulos aprovados nem o código.

> **Atualização de 16/11/2026:** as fatias 4A e 4B, a ligação com a "loja aberta" e parte do 4C e do 4E foram implementadas por decisão do usuário, sem a aprovação do Marlon e sem o piloto em papel que a seção 10 recomendava. Ver a tabela de situação em `00_Praticas_e_Melhorias.md`. Os nomes reais de tabelas e rotas estão nas migrações 022 e 023 e no Apêndice A do Manual Técnico.

> **Onde a implementação difere deste documento** (conferido por revisão independente em 16/11/2026):
> - `concluir` exige `checklist.resolver` (gerência), e não `checklist.executar`: cada função responde os seus itens e a gerência fecha.
> - A rota dos pontos de controle é `/api/checklists/pedidos/{id}/controles`, e a publicação de versão é `POST /api/checklists/modelos/{codigo}/versoes`. Não existem `POST /modelos`, `.../publicar` nem leitura dos itens de um modelo, e a situação `cancelada` não foi criada.
> - Não há tela de edição de modelos; só listar e instalar os modelos padrão.
> - Itens automáticos: só `caixa_aberto`, `loja_aberta` e `backup_do_dia`. Escala, treinamentos, alertas de estoque e sabores fechados seguem como marcação manual.
> - Corrigir uma resposta exige dizer o que foi feito quando ela sai de "não conforme" e sempre que a execução já foi concluída.
> - A aderência está na aba Checklists, e não dentro do BI.
> - O BI de entrega mede até atribuir e até a saída. O tempo na rua não é medido.

**Critério de sucesso:** Marlon lê este documento e diz "aprovado" ou aponta o que corrigir; as decisões da seção 11 ficam respondidas. Aprovado, o módulo segue para o desenho das telas e para a primeira fatia.

Marcações: **[Decisão]** é de Marlon; **[Sistema]** é fato conferido no código ou no plano; **[Fonte]** tem pesquisa citada no documento 00; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. Por que este módulo existe

Hoje o sistema registra o que acontece com o **pedido** (massa, montagem, forno, acabamento, despacho, caixa, estoque), mas não o que acontece com o **dia de trabalho**: abrir a loja, conferir temperatura das câmaras, limpar, fechar. Não há nada parecido com um checklist de abertura ou de fechamento no plano nem no código lido **[Sistema]**.

Esse buraco importa por três motivos. Primeiro, higiene e segurança do alimento dependem de rotinas diárias que hoje só existem na cabeça das pessoas. Segundo, os guias de vigilância citam que o serviço de alimentação deve ter registros com data e identificação de quem preencheu **[Fonte]**. Terceiro, sem registro não há melhoria contínua: não se mede o que se esquece.

## 2. Objetivo

Registrar, por função, o início, o acompanhamento e o fim do dia de trabalho (visão total) e três pontos de controle por pedido (visão de produção), com data, responsável, resultado e ação corretiva, e entregar à gerência um painel de pendências e de aderência.

## 3. Princípios de desenho

1. **Registrar cada fato uma vez** (princípio do Plano Macro, seção 1). Se o sistema já sabe a resposta (caixa aberto, alerta de estoque, "loja aberta", backup do dia), o item é **automático e só leitura**, em vez de pedir que alguém marque de novo.
2. **Pedido a pedido sem cliques novos.** As etapas da pizza já são registradas pelos tablets. A visão de produção do M4 não duplica isso. Ela acrescenta só três pontos que o sistema ainda não registra: leitura do pedido de volta, conferência final do pedido completo e causa do atraso.
3. **Acesso rígido por função, conferido no servidor** (decisão de 03/11/2026). Cada item tem um perfil responsável e só esse perfil, ou a gerência, responde.
4. **Registro que não se edita.** A resposta fica gravada com data, hora e usuário. Corrigir é gravar outra resposta com motivo, nunca apagar. Mesma lógica da auditoria, que só aceita inserção **[Sistema]**.
5. **Não bloquear por padrão.** O checklist orienta e mede. Se vira trava, as pessoas marcam tudo para passar (Lei de Goodhart: medida que vira meta deixa de medir bem). Bloqueios só onde o Marlon decidir.
6. **Produção não recebe mudança de layout** até o Marlon definir o novo (`desenho_tecnico/03_Padroes_de_Layout.md`, linha 7 e item 6 da lista final). Por isso o checklist da produção entra como **tela própria**, que já nasce com o kit de componentes, sem tocar nas telas atuais.

## 4. O que o módulo cobre e o que não cobre

**Cobre:** os seis checklists do documento 01 (início, acompanhamento e fim do dia; início, acompanhamento e fim do pedido, este último como três pontos de controle), itens com valor numérico e limite (temperatura), pendências com responsável, recorrência (semanal, mensal, semestral) para limpeza e manutenção, relatório de aderência no BI.

**Não cobre (v1):** fotos como evidência; assinatura digital; lembretes por WhatsApp; sensores automáticos de temperatura; geração do Manual de Boas Práticas e dos POPs que a RDC 216/2004 exige (o checklist é registro de apoio, não substitui esses documentos); integração com o Imobilizado para abrir ordem de serviço a partir de uma não conformidade (candidata para depois).

## 5. Modelo de dados proposto

Convenções do projeto **[Sistema]**: `loja_id` em tudo, `NUMERIC` para valores, `TIMESTAMPTZ` com horário gerado em Python (fuso America/Sao_Paulo), exclusão lógica por `ativo`, migrações numeradas sem editar as aplicadas. A última migração existente é a 021; este módulo seria a **022** (modelos e execução) e a **023** (pontos de controle do pedido). Nomes e campos abaixo são **[Suposição]** e fecham no desenho técnico.

| Tabela | Para quê | Campos principais |
|---|---|---|
| `checklist_modelo` | Um checklist por tipo | `id`, `loja_id`, `codigo`, `nome`, `tipo` (inicio_dia, acompanhamento, fim_dia), `ativo` |
| `checklist_versao` | Congela o conteúdo usado | `id`, `modelo_id`, `numero`, `publicada_em`, `publicada_por`, `vigente` |
| `checklist_item` | Itens de uma versão | `id`, `versao_id`, `setor`, `ordem`, `codigo`, `texto`, `criterio`, `perfil_responsavel`, `tipo_resposta` (marcar, numero, automatico), `fonte_auto`, `unidade`, `limite_min`, `limite_max`, `obrigatorio`, `recorrencia` (todo_turno, diario, semanal, mensal, semestral), `origem` |
| `checklist_execucao` | Um preenchimento por dia e turno | `id`, `loja_id`, `versao_id`, `data`, `turno`, `iniciada_em`, `iniciada_por`, `concluida_em`, `concluida_por`, `situacao` (aberta, concluida, concluida_com_pendencia, cancelada) |
| `checklist_resposta` | Cada resposta, só inserção | `id`, `execucao_id`, `item_id`, `resultado` (conforme, nao_conforme, nao_se_aplica), `valor_numerico`, `valor_texto`, `acao_corretiva`, `fora_do_limite`, `respondida_em`, `respondida_por`, `substitui_id` |
| `checklist_pendencia` | O que ficou por resolver | `id`, `resposta_id`, `descricao`, `perfil_responsavel`, `criada_em`, `resolvida_em`, `resolvida_por`, `resolucao` |
| `pedido_controle` (migração 023) | Três pontos por pedido | `pedido_id`, `ponto` (leitura_de_volta, conferencia_final, causa_atraso), `ok`, `texto`, `feito_por`, `feito_em` |

**Versões.** Um modelo em uso não se edita: publica-se uma nova versão. Execuções antigas continuam apontando para a versão que usaram, e o histórico fica coerente.

**Resposta vigente.** É a última por (`execucao_id`, `item_id`). A anterior fica registrada, ligada por `substitui_id`. Uma tabela só de inserção, com gatilho que impede atualizar e apagar, segue o padrão da auditoria **[Sistema]**.

**Item automático.** `tipo_resposta = automatico` com `fonte_auto` guarda a chave de uma leitura que o sistema já faz. Candidatas, a confirmar no código na hora de construir: caixa do dia aberto, alertas de estoque (baixo, zerado, negativo), "loja aberta", backup do dia (`backup_registro`), treinamentos com validade (RH), escala do dia (RH).

## 6. Regras de negócio

1. **Uma execução por modelo, dia e turno.** Iniciar de novo no mesmo dia e turno devolve a mesma execução (idempotente).
2. **Quem responde.** Só o perfil responsável do item, ou perfis de gerência. Administrador e proprietário veem tudo.
3. **Registro.** Hora e usuário vêm do servidor, nunca do tablet. Toda escrita passa por `auditar(...)` na mesma transação **[Sistema]**.
4. **Não conformidade.** Resultado "não conforme" exige ação corretiva em texto e cria uma pendência para o perfil responsável.
5. **Valor numérico.** Fora de `limite_min` e `limite_max`, o item vira não conforme sozinho, com `fora_do_limite` verdadeiro, e exige ação corretiva. Os limites vêm de parâmetros da loja, vazios até o Marlon definir (padrão do projeto, decisão de 16/10/2026 **[Sistema]**). A pesquisa sugere refrigerado até 5 °C e congelado a -18 °C ou menos **[Fonte]**; o Marlon confirma.
6. **Concluir.** A execução só conclui com todos os itens obrigatórios respondidos. Com pendência aberta, fica "concluída com pendência". Não impede o fechamento do caixa por padrão.
7. **Recorrência.** Itens semanais, mensais e semestrais aparecem na execução quando vencem, calculados pela última resposta conforme. Não precisa de agenda separada.
8. **"Não se aplica".** Permitido com motivo curto; a gerência vê o total de "não se aplica" por item para pegar uso indevido.
9. **Loja aberta.** Parâmetro `checklist_bloqueia_loja_aberta`, desligado por padrão. Desligado: ao ligar "loja aberta" sem o checklist de início concluído, a tela avisa. Ligado: o servidor recusa, e a gerência pode liberar com motivo, auditado **[Decisão pendente, seção 11]**.
10. **Conferência por amostra.** Toda semana a gerência confere 3 itens de um checklist concluído contra a realidade. Evita o "marcar tudo sem fazer" **[Prática]**.

## 7. Permissões

O sistema nega o que não está liberado e as permissões ficam em `api/security.py` **[Sistema]**. Proposta de quatro permissões novas:

| Permissão | O que permite | Perfis |
|---|---|---|
| `checklist.executar` | Ver e responder os itens da própria função | atendente, massa, pizzaiolo, acabamento, gerente, subgerente, administrador, proprietário |
| `checklist.ver` | Ver tudo do dia, pendências e aderência | gerente, subgerente, administrador, proprietário |
| `checklist.resolver` | Resolver pendências e liberar "loja aberta" com motivo | gerente, subgerente, administrador, proprietário |
| `checklist.gerir` | Editar modelos e publicar versões | administrador, proprietário |

Depois de implementar, rodar os geradores de apêndice de rotas e de permissões e ampliar `tests/test_acesso_rigido.py` **[Sistema]**.

## 8. API proposta

Prefixo `/checklists`, no padrão dos routers existentes (FastAPI, `requer("permissão")`, `get_db`). Nomes **[Suposição]**.

| Rota | Permissão | Função |
|---|---|---|
| `GET /checklists/hoje` | executar | Modelos do dia para o perfil, com a situação de cada um |
| `POST /checklists/execucoes` | executar | Inicia (ou devolve) a execução do modelo, data e turno |
| `GET /checklists/execucoes/{id}` | executar | Itens do perfil, com respostas vigentes e itens automáticos já calculados |
| `PUT /checklists/execucoes/{id}/itens/{item_id}` | executar | Grava uma resposta (nova linha; substitui a vigente) |
| `POST /checklists/execucoes/{id}/concluir` | executar | Conclui, com ou sem pendência |
| `GET /checklists/pendencias` | ver | Lista as pendências abertas |
| `POST /checklists/pendencias/{id}/resolver` | resolver | Fecha a pendência com a resolução |
| `GET /checklists/aderencia` | ver | Itens feitos e não conformes por período (alimenta o BI) |
| `GET/POST /checklists/modelos`, `POST /checklists/modelos/{id}/versoes`, `POST .../publicar` | gerir | Edição e publicação |
| `POST /pedidos/{id}/controles` | conforme o ponto | Grava um dos três pontos de controle do pedido |

## 9. Telas

Segue o layout C, 1 login e 3 áreas, uma tela por função **[Sistema]**. Tudo nasce com o kit de componentes do padrão de layout (cartão, etiqueta de situação, modal, aviso na tela), sem `confirm`, `prompt` nem `alert` **[Sistema]**.

| Onde | Quem | O que mostra |
|---|---|---|
| Produção > Checklist (aba nova) | massa, pizzaiolo, acabamento | Só os itens da função, em botões grandes de 44 px: Conforme, Não conforme, Não se aplica. Campo numérico para temperatura. Lista em cartões em tela estreita |
| Vendas > Checklist | atendente | Itens de balcão, caixa e canais |
| Admin > Checklists do dia | gerência, proprietário, administrador | Alertas primeiro (pendências, itens fora do limite), depois o andamento por setor, depois a aderência |
| Admin > Modelos | administrador, proprietário | Edição de itens e publicação de versão |
| Pedido de balcão (M1) | atendente | Telefone, endereço e entrega sugerida no resumo, com o ponto "li o pedido de volta" |
| Despacho (M3) | acabamento | Bebidas e acompanhamentos para conferir antes de atribuir o entregador |

**Cuidado com a Produção.** O ponto de controle do despacho (M3) e a aba de checklist dos tablets dependem do novo layout da Produção, que o Marlon ainda vai definir. A aba nova não conflita com as telas atuais, mas o M3 mexe numa tela existente e só entra junto desse redesenho **[Decisão pendente]**.

## 10. Fatias de construção

Cada fatia entrega algo que a loja usa. Não estimei horas: o esforço está em tamanho relativo.

| Fatia | Entrega | Tamanho |
|---|---|---|
| 4A | Modelos, versões, execução, resposta só inserção, pendências, tela de execução por função, tela da gerência, carga inicial dos checklists do documento 01 | Grande |
| 4B | Itens numéricos com limite, parâmetros de temperatura, pendência automática fora do limite | Médio |
| 4C | Recorrência (semanal, mensal, semestral) e itens automáticos | Médio |
| 4D | Aderência no BI, pauta da revisão semanal (M7) e aviso ou bloqueio da "loja aberta" | Médio |
| 4E | Pontos de controle do pedido (M1 e M3) | Pequeno e médio; M3 depende da decisão de layout |

**Pré-requisito: piloto em papel.** Os checklists em papel rodam 2 a 3 semanas antes da fatia 4A. A equipe mostra quais itens usa e quais sobram, e o Marlon decide o conteúdo final antes de virar tela **[Prática]**.

**Qualidade.** O padrão do projeto pede testes automatizados e revisão por dois revisores, um deles cego. Pelo registro de instalação de 06/11/2026, a suíte tem 254 testes e a única falha conhecida, com o ambiente configurado, é um teste que confere permissão de arquivo e não vale no Windows. Cada fatia entra com testes de acesso por função, de resposta só inserção, de idempotência da execução e dos limites numéricos.

## 11. Decisões que dependem do Marlon

| # | Pergunta | Minha sugestão |
|---|---|---|
| 1 | "Loja aberta" fica bloqueada até concluir o checklist de início? | Só aviso na primeira versão; bloquear depois, se a equipe aderir |
| 2 | Quem pode marcar "não se aplica" e com que motivo? | Qualquer perfil, com motivo curto e relatório para a gerência |
| 3 | Qual a cadência do checklist de acompanhamento (a cada hora ou outra)? | Começar a cada hora no pico e menos fora dele; ajustar pelo piloto |
| 4 | Limites e frequência de temperatura das câmaras | Começar em 5 °C e -18 °C, conferindo com a vigilância local |
| 5 | Itens que o sistema já sabe ficam automáticos ou o gerente marca? | Automáticos e só leitura |
| 6 | Pendência aberta impede fechar o dia ou o caixa? | Não, só aparece como alerta |
| 7 | Fotos de evidência entram no futuro? | Deixar fora da v1 |
| 8 | Quem edita os modelos? | Administrador e proprietário; gerência propõe |
| 9 | Por quanto tempo guardar os registros? | Definir com orientação jurídica e a vigilância (pendência 10 do plano, LGPD) |
| 10 | O piloto em papel de 2 a 3 semanas vale? | Sim, antes da fatia 4A |

## 12. Riscos

| Risco | O que fazer |
|---|---|
| Fadiga: itens demais viram ruído | Começar só com os itens que o piloto em papel mostrar que a equipe usa |
| Marcar tudo sem fazer | Medir aderência junto de não conformidades achadas e conferir por amostra (regra 10) |
| Mexer na Produção antes do novo layout | Aba própria; M3 só junto do redesenho |
| Tablet com mão suja ou luva | Botões de 44 px; respostas de um toque |
| Dado pessoal | Só o usuário logado; sem foto na v1; retenção a definir (decisão 9) |
| Duas fontes para o mesmo fato | Itens automáticos em vez de nova digitação |

## 13. Fontes

As fontes de pesquisa estão no documento [00_Praticas_e_Melhorias.md](00_Praticas_e_Melhorias.md) e em [01_Checklists.md](01_Checklists.md). O que vem do código foi lido só em parte (migrações 001, 004, 005, 006 e 017, `api/security.py`, `api/database.py`, `api/routers/canais.py` e `vendas_fechadas.py`, a lista de parâmetros e a tela de pedido). O BI e o restante do código não foram lidos.
