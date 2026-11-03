# Estrutura de Menus: Produção, Vendas e Administrativo

Versão 0.2, 03/11/2026, revisada por dois revisores (um sem contexto, outro conferindo contra o código e os documentos aprovados). Etapa 1 da nova direção (menus, depois telas, depois aplicações e servidores). Estilo de navegação: **Layout C** (trilho de ícones com rótulo, que vira barra embaixo no celular), escolhido por Marlon em 03/11/2026.

**Critério de sucesso:** todo item que existe hoje em `sistema/` tem lugar em um dos 3 módulos; nenhum item novo aparece sem fonte (decisão de Marlon, documento aprovado ou boa prática citada); cada item tem os perfis que o veem; Marlon aprova ou aponta o que mudar.

Marcações: **[Existe]** já está construído em `sistema/` (aba e submenu indicados); **[Aprovado]** está num documento de módulo já aprovado, mas ainda não construído; **[Novo]** é proposta deste documento, com a fonte; **[Suposição]** precisa da confirmação de Marlon.

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

Perguntado a Marlon no cartão de decisão. Recomendação: **um login, três áreas**.

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
| 🔥 Forno | Fila do forno | [Existe] sub Forno | gerência, pizzaiolo, acabamento |
| 📦 Acabamento | Acabamento e etiqueta | [Existe] sub Acabamento, botão "Acabada e etiqueta"; só o teste da impressora térmica está pendente | gerência, acabamento |
| ⏱️ Andamento | Andamento (todas as pizzas por fase e tempo) | [Existe] sub Andamento | gerência, atendente, massa, pizzaiolo, acabamento |
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
| atendente | Andamento | tudo, menos Canais e aprovar diferença de caixa; Entregadores e Motivos e maquininhas só consulta | Cardápio (só consulta) | Vendas |
| massa | Massa, Andamento | nada | nada | Produção |
| pizzaiolo | Montagem, Forno, Andamento | nada | nada | Produção |
| acabamento | Forno, Acabamento, Andamento | nada | nada | Produção |

Todos os perfis têm **Meus dados** (escala, ponto, banco de horas) no avatar.

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
