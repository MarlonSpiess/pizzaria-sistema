# Práticas e melhorias: atendimento, produção, acabamento e entrega

Versão 0.1, 16/11/2026. **PROPOSTA, aguarda a aprovação do Marlon.** Incorpora ao projeto o que foi levantado na pesquisa de boas práticas e na leitura do plano e do código. Não altera o Plano Macro v2.0 nem os módulos aprovados.

> **Atualização de 16/11/2026: implementado no código, ainda sem aprovação do Marlon e sem piloto em papel.** Por decisão do usuário, as melhorias abaixo foram construídas no sistema com as sugestões deste documento como padrão (tudo ajustável por parâmetro). Backup do código antes da mudança: `C:\AlCorp\backup_sistema_pizzaria_20261116_112145`. Os testes novos (`tests/test_checklists.py`) foram escritos mas **não foram executados** neste ambiente; falta rodar a suíte (comando no Manual Técnico, seção 8) antes de usar na loja.
>
> | Melhoria | Situação |
> |---|---|
> | M1 resumo do pedido | Parcial: telefone, endereço e a caixa "Li o pedido de volta ao cliente" no resumo, gravando o ponto de controle. A entrega sugerida não entrou: o cálculo só existe depois de criado o pedido. |
> | M2 tempos de entrega no BI | Feito em `GET /api/bi/producao` (`tempos_entrega`) e no cartão "Entregas: até atribuir e até sair". Mede do pedido até atribuir o entregador e até a saída. **O tempo na rua não é medido**: `entrega_real` é gravada no despacho, e o sistema não registra a chegada ao cliente. |
> | M3 conferência de bebida no despacho | **Não feito.** Mexe na tela de despacho, que o projeto mantém congelada até o novo layout da Produção. A API do ponto `conferencia_final` já existe. |
> | M4 módulo de Checklists (fatias 4A e 4B) | Feito: modelos e versões, execução por função, respostas só de inserção, pendências, itens numéricos com limite por parâmetro, tela das funções e da gerência, modelos padrão. |
> | M5 itens numéricos com alerta | Feito: fora do limite vira não conforme e pede ação corretiva. |
> | M6 itens periódicos | Parcial: o modelo aceita recorrência e só mostra o item quando vence; os modelos padrão usam "todo turno" porque as frequências não foram definidas. |
> | M7 pauta da revisão semanal | Parcial: a aba Aderência existe; a pauta montada pelo BI não. |
> | M8 horário de temperagem da massa | Não feito. |
> | Pontos de controle do pedido (4E) | Parcial: leitura de volta tem tela; conferência final e causa do atraso só pela API (`POST /api/checklists/pedidos/{id}/controles`). |
> | Loja aberta (4D) | Feito: avisa por padrão; recusa só se `checklist_bloqueia_loja_aberta` for "sim". |

Marcas: **[Fonte]** pesquisa citada; **[Sistema]** o sistema já faz; **[Prática]** conhecimento geral; **[Definir]** valor a decidir; **[Proposta]** melhoria nova.

## 1. Origem

Parte da pesquisa de boas práticas de pizzaria (revistas do setor e fornecedores, quase todas dos EUA; guias de vigilância sanitária e do Sebrae no Brasil) e da leitura do plano macro, do módulo de Produção e de trechos do código (migrações 004, 005 e 006, rotas de despacho e a tela de pedido de balcão). O BI e o restante do código não foram lidos. Regras gerais de produtividade (Parkinson, Pareto, Hick, Goodhart e outras) foram aplicadas à pizzaria no arquivo de referência.

## 2. Melhorias propostas para o sistema

