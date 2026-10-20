# Plano Macro: Sistema Integrado da Pizzaria

Versão 1.0, 20/10/2026. Consolida o plano macro e os detalhamentos dos nove módulos e do núcleo, todos aprovados por Marlon entre 18 e 20/10/2026. **Aguarda a aprovação final de Marlon.** Os documentos de cada módulo (pasta `modulos/`) são a fonte de verdade de cada assunto; este documento dá a visão do conjunto.

**Critério de sucesso deste documento:** Marlon lê a visão do conjunto (módulos, integrações, ordem de construção, parâmetros e pendências) e diz "aprovado" ou aponta o que corrigir. Aprovado, o planejamento termina e começa o desenho técnico.

**Como ler as fontes.** Cada afirmação vem de uma de três origens, sinalizadas no texto:

- **[Kit]**: o "Kit Aplicação Web" (Allex Corp, 16/10/2026). O kit traz padrão técnico (stack, segurança, banco, migrations, publicação no Fly.io); não traz conteúdo de negócio de pizzaria.
- **[Fonte]**: pesquisa na web, com link na seção 9.
- **[Prática]**: conhecimento de administração e de sistemas de gestão (ERP) sem fonte específica citada. Trate como proposta a validar.
- **[Suposição]**: hipótese minha que depende de resposta sua (seção 8).

---

## 1. Princípio que governa o desenho

Um sistema de gestão integrado funciona quando cada fato do negócio é registrado **uma vez, no módulo onde ele acontece**, e os outros módulos consomem esse registro em vez de redigitá-lo [Prática]. Uma venda nasce em Vendas; dela derivam a baixa de insumos (Estoques), o recebível (Financeiro), o valor esperado no caixa (Fechamento) e a receita da DRE (BI). Se a mesma venda for digitada em dois lugares, os números divergem e o BI perde a confiança.

O pedido de que cada módulo "possa trabalhar isoladamente" é compatível com isso desde que cada ponto de integração tenha **duas entradas possíveis**: a automática (vinda do módulo vizinho) e a manual ou por importação (quando o vizinho ainda não existe ou está desligado). Exemplo: sem o módulo RH, a folha entra em Contas a Pagar como lançamento manual na categoria "Pessoal"; quando o RH existir, o mesmo lançamento passa a ser gerado por ele.

As "5 Leis" do gabarito do projeto (Integração, Hierarquia, Automação, Evolução, Experiência) se aplicam diretamente: a Lei da Integração é o princípio acima; a Lei da Automação pede que baixas de estoque, provisões e conciliações sejam geradas pelo sistema, não digitadas.

---

## 2. Arquitetura macro

### 2.1 Camadas

| Camada | Conteúdo | Observação |
|---|---|---|
| **Núcleo (módulo 0)** | Usuários, perfis e permissões, auditoria, parâmetros da empresa, cadastros mestres compartilhados | Não está na sua lista; proponho que exista porque os 9 módulos dependem dele [Prática] |
| **Módulos operacionais** | 3 Estoques e Compras, 6 Vendas, 7 Produção, 8 Fechamento de Caixa | Registram os fatos do dia a dia |
| **Módulos administrativos** | 1 RH, 2 Imobilizado, 4 Contas a Pagar/Receber e Fluxo de Caixa | Registram compromissos e patrimônio |
| **Módulos analíticos** | 5 Custos, 9 BI | Leem os anteriores; quase não geram fato novo |

### 2.2 Cadastros mestres do núcleo (candidatos)

Estes cadastros são usados por vários módulos; se cada módulo tiver o seu, eles divergem [Prática].

- **Itens**: insumo (farinha, muçarela, caixa de pizza), material de uso e consumo (decisão de Marlon, 18/10/2026), preparo intermediário (massa, molho) e produto de venda (pizza grande calabresa, refrigerante). Com unidade de medida e conversões (saco 25 kg para g).
- **Ficha técnica (receita)**: quanto de cada insumo vai em cada produto ou preparo. É a peça que liga Vendas, Produção, Estoques e Custos. Proposta: cadastro no núcleo, mantido pelo módulo de Custos/Produção.
- **Pessoas e empresas**: fornecedores, clientes, funcionários, entregadores (um cadastro com papéis, ou cadastros separados; a decidir no detalhamento).
- **Plano de contas gerencial e centros de custo**: categorias de receita e despesa que alimentam o fluxo de caixa e a DRE.
- **Formas de pagamento**: dinheiro, Pix, crédito, débito, voucher, pagamento online do Anota Ai. O manual de integração Teknisa x Anota Aí mostra que o Anota Aí identifica a forma de pagamento por código externo com prefixo ONLINE_ ou OFFLINE_ [Fonte 1]; nosso cadastro precisa de um campo equivalente.
- **Unidades/lojas**: o projeto é para uma loja. O identificador da loja existe desde o início porque um futuro aplicativo central lerá o banco de cada loja (decisão de Marlon, 16/10/2026). O regime tributário é parâmetro da loja.

