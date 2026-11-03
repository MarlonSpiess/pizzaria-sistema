# Estrutura de Menus: Produção, Vendas e Administrativo

Versão 0.2, 03/11/2026, revisada por dois revisores (um sem contexto, outro conferindo contra o código e os documentos aprovados). Etapa 1 da nova direção (menus, depois telas, depois aplicações e servidores). Estilo de navegação: **Layout C** (trilho de ícones com rótulo, que vira barra embaixo no celular), escolhido por Marlon em 03/11/2026.

**Critério de sucesso:** todo item que existe hoje em `sistema/` tem lugar em um dos 3 módulos; nenhum item novo aparece sem fonte (decisão de Marlon, documento aprovado ou boa prática citada); cada item tem os perfis que o veem; Marlon aprova ou aponta o que mudar.

Marcações: **[Existe]** já está construído em `sistema/` (aba e submenu indicados); **[Aprovado]** está num documento de módulo já aprovado, mas ainda não construído; **[Novo]** é proposta deste documento, com a fonte; **[Suposição]** precisa da confirmação de Marlon; **[Proposta]** é mudança sugerida a partir de pedido de Marlon, ainda sem aprovação.

Protótipo navegável: [`planejamento/prototipos/Menus_3_Modulos.html`](../prototipos/Menus_3_Modulos.html). Abra no navegador, troque o perfil no topo e veja o menu mudar.

---

## 1. Princípio que governa o desenho

Um menu bom segue a **tarefa de quem usa**, e não a estrutura do banco ou do código. Três regras de boas práticas de navegação sustentam o desenho:

1. **No máximo dois níveis** (menu e submenu). Mais que isso, o usuário se perde e o tablet exige toques demais. No sistema atual o segundo nível já existe como abas no topo da tela (`subnav`), e continua igual.
2. **Mostrar só o que o perfil pode usar.** O controle de acesso por perfil (RBAC) já existe no servidor; o menu só repete a regra para não mostrar botão que daria erro. O servidor continua sendo a única barreira de segurança.
3. **Poucos itens no trilho.** No celular, o protótipo do Layout C mostra só os itens de operação e põe o resto em "Mais" (`Layout_C_Visual_Cartoes.html`). Com os 19 itens de hoje num trilho só, isso não funciona; por isso cada módulo tem o seu próprio trilho. Neste protótipo, o trilho rola na horizontal no celular; usar "Mais" ou rolagem fica para a Etapa 2 [Suposição].

Aplicado ao caso: Produção e Vendas são **áreas de operação** (tablet e balcão, pico de movimento, botões grandes, poucos itens). Administrativo é **área de escritório** (PC, listas longas, muitos itens). Por isso a separação pedida por Marlon é coerente com a forma como a loja trabalha.

---

## 2. Decisão em aberto: uma entrada ou três aplicações

**Decidido por Marlon em 03/11/2026: um login, três áreas.**

| Critério | Um login, 3 áreas | 3 aplicações separadas |
|---|---|---|
| O que muda no código atual | Pouco: a lista `ABAS` ganha o campo "módulo" e o trilho mostra a área ativa | Muito: 3 frontends, 3 publicações, 3 telas de login |
| Pessoa com mais de uma função (gerente, subgerente) | Troca de área num toque, sem sair | Precisa abrir outro app ou outro endereço |
| Tablet da produção | Abre direto na área Produção (o perfil "pizzaiolo" só vê Produção) | Igual |
| Segurança | A mesma API valida perfil em cada chamada | Igual; separar apps não adiciona barreira |
| Manutenção | Um só lugar para corrigir tema, login e permissões | Três |

O que de fato precisa ser separado é o **servidor de integração com os canais** (Anota Ai, iFood), porque ele roda sozinho, recebe pedidos mesmo sem ninguém logado e depende de internet. Isso é assunto da Etapa 3 (aplicações e servidores) e não muda os menus.

---

## 3. Como a navegação funciona no Layout C

