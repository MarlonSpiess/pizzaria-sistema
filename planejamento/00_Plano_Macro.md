# Plano Macro: Sistema Integrado da Pizzaria

Versão 0.5, 18/10/2026. Inclui as decisões de Marlon às perguntas das versões anteriores (seção 8); o restante segue em discussão.

**Situação dos módulos:** Núcleo e Vendas aprovados em 18/10/2026 ([detalhamento](modulos/01_Nucleo_e_Vendas.md)); Produção aprovada em 19/10/2026 ([detalhamento](modulos/02_Producao.md)); Fechamento de Caixa aprovado em 19/10/2026 ([detalhamento](modulos/03_Fechamento_de_Caixa.md)); Estoques e Compras em detalhamento ([rascunho](modulos/04_Estoques_e_Compras.md)); os demais ainda no nível do plano macro.

**Critério de sucesso deste documento:** dar a cada um dos 9 módulos um objetivo, uma lista de submódulos candidatos e as integrações com os outros, definir os princípios de dados (local agora, nuvem depois) e listar o que só o Marlon pode decidir. Detalhamento de telas, tabelas e regras fica para os documentos de cada módulo.

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

## 4. Os 9 módulos

Para cada módulo: objetivo, submódulos candidatos, o que recebe e o que entrega. Submódulos são candidatos, a lapidar um a um.

### 4.1 Módulo 1: RH

**Objetivo.** Gerir o quadro de pessoas e o custo de pessoal da pizzaria.

**Submódulos candidatos.** Cadastro de funcionários e contratos (CLT, intermitente, freelancer, motoboy terceiro); escalas e turnos; registro de ponto (informado no início; importação de ponto eletrônico biométrico no futuro, decisão de Marlon); banco de horas e horas extras; férias e afastamentos; prévia de folha e encargos para custo gerencial; comissões e gorjetas (se houver); treinamentos (ex.: boas práticas de manipulação de alimentos).

**Recebe.** Do núcleo: cadastro de pessoas. De Vendas: base para comissão ou taxa de entrega, se aplicável.
**Entrega.** A Contas a Pagar: salários, encargos, vale-transporte. A Custos: custo de mão de obra (fixo ou por produção). Ao BI: custo de pessoal na DRE.

**Limites que proponho.**
- A folha legal (eSocial, recibos oficiais, guias) costuma ser feita pelo escritório de contabilidade [Prática]. Proponho que o módulo seja **gerencial** e importe ou registre os valores da folha, sem substituir o contador [Suposição: pergunta P5].
- Ponto eletrônico: a Portaria MTP 671/2021 define três tipos de registrador (REP-C, relógio físico; REP-A, alternativo, que depende de acordo ou convenção coletiva; REP-P, por programa, que precisa gerar o Arquivo Fonte de Dados) [Fonte 2]. Construir um REP-P próprio implica atender requisitos técnicos e legais da portaria. Recomendo importar o arquivo de um registrador já existente em vez de criar um. Pelo que sei, a CLT (art. 74, após a Lei 13.874/2019) exige controle de jornada a partir de 20 empregados por estabelecimento; tenho boa confiança nisso, mas confirme com o contador.

### 4.2 Módulo 2: Imobilizado

**Objetivo.** Controlar os bens de uso da pizzaria (forno, masseira, freezer, motos, móveis, computadores) e o custo que eles geram ao longo do tempo.

**Submódulos candidatos.** Cadastro de bens (com nota, valor, data, local, responsável, plaqueta); depreciação mensal; manutenção preventiva e corretiva (agenda e histórico); baixa (venda, perda, descarte); seguros e garantias.

**Recebe.** De Compras: aquisição de bem (nota fiscal). De Contas a Pagar: parcelas do bem.
**Entrega.** A Custos: depreciação mensal como custo fixo. Ao BI: depreciação na DRE (gerencial). A Contas a Pagar: manutenções.

**Referência de taxas.** A IN RFB 1.700/2017, Anexo III, traz as taxas fiscais; exemplos citados: máquinas e equipamentos 10% ao ano (10 anos), móveis e utensílios 20% (5 anos), veículos 25% (4 anos) [Fonte 3]. Para a DRE **gerencial** pode fazer mais sentido usar a vida útil real do bem (o forno pode durar mais ou menos que 10 anos) [Prática]. Proponho permitir as duas, com a fiscal como padrão.

### 4.3 Módulo 3: Estoques e Compras