### 2.3 Integração entre módulos

Proposta [Prática]: cada módulo é dono das suas tabelas e só ele escreve nelas. A comunicação entre módulos é feita por **lançamentos de integração** (registro "venda 123 consumiu estes insumos", "compra 45 gerou este título a pagar"), com origem, data, usuário e status. Isso permite: ligar e desligar módulos, reprocessar quando algo falhar, e auditar de onde veio cada número.

No beta tudo roda num único banco e numa única aplicação, separados por esquema ou por prefixo de tabela por módulo [Suposição]. Separar em serviços independentes agora seria complexidade sem ganho para o porte de uma pizzaria (gabarito, "Foque no resultado"; skill `ponytail` do kit).

---

## 3. Dados locais no beta, prontos para a nuvem

| Decisão | Proposta | Origem |
|---|---|---|
| Stack | Python + FastAPI, PostgreSQL, frontend HTML/CSS/JS, mesmo padrão do kit (referência: Simulador Tributário e Cella PCP) | [Kit] seção 1 do LEIA-ME |
| Banco no beta | **PostgreSQL local**, não SQLite. O kit registra oito armadilhas na conversão SQLite para PostgreSQL do PCP (GROUP BY estrito, datas, BOOLEAN, SUM nulo, REAL de 4 bytes, hash bcrypt). Usar o mesmo banco no local e na nuvem elimina essa migração | [Kit] Manual Técnico 5.5 |
| Mudança de esquema | Migrations numeradas `migrations_pg/NNN_*.sql`, com runner de lock e checksum; nunca editar uma já aplicada | [Kit] Manual Técnico 9 |
| Tipos | Dinheiro e quantidades em `NUMERIC`; datas em `TIMESTAMPTZ`; horário gerado em Python com fuso America/Sao_Paulo | [Kit] Manual Técnico 5.4 |
| Segredos | Senha de banco e tokens (inclusive o token do Anota Ai) só em variável de ambiente, nunca no código | [Kit] Manual Técnico 1 |
| Auditoria | Toda escrita de negócio registra usuário e momento; tabela de auditoria só aceita inserção | [Kit] Manual Técnico 7 |
| Exclusão | Exclusão lógica (`ativo`), sem apagar histórico financeiro ou de estoque | [Kit] 5.4 e [Prática] |
| Backup | `pg_dump` antes de cada etapa e rotina diária no beta; arquivos de backup fora do git (LGPD: há dados de clientes e funcionários) | [Kit] LEIA-ME 6 e 10 |
| Nuvem | Fly.io região `gru`, um app e um Postgres. O kit alerta que o Fly Postgres não gerenciado está sem suporte e que o Managed Postgres custa US$ 38/mês no plano Basic (dado de 16/10/2026, confirmar no momento da migração) | [Kit] LEIA-ME 11 |
| Identificadores | Avaliar UUID em vez de `SERIAL` nas tabelas que podem receber dados de mais de uma origem (duas lojas, modo offline). O kit usa `SERIAL`; esta é uma proposta para discutir | [Prática] [Suposição] |

Decisão de Marlon (16/10/2026): o beta roda local, com espelho na nuvem (Fly.io) previsto para depois e, no início, sem espelho. Com um computador da loja servindo os demais aparelhos, se ele parar a operação para; o backup fora da máquina e o procedimento de contingência ficam para o detalhamento do núcleo [Prática]. O futuro aplicativo central lerá o banco de cada loja: o esquema precisa ser estável, documentado e consultável em modo leitura, e cada registro carrega o identificador da loja [Prática].

---

## 4. Os módulos e onde estão detalhados

A numeração original de Marlon (1 a 9) é mantida abaixo; os arquivos seguem a ordem em que foram detalhados.