- **Seletor de área** no alto do trilho: 🍕 Produção, 🧾 Vendas, 🏢 Administrativo. Só aparecem as áreas do perfil. Se o perfil tem uma área só (massa, pizzaiolo, acabamento), o seletor some.
- **Trilho** com os menus da área ativa (nível 1).
- **Abas no topo da tela** com os submenus (nível 2), como já é hoje.
- **Avatar** no canto superior direito: Meus dados, Trocar senha e Sair. "Trocar senha" a qualquer momento é [Novo]: hoje a tela só aparece quando a troca é obrigatória, mas o endereço `/auth/trocar-senha` já existe. A chave de tema noite e dia continua ao lado do avatar, como no Layout C.
- **Área inicial ao entrar**: massa, pizzaiolo e acabamento entram em Produção; atendente entra em Vendas; gerência entra na última área usada naquele aparelho [Novo].

---

## 4. Módulo Produção 🍕

Uso: 4 tablets (1 massa, 2 pizzaiolo, 1 acabamento) e a gerência. A unidade de trabalho é a pizza ([02_Producao.md](../modulos/02_Producao.md), aprovado em 19/10/2026).

| Menu (trilho) | Submenu (abas) | Situação | Perfis |
|---|---|---|---|
| 🥣 Massa | Massa e necessidade do dia (necessidade, saldo e falta por tamanho) | [Existe] aba Produção, sub Massa | gerência, massa |
| 👨‍🍳 Montagem | Fila de montagem | [Existe] sub Montagem | gerência, pizzaiolo |
| 📦 Acabamento | Saiu do forno, Acabamento e etiqueta, Despacho (tela única da função) | Saiu do forno e Acabamento [Existe] (hoje a sub Forno e a sub Acabamento); a tela única é [Proposta], pedida por Marlon em 03/11/2026 ("acabamento só vai ver a tela de acabamento/despacho"). Despacho (atribuir entregador) hoje é da recepção, em Entregas, e exige permissão nova (seção 7.1). Teste da impressora térmica pendente | gerência, acabamento |
| ⏱️ Andamento | Andamento (visão geral da cozinha) | [Existe] sub Andamento | gerência; as 3 funções de produção deixam de ver esta tela [Decidido por Marlon em 03/11/2026]. O atendente mantém o Andamento até a hora de entrega calculada aparecer em Vendas > Pedidos; então ele sai de Produção [Proposta] |
| ♻️ Perdas | Perdas e refações (consulta) | [Novo] tela de consulta para a gerência. O registro já existe dentro das filas (perda e refação na montagem e no acabamento, perda de massa na massa); fonte da regra: 02_Producao 5.6 e 8 (refações vão ao BI) | gerência |
| ⚙️ Configurar | Motivos, Etapas de produção | [Existe] sub Motivos; Etapas [Existe] em Fichas e etapas, sub Etapas de produção | gerência |

Nota: as **Etapas de produção** saem de "Fichas e etapas" e vêm para Produção > Configurar, porque descrevem o fluxo da cozinha. As **Fichas técnicas** ficam no Administrativo, porque são custo e cadastro de produto [Suposição].

---

## 5. Módulo Vendas 🧾

Uso: 2 PCs da recepção e o tablet do balcão. Escopo pedido por Marlon: canais (Anota Ai agora, iFood e outros depois), fazer pedidos, entregas e retiradas, caixa.