**Objetivo.** Saber o que existe, o que foi consumido, o que se perdeu e o que precisa ser comprado.

**Submódulos candidatos.**
- Estoques: saldos por item e local (freezer, câmara, estoque seco); entradas; saídas por venda (baixa pela ficha técnica), por produção, por perda/desperdício e por consumo interno (refeição de funcionário); inventário periódico e ajuste; validade e lote (FIFO/PEPS); estoque mínimo e ponto de pedido.
- Compras: cadastro de fornecedores; cotação; pedido de compra; recebimento com conferência contra o pedido; entrada da nota fiscal; histórico de preço por insumo.

**Recebe.** De Vendas e Produção: consumo de insumos. Do núcleo: itens e fichas técnicas.
**Entrega.** A Contas a Pagar: títulos das compras. A Custos: custo médio dos insumos e estoque inicial/final para o CMV. Ao Imobilizado: compras que são bens.

**Por que é central.** O CMV pela fórmula de estoque é `CMV = Estoque Inicial + Compras - Estoque Final` [Fonte 4]. Sem estoque confiável não existe CMV confiável; por isso este módulo vem cedo na ordem proposta (seção 6).

### 4.4 Módulo 4: Contas a Pagar/Receber e Fluxo de Caixa

**Objetivo.** Saber o que a pizzaria deve, o que tem a receber e quanto dinheiro terá em cada dia.

**Submódulos candidatos.** Contas a pagar (títulos, parcelas, recorrentes como aluguel e energia, agendamento, baixa); contas a receber (cartões com prazo e taxa da adquirente, Pix, repasses do Anota Ai ou de outros canais, fiado/convênio se houver); contas bancárias e caixas; conciliação bancária (importação de extrato OFX); conciliação de cartões (venda x repasse x taxa); fluxo de caixa realizado e projetado.

**Recebe.** De Compras: títulos a pagar. Do RH: folha. De Vendas e Fechamento de Caixa: recebíveis por forma de pagamento. Do Imobilizado: parcelas e manutenções.
**Entrega.** Ao BI: realizado por categoria (regime de caixa). A Custos: despesas fixas reais.

**Ponto de atenção.** Taxas de cartão e do canal de delivery são custo variável relevante e muitas vezes ficam escondidas na diferença entre venda e repasse [Prática]. A conciliação é o que as revela.

### 4.5 Módulo 5: Custos

**Objetivo.** Saber quanto custa cada pizza e quanto custa manter a pizzaria aberta, para precificar e medir margem.

**Submódulos candidatos.**
- Ficha técnica e custo do produto: insumos, quantidades, fator de correção (perda no pré-preparo), rendimento; custo unitário recalculado quando o preço do insumo muda.
- CMV teórico x CMV real: teórico = soma das fichas técnicas das vendas; real = fórmula de estoque. A diferença mede desperdício, porcionamento fora do padrão e desvios [Prática].
- Custos e despesas fixas: aluguel, pessoal fixo, depreciação, sistemas.
- Custos variáveis: insumos, embalagem, taxa de cartão, comissão do canal, entrega.
- Precificação e margem de contribuição por produto e por canal (a mesma pizza tem margem diferente no balcão e no delivery por causa das taxas).
- Ponto de equilíbrio.

**Recebe.** De Estoques: custo dos insumos e saldos. De Vendas: mix vendido. De RH, Imobilizado e Contas a Pagar: custos fixos.
**Entrega.** Ao BI: CMV e margens. A Vendas: sugestão de preço.

**Referência.** O Sebrae, citado pela Saipos, aponta CMV ideal por volta de 30% a 40% do faturamento; a Saipos cita 25% a 35% para delivery [Fonte 4]. São referências de mercado, não metas: a meta da sua pizzaria sai do seu próprio histórico.

### 4.6 Módulo 6: Vendas (integração Anota Ai)

**Objetivo.** Registrar toda venda, de qualquer canal, uma única vez, com itens, valores, descontos, taxa de entrega e forma de pagamento.

**Submódulos candidatos.** Cardápio e preços por canal; recebimento de pedidos do Anota Ai; pedidos de outros canais (balcão, telefone, salão, outros aplicativos) [pergunta P2]; cadastro de clientes e endereços; cancelamentos e estornos com motivo; promoções e cupons; entregas (entregador, taxa, tempo).