| Módulo | Situação | Documento |
|---|---|---|
| 0 Núcleo (usuários, perfis, parâmetros, cadastros, auditoria) | Aprovado em 18/10/2026 | [01_Nucleo_e_Vendas.md](modulos/01_Nucleo_e_Vendas.md) |
| 6 Vendas (balcão e Anota Aí) | Aprovado em 18/10/2026 | [01_Nucleo_e_Vendas.md](modulos/01_Nucleo_e_Vendas.md) |
| 7 Produção | Aprovado em 19/10/2026 | [02_Producao.md](modulos/02_Producao.md) |
| 8 Fechamento de Caixa | Aprovado em 19/10/2026 | [03_Fechamento_de_Caixa.md](modulos/03_Fechamento_de_Caixa.md) |
| 3 Estoques e Compras | v0.3 em revisão (lista de compras e cotação, 20/10/2026) | [04_Estoques_e_Compras.md](modulos/04_Estoques_e_Compras.md) |
| 4 Contas a Pagar/Receber e Fluxo de Caixa | Aprovado em 19/10/2026 | [05_Contas_e_Fluxo_de_Caixa.md](modulos/05_Contas_e_Fluxo_de_Caixa.md) |
| 5 Custos | Aprovado em 20/10/2026 | [06_Custos.md](modulos/06_Custos.md) |
| 2 Imobilizado (com manutenção completa) | Aprovado em 20/10/2026 | [07_Imobilizado.md](modulos/07_Imobilizado.md) |
| 1 RH | Aprovado em 20/10/2026 | [08_RH.md](modulos/08_RH.md) |
| 9 BI | Aprovado em 20/10/2026 | [09_BI.md](modulos/09_BI.md) |

### 4.1 Resumo de cada módulo

- **Núcleo.** Usuários com login pessoal e intransferível, perfis (administrador, proprietário, gerente, subgerente, atendente, massa, pizzaiolo, acabamento), parâmetros da loja, auditoria e cadastros mestres: itens, ficha técnica, pessoas e empresas, plano de contas e tipos de despesa, formas de pagamento, loja.
- **Vendas.** Pedido de balcão digitado só neste sistema e pedido do Anota Aí por adaptador, com cardápio único montado aqui e exportado ao Anota Aí (pizzas, calzones e bebidas; borda e extras são adicionais com preço). Pagamento dividido, desconto e acréscimo com motivo, cliente cadastrado na primeira compra, entregador terceiro, apoio à digitação do cupom fiscal.
- **Produção.** Unidade de trabalho é a pizza. API interna num dos PCs, tablets por função (massa em duas fases, pizzaiolo com retrocesso e motivo, forno esteira, acabamento com etiqueta por pizza), pedido urgente e agendado, estimativa de entrega por pizzas na frente.
- **Fechamento de Caixa.** Um caixa por dia, uma gaveta, contagem cega, sangrias e suprimentos, diferenças com justificativa, acerto do entregador por pedido, relatório do dia.
- **Estoques e Compras.** Locais (freezer, câmara fria, estoque seco), baixa pela ficha técnica mais inventário e ajuste, lote e validade nos insumos de pizza e calzone, lista de necessidades com itens avulsos, cotação por fornecedor e lista de compras definitiva (em revisão), pedido de compra por fornecedor, nota digitada, custo médio móvel com os últimos 3 preços visíveis, consumo interno para Custos.
- **Contas a Pagar/Receber e Fluxo de Caixa.** Contas bancárias por loja, despesas recorrentes por tipo, repasse por canal, entregador como conta a pagar, fluxo de 30 dias com 7 em destaque, conciliação digitada no começo.
- **Custos.** Custo do produto pela ficha técnica, CMV teórico e real mensal, custos fixos e variáveis por tipo de despesa, margem e sugestão de preço por margem desejada, ponto de equilíbrio, começando sem meta.
- **Imobilizado.** Bens cadastrados um a um, depreciação fiscal (padrão) ou por vida útil real, e rotina completa de manutenção preventiva, preditiva e corretiva com ordem de serviço, materiais e custos.
- **RH.** Gerencial; folha legal com o contador. Pessoas e contratos por tipo, escala parametrizável (6x1, 5x2 e outras), ponto lançado pelo gerente, benefícios, prévia de folha, treinamentos com validade; salários só para administrador e proprietário.
- **BI.** Só lê. Painel diário, DRE por competência, lucratividade por sabor e por categoria, CMV, produção, caixa, alertas na tela, histórico de 13 meses nas telas.

---

## 5. Mapa de integrações