| # | Melhoria | Onde mexe | Esforço | Decisão do Marlon |
|---|---|---|---|---|
| M1 | Resumo do pedido com telefone, endereço e entrega sugerida (só leitura) | Tela de pedido de balcão | Pequeno | Nenhuma |
| M2 | Tempo de saída e tempo na rua no BI, usando atribuido_em e entrega_real | BI e regra do despacho | Pequeno | Atribuir o entregador na hora em que sai |
| M3 | Conferência de bebida e acompanhamento no despacho, sem valores | Tela de despacho e rota /despacho | Médio | Mexe numa decisão aprovada; obrigatório ou só aviso |
| M4 | Módulo de Checklists: modelos por função e turno (início, acompanhamento, fim), execução com data, responsável, item ok ou não, observação e ação corretiva, relatório de aderência no BI | Tabelas, rotas e telas novas | Grande | Se bloqueia "loja aberta"; itens por estação; só depois do piloto em papel |
| M5 | Itens com valor numérico e limite (temperatura), com alerta fora do limite | Parte do M4 | Médio | Limites e frequência (ver Definir) |
| M6 | Itens recorrentes (diário, semanal, mensal, semestral) para limpeza e manutenção | Parte do M4 | Médio | Frequências do Manual de Boas Práticas |
| M7 | Pauta da revisão semanal montada pelo BI (atrasos, perdas, CMV, aderência) | BI | Médio | Quem participa e quando |
| M8 | Registro opcional do horário de temperagem da massa | Massa (lote e validade) | Pequeno | Depende dos tempos da receita |

**Recomendação de ordem.** M1 e M2 primeiro, porque usam o que já existe e dão medição real. M3 depende de decisão. M4, M5 e M6 só depois de os checklists em papel rodarem por 2 ou 3 semanas, para ver quais itens a equipe usa antes de virarem tela. M7 e M8 depois.

**Fatos verificados no código (somente leitura).** O cartão "3. Resumo" do pedido de balcão mostra itens, ajustes e total antes de "Confirmar pedido". A tabela `entrega` grava `atribuido_em` (momento da atribuição do entregador) e o pedido grava `entrega_real`. Não há nada parecido com um checklist de abertura ou de fechamento do dia no plano nem no código lido.

## 3. Fases de implantação

| Fase | O que fazer |
|---|---|
| 0, sem código, esta semana | Imprimir os checklists (arquivo docx). Combinar no balcão a leitura do pedido de volta. Conferência final do pedido com bebida. Teste de ventilação da caixa. Pedido-teste mensal pelo canal. |
| 1, depois da carga de fichas e tempos | Calibrar o tempo prometido. Completar fichas e quadro de gramaturas. Definir os tempos da massa e os tempos-alvo. Medir o tempo entre "acabada" e a atribuição do entregador. Revisão semanal dos motivos de perda. |
| 2, mudanças pequenas no sistema | M1 e M2. |
| 3, depois do piloto em papel | M3 (se aprovada), M4, M5, M6. |
| 4, opcional | M7, M8 e roteirização de entregas, só se o volume justificar. |

## 4. Valores a definir

| O que definir | Quem define ou onde está |
|---|---|
| Temperatura e pré-aquecimento do forno | Manual do forno e receita |
| Tempos da massa (descanso, temperagem, janela de uso) | Receita da loja |
| Tempos-alvo por etapa (massa, montagem, forno, acabamento, despacho) | Marlon, com base no histórico do BI |
| Frequência da leitura de temperatura das câmaras durante o turno | Marlon e vigilância sanitária local |
| Limites de temperatura de recebimento por produto | Manual de Boas Práticas da loja |
| Cronograma de limpeza periódica (coifa, câmara, reservatório, pragas) | Manual de Boas Práticas e normas locais |
| Se "loja aberta" fica bloqueada até o checklist de início ser concluído | Marlon |
| Cadência do acompanhamento (a cada hora ou outra) | Marlon |
| Meta de CMV e de custo de pessoal da loja | Marlon e contador |

## 5. Limites e cuidados

- A maior parte das fontes é de fornecedores e revistas do setor. Trate como prática de mercado, não como norma.
- Limites de temperatura vêm de materiais secundários que citam a RDC 216/2004 (refrigerado até 5 °C, congelado a -18 °C ou menos, manutenção a quente a 60 °C ou mais por até 6 h). Há divergências entre fontes e normas estaduais ou municipais. Confirme no texto oficial e com a vigilância sanitária do município.
- Referência de CMV entre 30% e 40% vem de páginas de fornecedores que atribuem o dado ao Sebrae; a página original não foi encontrada.
- Alegações de fabricantes (por exemplo "cortou reclamações pela metade" e "economiza 15 a 20 s por pizza") não têm dado e não foram usadas.
- Os passos de limpeza do forno dependem do modelo; siga o manual do fabricante.

## 6. Arquivos desta pasta