**O que já se sabe sobre o Anota Ai [Fonte 1].** No manual da integração Teknisa x Anota Aí: a autenticação é por token fornecido pelo Anota Aí mais o ID da loja; cada produto é ligado pelo "ID Externo" cadastrado no Anota Aí; formas de pagamento por código externo (ONLINE_ ou OFFLINE_); observações de item em três tipos (acréscimo, retirada, observação); pedido com produto inexistente ou preço zerado é recusado. O manual não descreve atualização de status nem webhook. **Não encontrei documentação pública da API do Anota Ai**; o acesso provavelmente é por parceria. Em 16/10/2026 Marlon informou que ainda não há token nem contato com o Anota Ai; o material "já visto" não está nesta pasta do projeto.

**Recebe.** Do núcleo: itens e preços.
**Entrega.** A Produção: pedido vira ordem de produção. A Estoques: consumo pela ficha técnica. A Fechamento de Caixa: valor esperado por forma de pagamento. A Contas a Receber: recebíveis online e de cartão. Ao BI: receita.

**Fiscal (decisão de Marlon, 16/10/2026).** Os canais são balcão (neste sistema) e Anota Ai. O cupom fiscal (CF) é emitido por software de terceiro; a evolução disso fica para o futuro. Hoje a venda é digitada duas vezes: neste sistema e no software do cupom fiscal; no futuro este sistema emitirá o cupom (resposta de Marlon à pergunta A1, 16/10/2026). Pedidos de balcão são digitados só neste sistema (resposta à A3).

### 4.7 Módulo 7: Produção (Ordens de Produção)

**Objetivo.** Acompanhar cada pedido da entrada até a entrega, e os preparos feitos em lote.

**Submódulos candidatos.**
- OP de pedido: gerada automaticamente pela venda. O aplicativo móvel se comporta de forma diferente em cada função, e cada colaborador tem login próprio (decisão de Marlon, 16/10/2026):
  - **Massa:** vê as bordas por pedido e a quantidade de massas abertas normais necessárias. A massa é maleável (pode ser produzida antes) e pode ser perdida por vários motivos, que o sistema precisa registrar.
  - **Pizzaiolo:** vê só a pizza que precisa produzir, não o pedido. Os pedidos entram numa fila e as pizzas são solicitadas em sequência, não importa quantos pizzaiolos haja. Ao confirmar a manufatura, a pizza vai para o forno.
  - **Acabamento:** vê os pedidos e as pizzas que estão no forno (depois da confirmação do pizzaiolo) e imprime a identificação em etiqueta autoadesiva, numa impressora térmica portátil; o modelo da impressora varia.
  - Marlon explicou o fluxo completo em 18/10/2026. O detalhamento vigente está em `planejamento/modulos/02_Producao.md` (v0.3, aprovada em 19/10/2026) e substitui o desenho acima.
- OP de pré-preparo: massa, molho, cortes de recheio feitos em lote, que consomem insumos e geram estoque de preparo intermediário com validade.
- Expedição e entrega: atribuição de entregador, saída, retorno.
- Indicadores: tempo médio por fase, atrasos, refação (pizza refeita por erro).

**Recebe.** De Vendas: pedidos. Do núcleo: fichas técnicas.
**Entrega.** A Estoques: consumo e produção de intermediários. A Vendas: status do pedido (e ao Anota Ai, se a integração permitir retorno de status, o que não está confirmado). Ao BI: tempos e perdas.

**Escopo (decisão de Marlon, 16/10/2026).** OP por pedido e também por lote de pré-preparo, pedido primeiro.

### 4.8 Módulo 8: Fechamento de Caixa

**Objetivo.** Garantir, a cada turno ou dia, que o dinheiro e os comprovantes conferem com as vendas.

**Submódulos candidatos.** Abertura de caixa (fundo de troco); sangrias e suprimentos; recebimentos por forma de pagamento; contagem cega no fechamento (operador informa o contado sem ver o esperado) [Prática]; diferenças com justificativa e responsável; acerto de entregadores (dinheiro e troco); relatório do turno; envio dos totais a Contas a Receber e Fluxo de Caixa.

**Recebe.** De Vendas: valor esperado por forma de pagamento.
**Entrega.** A Contas a Receber e Fluxo de Caixa: valores realizados. Ao BI: quebras de caixa.

### 4.9 Módulo 9: BI

**Objetivo.** Transformar os registros dos outros módulos em decisão.