| Menu (trilho) | Submenu (abas) | Situação | Perfis |
|---|---|---|---|
| 📊 Painel | Painel do turno (uma tela com indicadores: pedidos abertos, caixa do dia, entregas de hoje) | [Novo] reúne números que já existem (BI Painel do dia, Caixa do dia, Entregas) num painel de operação, no padrão do Layout C | gerência, atendente |
| ➕ Novo pedido | Novo pedido (entrega ou retirada) | [Existe] aba Vendas, sub Novo pedido | gerência, atendente |
| 🧾 Pedidos | Pedidos do dia, Quadro por situação | Pedidos do dia [Existe]; Quadro por situação [Novo], é o quadro do Layout C | gerência, atendente |
| 🛵 Entregas | Entregas de hoje (atribuir entregador), Acerto do entregador | [Existe] aba Caixa, sub Entregas | gerência, atendente |
| 🏪 Retiradas | Prontas para retirar | [Novo] hoje a retirada aparece só no quadro de pedidos; separada, a recepção vê de uma vez quem está esperando. Fonte: 02_Producao 5.5 (pizza pronta vai para retirada ou despacho) | gerência, atendente |
| 💰 Caixa | Caixa do dia (abertura, sangria e suprimento, contagem cega, fechamento) | [Existe] aba Caixa, sub Caixa do dia | atendente abre, lança, conta e fecha; aprovar diferença acima da tolerância: gerente, proprietário e administrador (`caixa.py`, APROVADORES) |
| 🔌 Canais | Fila de entrada, Erros de integração, Anota Ai, iFood (futuro), Mapa de produtos (ID externo) | [Aprovado] 01_Nucleo_e_Vendas (canal é cadastro, um adaptador por canal); telas ainda não existem | configurar canal e mapa: só administrador (decisão B10: "só o administrador geral e o desenvolvedor"; o desenvolvedor não é perfil do sistema, [Suposição] ele usa um login de administrador); gerência vê a fila e os erros |
| 👥 Clientes | Clientes (com endereço) | [Existe] aba Clientes | gerência, atendente |
| ⚙️ Configurar | Entregadores, Motivos e maquininhas (motivos de sangria e suprimento, maquininhas, taxa e prazo de recebimento) | [Existe] aba Entregadores; aba Caixa, sub Motivos e maquininhas | gerência edita; atendente só consulta, como hoje |

### 5.1 O que a pesquisa diz sobre os canais