- [02_Modulo_Checklists_M4.md](02_Modulo_Checklists_M4.md): detalhamento da melhoria M4 (módulo de Checklists): dados, regras, permissões, API, telas, fatias e decisões do Marlon.
- [01_Checklists.md](01_Checklists.md) e Checklists_da_Pizzaria.docx (versão para imprimir): os três checklists do dia e os três do pedido.
- referencia/: as listas geradas na pesquisa, em Word (lista completa, lista compacta geral e lista compacta da pizzaria). A lista compacta da pizzaria traz as 14 práticas por etapa, com a situação de cada uma no sistema.

## Anexo A. Regras gerais e práticas por etapa

(Conteúdo da lista compacta da pizzaria, convertido do arquivo de referência. A numeração de fases deste anexo é a da lista original; vale a numeração da seção 3 acima, em que as mudanças M1 e M2 formam a fase 2.)

Fork para a produção diária da pizzaria, derivado da "lista compacta" geral. Foco em atendimento, produção, acabamento e entrega.

Backup dos originais: C:\AlCorp\backup_20261116_093611 (lista completa e lista compacta, conferidos por hash).

Projeto de referência: Sistema Integrado da Pizzaria (C:\Maria Gabriela\Pizzaria), plano macro v2.0 de 04/11/2026. Confirmado pelo usuário como o "Sistemas Integrados Pizzaria".

### Como ler

- "No sistema hoje" usa quatro estados: Existe, Parcial, Não há e Não se aplica. Onde não consegui confirmar, está escrito "não verifiquei". Li o plano, o módulo de Produção e, em parte, o código (migrações 004, 005 e 006, rotas de despacho e a tela de pedido). O BI e o restante do código não foram lidos.

- "Fonte e confiança" diz de onde vem a prática. A maior parte da pesquisa é de revistas do setor e de fornecedores, quase toda dos EUA. Trate como prática de mercado, não como norma.

- Nenhum valor numérico foi inventado. Onde há faixa, ela vem da fonte citada e deve ser validada na receita e na cozinha da loja.

### 1. As 9 regras gerais aplicadas à pizzaria

| **\#** | **Regra geral**              | **Na pizzaria**                                                                                                                                   | **Observação**                                                                                             |
|--------|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| 1      | **Parkinson**                | Tempo-alvo curto por etapa (massa, montagem, forno, acabamento, despacho), em vez de um prazo único para o pedido.                                | Tempo de forno e capacidade já são parâmetros da loja; falta definir os demais tempos-alvo.                |
| 2      | **Brooks**                   | Em pico com atraso, antes de pôr mais gente numa estação, reduza escopo: desligar "loja aberta", empurrar pedidos para agendados, fechar sabores. | Analogia: a lei original trata de projetos de software.                                                    |
| 3      | **Pareto**                   | Concentre mise en place e treino nos sabores que mais saem.                                                                                       | Não assuma 80/20: confira no BI (lucratividade por sabor) quanto os sabores mais vendidos realmente pesam. |
| 4      | **Hick**                     | Cardápio enxuto no balcão e telas com poucas ações por função.                                                                                    | As telas por função já seguem essa linha. O cardápio é decisão do Marlon.                                  |
| 5      | **Agir sem certeza total**   | Comece pelas rotinas manuais (fase 0 abaixo), sem esperar o sistema.                                                                              | Ajuste depois de uma semana de uso.                                                                        |
| 6      | **Goodhart**                 | Se só o tempo de entrega for meta, a pressa pode custar qualidade. Acompanhe junto refações, perdas e reclamações.                                | O BI já prevê refações, perdas e atrasos.                                                                  |
| 7      | **Quatro campos por tarefa** | Cada estação tem responsável, jeito certo (ficha e gramatura), prazo (tempo-alvo) e motivo.                                                       | Responsável: função com login próprio.                                                                     |
| 8      | **Um responsável final**     | Um responsável por turno e um por estação.                                                                                                        | O acesso rígido por função já separa o que cada um vê e faz.                                               |
| 9      | **Ciclos curtos**            | Revisão semanal com o BI: mude uma coisa, meça, confirme.                                                                                         | Comece pelo tempo prometido contra o tempo real.                                                           |

### 2. Práticas por etapa

#### Atendimento