**Submódulos candidatos.** DRE gerencial mensal (receita bruta, deduções, receita líquida, CMV, margem bruta, despesas variáveis, margem de contribuição, despesas fixas, EBITDA, depreciação, resultado); lucratividade por produto, por canal, por dia da semana e por turno; CMV teórico x real; ticket médio e volume; painel diário; metas e alertas (ex.: CMV acima da meta).

**Recebe.** De todos. **Entrega.** Relatórios e painéis; não escreve em outros módulos.

**Ponto de atenção.** A DRE gerencial depende de regime (caixa ou competência) e do regime tributário (as deduções do Simples Nacional são calculadas de forma diferente do Lucro Presumido) [Prática] [pergunta P8].

---

## 5. Mapa de integrações

| De | Para | O que passa |
|---|---|---|
| Vendas | Produção | Pedido gera OP |
| Vendas / Produção | Estoques | Consumo de insumos pela ficha técnica |
| Vendas | Fechamento de Caixa | Valor esperado por forma de pagamento |
| Vendas | Contas a Receber | Recebíveis de cartão, Pix e canal online |
| Compras | Contas a Pagar | Títulos da nota de compra |
| Compras | Imobilizado | Aquisição de bem |
| Estoques | Custos | Custo médio, estoque inicial e final |
| RH | Contas a Pagar / Custos | Folha, encargos, custo de pessoal |
| Imobilizado | Custos / BI | Depreciação mensal |
| Fechamento de Caixa | Fluxo de Caixa | Valores realizados do turno |
| Contas a Pagar/Receber | BI | Realizado por categoria |
| Custos | BI / Vendas | CMV, margens, sugestão de preço |

Cada linha desta tabela terá, no detalhamento, a forma automática e a forma manual (para o módulo funcionar isolado).

---

## 6. Ordem de construção proposta

**Princípio:** construir primeiro o que outros módulos consomem e o que dá resultado no dia a dia; o BI vem por último porque só é confiável quando os dados de origem são [Prática].

| Etapa | Módulos | Por quê |
|---|---|---|
| 0 | Núcleo (usuários, perfis, auditoria, cadastros mestres, ficha técnica) | Todos dependem dele |
| 1 | 6 Vendas + 7 Produção + 8 Fechamento de Caixa | Prioridade de Marlon: o pedido nasce em Vendas, é produzido por função e fecha no caixa; Anota Ai entra por último, como adaptador |
| 2 | 3 Estoques e Compras | Com vendas e fichas técnicas, a baixa de estoque já é automática |
| 3 | 4 Contas a Pagar/Receber e Fluxo de Caixa | Recebe compras e caixa já estruturados |
| 4 | 5 Custos | Precisa de estoque, vendas e despesas |
| 5 | 2 Imobilizado e 1 RH | Alimentam custo fixo; até lá entram como lançamento manual no financeiro |
| 6 | 9 BI | Consolida tudo |

Alternativa razoável: começar por Estoques e Fichas técnicas se o CMV for hoje a maior dor. Minha recomendação é a ordem acima, porque sem vendas registradas a baixa de estoque continua manual. Prioridade de Marlon (16/10/2026): vendas, produção e caixa, sem perder de vista estoques, insumos, custos fixos e variáveis, imobilizado e material de uso e consumo.

---

## 7. Fora do escopo do beta (proposta)

- Emissão fiscal própria (cupom fiscal): hoje é feita por software de terceiro, com digitação dupla; a emissão pelo nosso sistema está prevista para o futuro (Marlon, 16/10/2026).
- Folha de pagamento legal e eSocial (fica com o contador).
- Ser o registrador oficial de ponto (REP).
- Contabilidade societária completa (o BI faz DRE gerencial, não balanço oficial).
- Aplicativo de pedidos para o cliente final (o Anota Ai já cumpre esse papel).

---

## 8. Decisões de Marlon e perguntas em aberto

As referências P1 a P11 no texto vêm da versão 0.1; todas foram respondidas em 16/10/2026, abaixo.

### 8.1 Decisões