- **Anota Ai.** Não há documentação pública da API. Os manuais de sistemas que já integram mostram o mesmo caminho: o lojista copia o "Token da sua loja" em Configuração geral > Integrações, abre chamado com o Anota Ai e recebe o token da integração; cada produto do Anota Ai é ligado ao nosso pelo campo "ID Externo" no Gerenciador de Cardápio; o cardápio do Anota Ai precisa estar na versão V3; há aceite automático de pedido ([manual CPlug](https://manual.cplug.com.br/books/delivery/page/integra%C3%A7%C3%A3o-anota-ai)). Isso confirma o submenu **Mapa de produtos** e reforça a [Fonte 1] já usada em 01_Nucleo_e_Vendas. O retorno de situação ao Anota Ai (em preparo, saiu, entregue) continua **não confirmado**.
- **iFood.** O portal oficial tem guias de fluxo e de eventos do pedido ([fluxo](https://developer.ifood.com.br/en-US/docs/guides/modules/order/workflow), [eventos](https://developer.ifood.com.br/en-US/docs/guides/modules/order/events)), mas não pôde ser lido em 03/11/2026. Os detalhes (como os pedidos chegam, confirmação de recebimento, situações) ficam [Suposição, não confirmada na fonte] e serão conferidos no portal antes da Etapa 3. Para o menu basta saber que o pedido chega de fora, precisa ser aceito e muda de situação, o mesmo que o Anota Ai.
- **Conclusão para o menu:** os dois canais cabem no mesmo desenho (fila de entrada, mapa de produtos, erros), por isso o menu **Canais** é genérico e cada canal é uma aba. É o que a decisão C7 já pedia.

---

## 6. Módulo Administrativo 🏢

Uso: PC do escritório, gerência e proprietário. "Todas as demais opções."

| Menu (trilho) | Submenu (abas) | Situação | Perfis |
|---|---|---|---|
| 📊 Painel | Painel do dia, DRE, Lucratividade, Produção | [Existe] aba BI | gerência |
| 🍕 Cardápio | Sabores de pizza, Preços por categoria, Bordas e adicionais, Calzones, bebidas e outros, Simulador de preço | [Existe] aba Cardápio. É o cadastro único exportado aos canais (decisão C1) | gerência; atendente só consulta, como hoje |
| 📋 Fichas técnicas | Fichas, Itens, O que falta | [Existe] aba Fichas e etapas (a sub Etapas vai para Produção) | gerência |
| 📦 Estoque | Saldos, Lançar movimento, Inventário, Alertas, Locais | [Existe] aba Estoque | gerência |
| 🛒 Compras | Lista de compras, Pedidos, Recebimento, Fornecedores | [Existe] aba Compras | gerência |
| 🏦 Financeiro | Fluxo de caixa, A pagar, A receber, Lançar, Conciliação, Cadastros | [Existe] aba Contas | gerência |
| 📈 Custos | Custo dos produtos, CMV, Resultado do mês, Fator de correção | [Existe] aba Custos | gerência |
| 🏭 Imobilizado | Alertas, Bens, Ordens de serviço, Plano de manutenção, Inventário, Categorias | [Existe] aba Imobilizado | gerência |
| 👥 RH | Equipe, Escala, Ponto e banco de horas, Ausências e documentos, Folha gerencial, Cadastros | [Existe] aba RH | gerência; Folha gerencial só administrador e proprietário, como hoje |
| 🔑 Sistema | Usuários, Parâmetros, Auditoria, Backup | [Existe] abas Usuários, Parâmetros, Auditoria; Backup é hoje o cartão da aba Painel | Usuários: administrador e proprietário; demais: gerência (editar Parâmetros só administrador e proprietário) |

Vendas (9 itens) e Administrativo (10 itens) passam do que cabe no trilho do celular; ver a regra 3 da seção 1.

---

## 7. Perfis e áreas

"Gerência" = administrador, proprietário, gerente e subgerente (constante `GERENCIA` em `app.js`). Os perfis são os 8 que já existem na tabela `usuario`; nenhum perfil novo é proposto. As permissões abaixo são as da tabela `PERMISSOES` em `api/security.py`; o menu só as repete.

| Perfil | Produção | Vendas | Administrativo | Entra em |
|---|---|---|---|---|
| administrador | tudo | tudo | tudo | última área |
| proprietário | tudo | tudo | tudo | última área |
| gerente | tudo | tudo, menos configurar canais | tudo, menos Usuários, Folha gerencial, editar Parâmetros, aprovar em Financeiro e em Imobilizado | última área |
| subgerente | tudo | tudo, menos configurar canais e aprovar diferença de caixa | o mesmo do gerente, e também menos aprovar em RH | última área |
| atendente | só Andamento, por enquanto (sai quando a entrega calculada aparecer em Vendas > Pedidos) | tudo, menos Canais e aprovar diferença de caixa; Entregadores e Motivos e maquininhas só consulta | Cardápio (só consulta) | Vendas |
| massa | só Massa | nada | nada | Produção |
| pizzaiolo | só Montagem | nada | nada | Produção |
| acabamento | só a tela Acabamento (saiu do forno, acabamento e etiqueta, despacho) | nada | nada | Produção |

Todos os perfis têm **Meus dados** (escala, ponto, banco de horas) no avatar.

### 7.1 Controle de acesso rígido (pedido de Marlon, 03/11/2026)

Regra: **cada função só vê e só acessa a tela que é dela**. O pizzaiolo vê só Montagem; o acabamento vê só Acabamento e Despacho; a massa vê só Massa. Atendente: só Vendas, mais consulta de Cardápio.

**A regra vale no servidor, não só no menu.** Esconder o botão não protege nada: o código das telas (`/static/app.js`) é público e quem sabe o endereço da API chama a rota direto. Boa prática (princípio do menor privilégio; controle de acesso no servidor, OWASP): toda rota confere a permissão do perfil de quem chama.

**Situação medida em `sistema/api` (03/11/2026)**

- Toda rota exige permissão por `requer(...)`; só `/auth/*` e `/health` fogem, por natureza. Massa, pizzaiolo e acabamento têm só `rh.proprio` e `producao.*` (`security.py:46-48`), então já recebem 403 em `/vendas`, `/cardapio`, `/clientes`, `/entregadores`, `/caixa`, `/auditoria` e `/rh` (exceto os próprios dados). Falta apenas o teste que prove isso para cada perfil (hoje há testes de escrita por função em `test_producao.py` e de 4 leituras administrativas em `test_permissoes_usuarios.py`).
- Escritas de produção: oito permissões (`massa`, `montagem`, `forno`, `acabamento`, `perda`, `perda_massa`, `refazer`, `gerir`). Estão certas, com uma exceção: `producao.forno` é do pizzaiolo e do acabamento (`security.py:47-48`).

**Brechas de leitura (fechadas no código em 03/11/2026 e cobertas por `tests/test_acesso_rigido.py`: fila por situação, `cliente`, pedidos, massa, motivos, escala e forno do pizzaiolo; por fazer: Despacho, `entregas.despachar` e a rota de Perdas)**

| Rota | Hoje | Proposta |
|---|---|---|
| `GET /producao/fila` (`producao.py:68`) | `producao.ver`, que atendente, massa, pizzaiolo e acabamento têm; o parâmetro `situacao` deixa o pizzaiolo ler pizzas de qualquer etapa, e a resposta traz o estado do forno | A rota força o conjunto por permissão: montagem vê só "na lista" e "em montagem"; acabamento vê "no forno", "saiu do forno" e "acabada" e o estado do forno; gerência vê tudo. Situação fora do conjunto recebe 403 |
| `GET /producao/fila` e `/pedidos` (`producao.py:11`, `:90`) | Devolvem o nome do cliente a todas as funções (endereço e telefone não vão nessas rotas) | Só quem tem acabamento ou gerência recebe `cliente`, porque só a etiqueta o usa (`app.js:921`) |
| `GET /producao/pedidos` (`producao.py:87`) | `producao.ver` | Só acabamento (usa para "Marcar pedido acabado") e gerência. Deixa de ser a tela Andamento para as funções de produção |
| `GET /producao/massa` (`producao.py:262`) | `producao.ver` | Só massa e gerência |
| `GET /producao/motivos` (`producao.py:297`) | `producao.ver` | Quem tem a permissão de escrita que usa o motivo (`perda`, `perda_massa`, `refazer`, `montagem`) e gerência |
| `GET /rh/escalados` (`rh.py:309`) | `producao.ver`: massa, pizzaiolo, acabamento e atendente leem nome, função e horário de toda a escala. O `app.js` não chama esta rota | Exigir `rh.ver` (gerência); ajustar `test_rh.py:114`, que hoje lê como pizzaiolo |
| Atendente em Produção | Tinha `producao.ver` e lia todas as rotas acima | **Feito em 03/11/2026:** `producao.ver` foi removida de todos os perfis (nenhuma rota a usa mais). O atendente lê só `/producao/pedidos`, por `vendas.ver`, para o Andamento. A hora de entrega calculada só existe nessa rota; devolvê-la em Vendas > Pedidos é mudança de código, a fazer |

Para isso **não é preciso criar permissões de leitura novas**: a rota filtra pela permissão de escrita que o perfil já tem. Menos permissões, menos erro.

**Mudanças de permissão que alteram o fluxo (Marlon escolheu "cada função só a sua tela" em 03/11/2026; Marlon também aceitou, em 03/11/2026, que o acabamento não vê o valor do pedido no despacho e que despachar exige o caixa aberto)**

- **Forno:** retirar `producao.forno` do pizzaiolo; "Saiu do forno" fica só com o acabamento, e a leitura do forno com ele. Os testes de `test_producao.py` já usam o acabamento para esse passo.
- **Despacho no acabamento (feito em 03/11/2026):** permissão nova `entregas.despachar` (acabamento, gerência e administrador) e três rotas: `GET /caixa/despacho` (pedido, situação e nome do entregador, sem total nem valor; avisa quando o caixa não está aberto), `GET /caixa/despacho/entregadores` (só id e nome dos ativos) e `POST /caixa/despacho/{pedido}` (usa sempre o valor padrão da entrega e não devolve valores). O acabamento continua sem `caixa.ver` e sem `entregadores.ver`. Atribuir entregador exige o caixa aberto pela recepção. A rota antiga da recepção (`caixa.operar`) não mudou. Falta registrar na auditoria se a atribuição veio do despacho ou da recepção.
- **Perdas e refações** (seção 4, [Novo]) não tem rota de consulta hoje; a rota nova exigiria `producao.gerir` ou `bi.ver`, a decidir.

**Testes a escrever** (Etapa 3, com os dois revisores): para massa, pizzaiolo, acabamento e atendente, uma matriz rota x perfil que confirma 403 fora da própria tela e 200 dentro; e o menu mostrando só a tela do perfil. Conferir também que `DOCS_ENABLED` está desligado em produção, porque `/docs` e `/openapi.json` listam todas as rotas.

O menu continua só repetindo a regra, para não mostrar o que daria erro. Esta etapa registra a regra e a proposta; mudar `security.py` e as rotas é código e entra na Etapa 3.

Decidido por Marlon em 03/11/2026: uma tela por função. Forno e Despacho ficam dentro da tela do acabamento; o Andamento fica só para a gerência.

---

## 8. Integração entre os módulos (o que liga um ao outro)

O pedido nasce em **Vendas** (balcão ou canal), vira pizzas na fila de **Produção**, volta para **Vendas** pronto para retirada ou despacho, e fecha no **Caixa**. A ficha técnica de cada pizza produzida baixa o **Estoque**, que alimenta **Compras** e **Custos**; o caixa fechado vai para o **Financeiro**; tudo aparece no **Painel** do Administrativo. Os menus não criam ligações novas; mostram as que o sistema já tem.

---

## 9. Mudanças em relação ao menu de hoje

| Hoje (19 itens, 6 grupos) | Proposta |
|---|---|
| Painel e Meus dados em "Visão geral" | Painel de operação em Vendas; Painel gerencial (BI) no Administrativo; cartão Backup em Sistema; Meus dados no avatar |
| Vendas, Produção, Caixa em "Operação" | Vendas e Caixa no módulo Vendas; Produção vira módulo próprio, com cada função no trilho |
| Entregas dentro de Caixa | Entregas vira menu de Vendas |
| Clientes e Entregadores em "Cadastros" | Vão para Vendas (quem usa é a recepção) |
| Fichas e etapas | Fichas no Administrativo; Etapas em Produção > Configurar |
| Motivos e maquininhas dentro de Caixa | Vendas > Configurar |
| Canais | Novo menu em Vendas (sem tela hoje) |
| Retiradas | Novo menu em Vendas (hoje só no quadro de pedidos) |

---

## 10. Próximo passo

Com os menus aprovados, a Etapa 2 revisa cada tela no padrão do Layout C, começando por Vendas > Pedidos (quadro por situação) e Produção (filas por função), que são as de maior uso no pico.

**Recomendação:** aprovar o desenho com um login e três áreas, porque reaproveita tudo o que está construído e testado (188 testes) e deixa a separação real para onde ela importa, que é o servidor de integração com os canais na Etapa 3.


## Canais: estado em 03/11/2026

Tela Vendas > Canais criada (estrutura apenas): um canal por aba (Anota Ai, iFood desativado), fila de entrada com recusa, mapa de ID Externo por produto. Acesso: só gerência (vendas.gerir); isto difere da restrição anterior de configurar canal só pelo administrador (B10), a confirmar com Marlon. Pendentes: aceitar pedido da fila e criar o pedido, Erros de integração, guarda do token (variável de ambiente, nunca no banco), integração real quando o Anota Ai liberar o token.