| **\#** | **Prática** | **Fonte e confiança** | **No sistema hoje** | **Como e quando implementar** |
|----|----|----|----|----|
| A1 | **Ler o pedido de volta e confirmar telefone e endereço** | Guias do setor de pizzaria (PMQ, Pizza Today). Confiança média: orientação de prática, sem estudo. | Parcial. O cartão "3. Resumo" mostra itens, ajustes e total antes de "Confirmar pedido" (conferido no código). Telefone, endereço e entrega sugerida não aparecem no resumo; não li o cartão "1. Pedido e cliente". | Fase 0: regra falada no balcão. Fase 2: mostrar telefone, endereço e entrega sugerida, só leitura, no resumo. |
| A2 | **Prometer um tempo que se cumpre** | Foodtec e Slice (fornecedores de sistema). Afirmam que a precisão do tempo prometido pesa mais que a velocidade. Confiança média. | Existe. A entrega calculada usa pizzas na frente, pizzaiolos ativos, forno, acabamento e deslocamento; a entrega real é gravada; o BI mostra atrasos. | Fase 1: após a carga dos tempos, compare prometido e real por 2 a 4 semanas e ajuste os parâmetros. |
| A3 | **Plano B para o pico** | Slice (plano B para telefones sobrecarregados). Confiança baixa a média; é adaptação minha. | Parcial. Existem pedido agendado, "loja aberta" e fechamento de sabores por ingrediente. | Fase 0: combine quando desligar "loja aberta" e quando empurrar para agendado. |

#### Produção

| **\#** | **Prática** | **Fonte e confiança** | **No sistema hoje** | **Como e quando implementar** |
|----|----|----|----|----|
| P1 | **Mise en place por estação antes do serviço** | Pizza Today e modelos de checklist. Confiança média. A economia de "15 a 20 s por pizza" é alegação de fabricante, não usei. | Não há checklist de abertura no plano. Há alerta de estoque baixo e o botão "Sem ingredientes". | Fase 0: checklist em papel por estação. Fase 2: no sistema, se fizer sentido. |
| P2 | **Porção padronizada, quadro à vista e pesagem periódica** | Pizza Marketplace e Speedline; Sebrae sobre ficha técnica e pré-pesagem. Confiança média a alta para a ficha técnica. | Parcial. Ficha técnica no núcleo e baixa de estoque por ficha existem. Fichas de bordas, adicionais e bebidas e o fator de correção ainda não têm dado. | Fase 1: complete as fichas, cole o quadro de gramaturas na linha e pese amostras toda semana. Compare CMV teórico e real em Custos. |
| P3 | **Gestão da massa: dividir logo, resfriar, temperar, usar dentro da janela** | PMQ e Heckers Ceresota (fornecedor). Valores variam: mínimo de 18 h e 24 a 48 h típicos; temperar até cerca de 10 a 13 °C (50 a 55 °F); janela de 2 a 3 h. Confiança média; dependem da receita. | Parcial. A função Massa tem duas fases, lote e validade para massas e contagem de massa aberta. Não vi registro de horário de resfriamento ou temperatura. | Fase 1: o Marlon define os tempos da receita da loja. Use lote e validade como marcador de horário. Fase 2: avalie registrar o horário de temperagem. |
| P4 | **Registrar perdas com motivo e refação ligada à original** | Sebrae (planilhas de perda no pré-preparo). Confiança média a alta. | Existe. Motivos de perda e retrocesso, refação ligada à pizza original e cartão "Pizzas perdidas para refazer". | Fase 1: revisão semanal dos motivos no BI. |
| P5 | **PEPS e validade** | Sem fonte específica encontrada nesta pesquisa. Prática comum de gestão de estoque. | Existe. Estoques prevê lote, validade e saída pelo mais antigo, inclusive para massas. | Fase 1: conferir se a equipe segue a regra no estoque físico. |

#### Acabamento