| # | Tema | Decisão de Marlon | Efeito no plano |
|---|---|---|---|
| 1 | Canais e fiscal | Vendas pelo balcão (neste sistema) e pelo Anota Ai. O cupom fiscal é emitido por software de terceiro; a evolução fica para o futuro | Fiscal fora do beta; Vendas registra e concilia |
| 2 | Unidades | Uma loja. No futuro, um aplicativo lerá todos os bancos e centralizará as informações | Um banco por loja, esquema estável e legível em modo leitura, identificador de loja nos dados |
| 3 | Maior dor | Seguir a recomendação | Ordem da seção 6 mantida, com Vendas e Fechamento de Caixa primeiro |
| 4 | Regime tributário | Parametrizado por loja | Regime vira parâmetro da loja e muda as deduções da DRE |
| 5 | RH | Seguir a recomendação | Módulo gerencial, folha legal com o contador |
| 6 | Anota Ai | Ainda sem token nem contato | Submódulo só desenhado até haver acesso |
| 7 | OP | Seguir a recomendação | Por pedido e por lote, pedido primeiro |
| 8 | Onde roda | Local no início, com espelho na nuvem (Fly.io) previsto e, de início, sem espelho | PostgreSQL local; espelho só depois |
| 9 | Equipamentos | 2 PCs na recepção, ambos ligados ao Anota Ai, com opção de pedido local só pelo app; 1 tablet na massa, 2 no pizzaiolo e 1 no acabamento, com impressora para identificar as pizzas | Vários aparelhos no mesmo banco pela rede da loja; Produção por estações; identificação impressa no acabamento |
| 10 | Sistemas atuais | Nenhum além do Anota Ai | Nada a migrar |
| 11 | Stack | Seguir a recomendação | FastAPI, PostgreSQL e HTML, padrão do kit |

### 8.2 Consequências técnicas a decidir [Prática]

- Dois PCs e quatro tablets no mesmo banco: um computador faz o papel de servidor local e os demais acessam pela rede da loja, pelo navegador. Qual PC será o servidor, e ele fica ligado durante toda a operação?
- Anota Ai nos dois PCs: o recebimento de pedidos deve acontecer num ponto só (o servidor), para não duplicar pedidos; os dois PCs veem a mesma fila.
- O modelo da impressora do acabamento define o formato da identificação (etiqueta ou comanda).

### 8.3 Perguntas em aberto

- **A1.** (Respondida em 16/10/2026: digitação dupla hoje; no futuro este sistema emitirá o cupom fiscal.)
- **A2.** Quem pode pedir ao Anota Ai o acesso de integração (token)? Sem isso o submódulo fica só desenhado.
- **A3.** (Respondida em 16/10/2026: sim, o pedido local é digitado só neste sistema.)
- **A4.** (Respondida em 16/10/2026: a quantidade de colaboradores é variável e vinculada ao cadastro; o ponto é informado no início e, no futuro, pode ser importado de ponto eletrônico biométrico.)
- **A5.** (Respondida em 16/10/2026: ver o comportamento por função em Produção, seção 4.7. Detalhes ficam para o módulo Produção, que Marlon descreveu como separado e especial.)
- **A6.** (Respondida em 16 e 18/10/2026: etiqueta autoadesiva em impressora térmica portátil, modelo variável; imprime sabor, número do pedido, cliente e observações.)
- **A7.** (Respondida em 16/10/2026: prioridade é vendas, produção e caixa, mantendo no horizonte estoques, insumos, custos fixos e variáveis, imobilizado e material de uso e consumo.)
- **E1.** (Respondida em 18/10/2026: sim, material de uso e consumo é classe de item em Estoques e Compras.)
- **E2.** (Respondida em 18/10/2026: a etiqueta leva sabor, número do pedido, cliente e observações, conforme a lista proposta.)

---

## 9. Fontes

1. Teknisa, "Manual AnotaAi" (integração Anota Aí x Teknisa): https://universidade.teknisa.com/wp-content/uploads/2025/12/Manual_AnotaAi.pdf
2. Jornal Contábil, "Portaria 671 e suas implicações no registro de ponto": https://www.jornalcontabil.com.br/noticia/portaria-671-e-suas-implicacoes-no-registro-de-ponto/
3. Lefisc, "Depreciação fiscal" (IN RFB 1.700/2017, Anexo III): https://www.lefisc.com.br/boletins/2025/janeiro_semana_1/IR-depreciacao_fiscal/index.asp
4. Saipos, "Como calcular CMV de uma pizzaria" (cita o Sebrae): https://saipos.com/gestao/controle-de-estoque/como-calcular-cmv-de-uma-pizzaria
5. Kit Aplicação Web (Allex Corp, 16/10/2026): `00_LEIA-ME_Conhecimento_Alcorp.md`, `01_Manual_Tecnico.md`, `anexos/Gabarito_em_Uso.md`.