| De | Para | O que passa |
|---|---|---|
| Núcleo | Todos | Usuários e perfis, itens, ficha técnica, parâmetros, formas de pagamento, loja |
| Vendas | Produção | Pedido, itens e adicionais; pedido urgente |
| Produção | Vendas | Situação do pedido e entrega real |
| Vendas e Produção | Estoques | Consumo pela ficha técnica; perdas; falta de insumo ao retroceder |
| Vendas | Fechamento de Caixa | Valor esperado por forma de pagamento; descontos e cancelamentos; pedidos sem CF |
| Vendas | Contas | Recebíveis por canal e total a pagar do entregador |
| Fechamento de Caixa | Contas | Valores realizados por forma de pagamento; sangrias e suprimentos |
| Estoques e Compras | Contas a Pagar | Títulos das compras |
| Estoques e Compras | Imobilizado | Aquisição de bem |
| Estoques | Custos | Custo médio, estoque inicial e final, perdas, consumo interno |
| Contas | Custos | Despesas fixas reais, taxas de cartão e de canal |
| RH | Núcleo, Produção, Vendas | Pessoa vira usuário; escala de pizzaiolos; funcionário com preço especial |
| RH | Contas, Custos | Valor gerencial de folha, encargos e pro-labore; custo de pessoal |
| Imobilizado | Contas, Custos, Produção | Parcelas e manutenções; depreciação; tempo parado de bem crítico |
| Custos | Vendas | Sugestão de preço |
| Todos | BI | Leitura de tudo, sem escrever |

Cada linha tem uma forma automática e uma forma manual, para cada módulo funcionar isolado.

---

## 6. Ordem de construção

**Princípio:** construir primeiro o que outros módulos consomem e o que dá resultado no dia a dia; o BI vem por último porque só é confiável quando os dados de origem são [Prática].

| Etapa | Módulos | Por quê |
|---|---|---|
| 0 | Núcleo (usuários, perfis, auditoria, parâmetros, cadastros mestres, ficha técnica) | Todos dependem dele |
| 1 | Vendas, Produção e Fechamento de Caixa | Prioridade de Marlon; o Anota Aí entra por último, como adaptador |
| 2 | Estoques e Compras | Com vendas e fichas técnicas, a baixa é automática |
| 3 | Contas a Pagar/Receber e Fluxo de Caixa | Recebe compras e caixa já estruturados |
| 4 | Custos | Precisa de estoque, vendas e despesas |
| 5 | Imobilizado e RH | Alimentam custo fixo; até lá entram como lançamento manual em Contas |
| 6 | BI | Consolida tudo |

**Sugestão de primeiro incremento** [Suposição]: a menor fatia que a loja usa de ponta a ponta é o Núcleo com login e parâmetros, o cadastro do cardápio, o pedido de balcão com pagamento, a fila de produção por função e o fechamento do dia. Os demais módulos entram em seguida, na ordem acima.

---

## 7. Fora do escopo do beta

- Emissão fiscal própria (cupom fiscal): hoje é feita por software de terceiro, com digitação dupla; prevista para o futuro.
- Folha de pagamento legal e eSocial (fica com o contador).
- Ser o registrador oficial de ponto (REP); o relógio biométrico entra depois, por importação.
- Contabilidade societária completa (o BI faz DRE gerencial, não balanço oficial).
- Aplicativo de pedidos para o cliente final (o Anota Aí já cumpre esse papel).
- Envio automático de WhatsApp ao cliente e alertas por WhatsApp (no beta, link de um clique).
- Importação de XML de NF-e, de OFX e de folha do contador (no começo, digitação).
- Previsão de vendas e sensores automáticos de manutenção.
- Várias lojas (o esquema já prevê; a consolidação fica para um aplicativo central).

---

## 8. Decisões de Marlon e pendências

### 8.1 Decisões gerais

Todas as decisões de negócio estão registradas nos documentos dos módulos, com a marcação [Decisão] e o código da pergunta. As de alcance geral:

| # | Tema | Decisão de Marlon |
|---|---|---|
| 1 | Canais e fiscal | Balcão (neste sistema) e Anota Aí; cupom fiscal por software de terceiro hoje |
| 2 | Lojas | Uma loja por banco; cada loja é uma empresa à parte; no futuro um aplicativo central lê todos os bancos |
| 3 | Onde roda | Local no início (PostgreSQL), espelho na nuvem (Fly.io) depois |
| 4 | Equipamentos | 2 PCs na recepção, tablets por função, impressora térmica portátil de etiqueta, forno esteira |
| 5 | Stack | FastAPI, PostgreSQL e HTML, padrão do kit |
| 6 | Prioridade | Vendas, produção e caixa primeiro |
| 7 | Regime tributário | Parâmetro da loja |
| 8 | Acesso ao Anota Aí | Marlon pede só depois de o sistema funcionar |
| 9 | Parâmetros | Valores configuráveis nos parâmetros da loja, sem valor fixo no código |

### 8.2 Parâmetros da loja a definir antes de usar

Ficam vazios ou com padrão e Marlon preenche na implantação:

- Vendas: limite de desconto em % por perfil; taxa padrão de entrega e diária do entregador; desconto e limite diário do preço de funcionário.
- Produção: tempo de forno e capacidade do forno; motivos de retrocesso e de perda.
- Fechamento de Caixa: fundo de troco padrão; valor de sangria que exige o gerente; tolerância de diferença.
- Estoques e Compras: locais de armazenamento; valor de compra que exige aprovação; fator de correção por insumo.
- Contas: contas bancárias; taxa e prazo por maquininha (sem limite de maquininhas) e por canal; tipos de despesa (fixo ou variável); valor de pagamento que exige o administrador.
- Imobilizado: valor mínimo para ser bem (confirmar com o contador); valor de ordem de serviço que exige o administrador; categorias de bem.
- RH: tipos de escala; limite de horas extras; benefícios; tipos de contrato.
- BI: metas (sem meta no começo); alertas ligados.

### 8.3 Pendências abertas

| # | Pendência | Quem resolve | Quando |
|---|---|---|---|
| 1 | D2: lista de sabores e preços por tamanho, de bordas e adicionais | Marlon | Na carga do cadastro |
| 2 | Planilha da ficha técnica (1/2 Grande ou Broto, sabor e ingredientes com quantidade) | Marlon | Na carga do cadastro |
| 3 | Lista de bens, de fornecedores e de funcionários para a carga inicial | Marlon | Na implantação |
| 4 | Token e contato do Anota Aí | Marlon pede após o sistema funcionar | Depois do sistema funcionando |
| 5 | Modelos da impressora e dos fornos | Marlon | No desenho técnico |
| 6 | Qual PC é o servidor e como o segundo assume se o primeiro parar | Marlon e desenvolvedor | No desenho técnico |
| 7 | Backup diário fora da máquina e rotina de contingência | Desenvolvedor | No desenho técnico |
| 8 | Identificador dos registros: UUID ou sequencial | Desenvolvedor | No desenho técnico |
| 9 | Confirmar com o contador: valor mínimo de bem, regime, taxas de depreciação, regras de banco de horas, relatório mensal | Marlon | Antes de ligar os módulos |
| 10 | LGPD: dados de clientes e funcionários, acesso e retenção | Desenvolvedor, com orientação jurídica | No desenho técnico |
| 11 | Atualizar o cadastro de perfis do Núcleo com proprietário e subgerente (subgerente: permissões do gerente, exceto aprovar diferença de caixa) e incorporar em Vendas o preço de funcionário e os itens de cardápio vindos de Produção | Desenvolvedor | No desenho técnico |
| 12 | Cupom fiscal pelo nosso sistema (tipo de documento exigido no estado e município) | A pesquisar | Projeto futuro |

---

## 9. Fontes

1. Teknisa, "Manual AnotaAi" (integração Anota Aí x Teknisa): https://universidade.teknisa.com/wp-content/uploads/2025/12/Manual_AnotaAi.pdf
2. Jornal Contábil, "Portaria 671 e suas implicações no registro de ponto": https://www.jornalcontabil.com.br/noticia/portaria-671-e-suas-implicacoes-no-registro-de-ponto/
3. Lefisc, "Depreciação fiscal" (IN RFB 1.700/2017, Anexo III): https://www.lefisc.com.br/boletins/2025/janeiro_semana_1/IR-depreciacao_fiscal/index.asp
4. Saipos, "Como calcular CMV de uma pizzaria" (cita o Sebrae): https://saipos.com/gestao/controle-de-estoque/como-calcular-cmv-de-uma-pizzaria
5. Kit Aplicação Web (Allex Corp, 16/10/2026): `00_LEIA-ME_Conhecimento_Alcorp.md`, `01_Manual_Tecnico.md`, `anexos/Gabarito_em_Uso.md`.