| **\#** | **Prática** | **Fonte e confiança** | **No sistema hoje** | **Como e quando implementar** |
|----|----|----|----|----|
| F1 | **Conferência final do pedido antes de fechar** | Foodtec (dupla conferência). Fonte única de fornecedor; confiança baixa a média. | Parcial. Etiqueta por pizza com cliente, Id e sabor; pedido acabado só à mão. Bebida e acompanhamento não entram no checklist do acabamento (decisão aprovada). | Fase 0: conferência final inclui bebida e acompanhamento, no despacho. Fase 2: item no checklist de entrega. |
| F2 | **Ventilar a pizza antes de fechar a caixa e evitar vapor e gordura** | PMQ, Racklify (vendedor de caixas), Takeaware. Falam em 1 a 2 min de ventilação; há troca com perda de calor. Confiança baixa a média. | Não há. É procedimento físico. | Fase 0: teste da loja com a caixa atual, comparando 0, 1 e 2 min de ventilação. Registre o resultado como padrão. |
| F3 | **Não deixar a pizza pronta esperando o despacho** | Blogs de embalagem: cerca de 20 a 30 min quente na caixa. Fonte fraca. RDC 216 (fontes secundárias): manter quente a 60 °C ou mais, até 6 h. Não li o texto oficial. | Parcial. O despacho está na tela do acabamento e há tempos por etapa. O sistema grava o momento em que o entregador é atribuído (atribuido_em). | Fase 1: meça o tempo entre "acabada" e a atribuição do entregador. Antes de usar a regra de temperatura, confirme com a vigilância sanitária local. |

#### Entrega

| **\#** | **Prática** | **Fonte e confiança** | **No sistema hoje** | **Como e quando implementar** |
|----|----|----|----|----|
| E1 | **Separar tempo de saída da loja e tempo na rua** | Foodtec. Fonte única de fornecedor; confiança média. | Parcial. O sistema grava a hora do pedido, a atribuição do entregador (atribuido_em) e a entrega real (entrega_real). Não verifiquei se o BI já separa tempo de saída e tempo na rua. | Fase 2: sem campo novo; usar a atribuição como saída e mostrar os dois tempos no BI. Exige atribuir o entregador na hora em que ele sai. |
| E2 | **Agrupar entregas por rota** | Foodtec: roteirização e agrupamento reduzem o tempo na rua. Confiança baixa a média. | Não há. O entregador é terceiro; roteirização não está no escopo. | Fase 3, só se o volume justificar. Avalie junto da decisão sobre o módulo de entrega do Anota Ai. |
| E3 | **Fazer o próprio pedido-teste** | Foodtec. Fonte única; baixo custo. | Não se aplica. | Fase 0, uma vez por mês: peça pelo canal e acompanhe até a porta. |

### 3. Quando implementar

| **Fase**                                        | **Itens**                                                                                                                                                                                                                                  |
|-------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Fase 0 (sem código, esta semana)                | **A1 e A3 combinados no balcão; P1 checklist em papel; F1 conferência final com bebida; F2 teste de ventilação; E3 pedido-teste.**                                                                                                         |
| Fase 1 (depois da carga de fichas e tempos)     | **A2 calibragem do tempo prometido; P2 fichas, quadro e pesagem; P3 tempos da massa; P4 e P5 revisão semanal; F3 medição entre "acabada" e a atribuição do entregador.**                                                                   |
| Fase 2 (mudanças no sistema, decisão do Marlon) | **E1 tempos de saída e na rua no BI; A1 telefone, endereço e entrega sugerida no resumo; F1 conferência de bebida no despacho (depende de decisão); P1 checklist de abertura (só depois de 2 a 3 semanas de papel). Detalhes na seção 4.** |
| Fase 3 (condicional)                            | **E2 roteirização, somente se o volume justificar.**                                                                                                                                                                                       |

### 4. Mudanças de sistema (fase 2)

Verificadas por leitura do código, sem alterar nada. Cada item depende de decisão do Marlon.

| **\#** | **Mudança**                                                                                                                                                      | **Onde mexe**                                                                  | **Esforço**      | **Decisão do Marlon**                                                                                                                    |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| 1      | **Horário de saída (E1): usar atribuido_em como saída e mostrar no BI o tempo de saída (pedido até atribuição) e o tempo na rua (atribuição até entrega_real).** | Regra de uso no despacho e relatório do BI. Não verifiquei se o BI já calcula. | Pequeno          | Confirmar que o entregador é atribuído na hora em que sai. Se for antes, o tempo de saída fica errado.                                   |
| 2      | **Resumo para ler de volta (A1): mostrar telefone, endereço e entrega sugerida, só leitura, no cartão "3. Resumo".**                                             | frontend/static/app.js, perto da linha 835.                                    | Pequeno, só tela | Nenhuma. Antes, conferir o que o cartão "1. Pedido e cliente" já mostra.                                                                 |
| 3      | **Conferência de bebida no despacho (F1): listar bebidas e acompanhamentos, sem valores, com marca de "conferido" antes de atribuir o entregador.**              | Tela de despacho do acabamento e rota /despacho em api/routers/caixa.py.       | Médio            | Sim. Mexe numa decisão aprovada (bebida e acompanhamento fora do checklist do acabamento). Decidir se a marca é obrigatória ou só aviso. |
| 4      | **Checklist de abertura por estação (P1): modelo por função e registro de quem conferiu e quando.**                                                              | Tabelas, rotas e tela novas; não existe nada parecido hoje.                    | Médio a grande   | Sim. Se bloqueia "loja aberta" ou só registra; quais itens por estação.                                                                  |

- Recomendação: fazer 1 e 2 primeiro, pois usam o que já existe. O 3 depende de decisão. O 4 só depois de o checklist em papel da fase 0 rodar por 2 ou 3 semanas, para ver quais itens a equipe realmente usa.

- Item opcional, fora da fase 2: registrar o horário de temperagem da massa (P3). Depende dos tempos da receita; até lá, lote e validade da massa servem como marcador.

### 5. Pendências e limites

- Os tempos da massa (descanso, temperagem, janela de uso) dependem da receita da loja. Cabe ao Marlon definir.

- A regra de temperatura de manutenção a quente vem de fontes secundárias sobre a RDC 216/2004. As regras de transporte não foram confirmadas. Consulte o texto oficial e a vigilância sanitária do município.

- Fabricantes de caixas e de software vendem o que recomendam. Alegações como "cortou reclamações pela metade" não têm dado e não foram usadas.

- As pendências já abertas do projeto continuam valendo: teste da impressora térmica Bluetooth, backup fora da máquina, token do Anota Ai e dados de cardápio e fichas.

### Fontes

- [<u>PMQ: In Lehmann's Terms, 5 tips para um bom delivery</u>](https://www.pmq.com/5-tips-for-a-better-delco-pizza/)

- [<u>PMQ: Getting pizza dough balls into the cooler</u>](https://www.pmq.com/getting-pizza-dough-balls-into-the-cooler/)

- [<u>PMQ: Effective dough management</u>](https://www.pmq.com/effective-dough-management/)

- [<u>PMQ: How to prevent blown dough</u>](https://www.pmq.com/how-to-prevent-blown-dough/)

- [<u>Heckers Ceresota: Pizza dough</u>](https://www.heckersceresota.com/pizza-flour/d/)

- [<u>Pizza Today: Practical approaches to speed up your makeline</u>](https://pizzatoday.com/news/practical-approaches-to-speed-up-your-makeline/143592/)

- [<u>Speedline Solutions: Portion control in your pizzeria</u>](https://www.speedlinesolutions.com/blog/portion-control-reduce-inventory-costs-in-your-pizzeria)

- [<u>Foodtec: Pizza delivery performance, 4 metrics</u>](https://foodtecsolutions.com/blog/2019/09/12/pizza-delivery-performance-4-metrics-you-need-to-be-measuring/)

- [<u>Foodtec: Mastering pizza delivery, expectations and accuracy</u>](https://foodtecsolutions.com/blog/2025/08/12/mastering-pizza-delivery-its-about-expectations-and-accuracy-not-just-speed/)

- [<u>Slice: Why accurate delivery times are crucial</u>](https://slice.com/resources/why-accurate-delivery-times-are-crucial)

- [<u>Slice: Handling phone lines during peak hours</u>](https://slice.com/blog/handling-phone-lines-during-peak-hours-advice-for-your-staff/)

- [<u>Racklify: Designing pizza boxes for delivery</u>](https://racklify.com/encyclopedia/designing-pizza-boxes-for-delivery-venting-stacking-and-branding-tips/)

- [<u>Sebrae: E-book Como elaborar fichas técnicas</u>](https://sebrae.com.br/Sebrae/Portal Sebrae/Arquivos/E-book_Como_elaborar_fichas_técnicas.pdf)

- [<u>Sebraetec MG: Redução de desperdício na cozinha</u>](https://sebraetec.sebraemg.com.br/wp-content/uploads/2023/08/REDUCAO-DE-DESPERDICIO-NA-COZINHA.pdf)

- [<u>RDC 216/2004 (reprodução, para conferir o texto oficial)</u>](https://vigilanciasanitaria.prefeitura.rio/wp-content/uploads/sites/84/2023/05/RESOLUcaORDCN216ANVISA.pdf)
