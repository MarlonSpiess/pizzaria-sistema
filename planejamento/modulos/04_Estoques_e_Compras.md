# Detalhamento 04: Estoques e Compras

Versão 0.3, 20/10/2026. Consolidada com as respostas J1 a J14 de Marlon e com a revisão da J8 (lista de compras e cotação) pedida em 20/10/2026. A v0.2 foi aprovada em 19/10/2026; **a v0.3 aguarda nova aprovação, só na parte de Compras (3.2, J8 e perguntas J8a a J8e).** Parte do [Plano Macro](../00_Plano_Macro.md), seção 4.3. Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), [Produção](02_Producao.md) e [Fechamento de Caixa](03_Fechamento_de_Caixa.md), todos aprovados.

**Critério de sucesso:** Marlon lê o desenho e as respostas da seção 6 e diz "aprovado" ou aponta o que corrigir.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Objetivo do módulo: saber o que existe, o que foi consumido, o que se perdeu e o que precisa ser comprado **[Plano Macro]**.
- **Material de uso e consumo** é uma classe de item em Estoques e Compras **[Decisão E1]**.
- O cadastro de itens (insumos, preparos e produtos de venda) e a ficha técnica são do Núcleo; a ficha só é preenchida agora **[Plano Macro]**.
- Produção baixa a farinha e os demais insumos da massa pela ficha técnica; o operador conta o estoque de massa aberta **[Decisão H12]**.
- Perdas de massa e de pizza pronta chegam com motivo; falta de insumo ao retroceder uma pizza avisa Estoques **[Decisão H5 e H9]**.
- Não há outros preparos em lote além da massa **[Decisão H9]**.
- Uma loja, um banco por loja, com o identificador da loja em todo registro **[Decisão P2]**.
- Dinheiro em NUMERIC, login pessoal, auditoria só de inserção, exclusão lógica **[Kit]**.

---

## 2. Objetivo

Manter o saldo real de cada item, registrar entradas e saídas com origem e responsável, apontar o que falta e o que vence, e entregar custo e consumo a Custos, Contas a Pagar e BI.

---

## 3. Submódulos propostos

### 3.1 Estoques **[Prática, a confirmar]**

| Submódulo | O que faz |
|---|---|
| Itens e classes | Insumo (queijo, farinha), embalagem, bebida revendida e **material de uso e consumo** (limpeza, descartáveis) **[Decisão E1]**. Unidade de medida e unidade de compra por item |
| Locais | Onde o item fica (freezer, câmara, estoque seco) |
| Saldos | Quantidade por item e local, calculada dos movimentos; nunca digitada direto |
| Movimentos | Entrada (compra), saída por venda (ficha técnica), saída por produção, perda, consumo interno, ajuste de inventário. Cada um com quem, quando e motivo; só inserção |
| Inventário | Contagem periódica; a diferença vira ajuste com motivo |
| Validade e lote | Controle por lote, saída pelo mais antigo (PEPS) |
| Mínimo e ponto de pedido | Alerta quando o saldo chega ao mínimo |

### 3.2 Compras **[Prática, a confirmar]**

| Submódulo | O que faz |
|---|---|
| Fornecedores | Cadastro com contato, prazo e forma de pagamento |
| Lista de necessidades | O sistema reúne tudo que precisa ser comprado: itens abaixo do mínimo ou do ponto de pedido, itens perto de vencer e a falta apontada pela Produção. O operador pode **acrescentar outros itens** à mão e **remover ou ajustar** quantidades, sempre com motivo para o que o sistema sugeriu e saiu |
| Pedido de cotação | Da lista de necessidades gera uma **lista por fornecedor**, para pedir preço. Registra preço, prazo e condição que cada fornecedor respondeu, com data |
| Mapa de cotação | Compara, item a item, os preços dos fornecedores e o último preço pago, com os últimos 3 preços do item (J14) |
| Lista de compras definitiva | O comprador escolhe o fornecedor de cada item (ou o mapa sugere o mais barato, ele confirma) e o sistema fecha a lista; quem tem poder de aprovação (J7) aprova. Dela saem os pedidos de compra |
| Pedido de compra | Um por fornecedor, gerado da lista definitiva ou digitado direto |
| Recebimento | Conferência da entrega contra o pedido; diferenças registradas |
| Entrada da nota | Valores e quantidades da nota entram nos movimentos e geram o título a pagar |
| Histórico de preço | Preço por insumo e fornecedor ao longo do tempo |

---

## 4. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Núcleo | Itens, unidades e ficha técnica | Núcleo para Estoques |
| Vendas | Consumo de insumos pela ficha técnica, ao concluir o pedido **[Suposição]** | Vendas para Estoques |
| Produção | Consumo, perda de massa e de pizza, falta de insumo | Produção para Estoques |
| Contas a Pagar | Títulos das compras | Estoques para Contas |
| Custos | Custo médio dos insumos, estoque inicial e final para o CMV, perdas | Estoques para Custos |
| Imobilizado | Compras que são bens | Estoques para Imobilizado |
| BI | Giro, ruptura, perdas, variação de preço | Estoques para BI |

Cada ligação tem forma manual, para o módulo funcionar sozinho **[Prática]**.

**Por que é central.** O CMV pela fórmula de estoque é `CMV = Estoque Inicial + Compras - Estoque Final` (Plano Macro, fonte 4). Sem estoque confiável não existe CMV confiável.

---

## 5. Pontos que o fluxo de Produção deixou para cá

1. **Baixa pela ficha técnica:** exige ficha técnica de pizza (sabor por tamanho), de calzone, de bebida e de adicionais. Hoje nenhuma existe.
2. **Falta de insumo ao retroceder:** gera um aviso. Falta definir se vira alerta ou lançamento de ruptura.
3. **Massa aberta e massa com borda:** são produtos intermediários com saldo próprio, contados pelo operador, e precisam de item e unidade no cadastro.
4. **Bebida e acompanhamento** entram no cardápio como produto: são item de revenda com saldo.

---

## 6. Perguntas

### 6.1 Respondidas por Marlon em 19/10/2026

- **J3:** contagem **diária dos itens críticos** e **completa mensal** **[Decisão]**.
- **J5:** o consumo é baixado **pelos dois caminhos**: ficha técnica no dia a dia e inventário. O módulo **deve ter a rotina de inventário e de ajuste de estoque** **[Decisão]**.
- **J6:** **já existe uma planilha com a ficha técnica** **[Decisão]**. Falta Marlon enviá-la para eu ler o formato e planejar a carga.
- **J9:** a nota fiscal é **digitada no começo**; a importação de XML fica para depois **[Decisão]**.

Formato da ficha técnica (Marlon, 19/10/2026): a planilha traz, para **1/2 Grande ou Broto**, o **nome do sabor** e a lista de **ingrediente e quantidade**; pode vir como planilha de Excel. Leitura minha: a quantidade vale para meia Grande, que é igual a uma Broto; uma Grande de um sabor consome o dobro, e uma Grande de dois sabores consome a quantidade de cada sabor **[Suposição, a confirmar]**.

### 6.2 Respondidas em 19/10/2026

- **J1:** locais de armazenamento: **todos os sugeridos** (freezer, câmara fria e estoque seco) **[Decisão]**.
- **J2:** tamanho do cadastro **[Decisão]**:
  - Cardápio: 50 sabores de pizza, 10 calzones, 10 bebidas e 4 bordas (podem crescer).
  - Insumos em estoque: cerca de 40, incluindo os da massa; os ingredientes de montagem são de 25 a 30.
  - Material de uso e consumo (limpeza e outros): cerca de 100 itens.
- **J4:** lote e validade para **todos os insumos de pizzas e calzones, inclusive as massas** **[Decisão]**.
- **J7:** compra e aprovação do pedido de compra ficam com o **administrador do sistema, o proprietário, o gerente e o subgerente** **[Decisão]**. O perfil **subgerente** é novo (ver seção 7).
- **J8 (revisada em 20/10/2026):** o sistema monta a **lista de necessidades**, o operador pode **inserir outros itens**, e dela saem **listas de cotação por fornecedor**, o **controle das cotações** e a **lista de compras definitiva**, que gera os pedidos por fornecedor **[Decisão]**. Substitui a regra anterior (pedido por fornecedor e cotação opcional). Detalhes em 6.3.
- **J10:** prazo e forma de pagamento por fornecedor; conferente registrado por entrega **[Decisão]**.
- **J11:** compra urgente paga com dinheiro do caixa entra como **compra sem pedido, ligada à sangria** **[Decisão]**.
- **J12:** refeição de funcionário e consumo interno saem do estoque como **"consumo interno"**, com valor para **Custos** (não para o RH) **[Decisão]**. Em Vendas, funcionário compra com **preço especial com desconto e limite de quantidade** (ver seção 7).
- **J13:** estoque mínimo por **sugestão pelo consumo médio**, com Marlon aprovando **[Decisão]**.
- **J14:** custo por **custo médio móvel**, com os **últimos 3 preços visíveis**, para enxergar tendência e sazonalidade **[Decisão]**.

Todas as perguntas do módulo estão respondidas.

---

### 6.3 Perguntas da revisão da J8 (a responder)

- **J8a:** a cotação é sempre obrigatória ou o comprador pode pular e ir direto da necessidade ao pedido, para itens do dia a dia? (recomendo: pode pular, escolhendo "fornecedor habitual" por item)
- **J8b:** o item avulso que o operador insere pode ser algo fora do cadastro (ex.: compra pontual), ou só item já cadastrado? (recomendo: só cadastrado, com cadastro rápido de item novo pelo gerente)
- **J8c:** a cotação é registrada à mão (telefone, WhatsApp) ou o sistema deve enviar a lista ao fornecedor? (recomendo: à mão no começo; no beta só gerar a lista para copiar ou imprimir)
- **J8d:** um item pode ser dividido entre dois fornecedores na lista definitiva? (recomendo: sim)
- **J8e:** quem aprova a lista definitiva: acima de um valor nos parâmetros, o gerente ou subgerente; abaixo, o próprio comprador? (recomendo: sim, valor de aprovação já previsto na seção 7)

---

## 7. Efeitos em outros módulos (a incorporar)

- **Núcleo:** novo perfil **subgerente**, com poder de compra e aprovação de pedido de compra. Permissões: as do gerente, exceto aprovar diferença de caixa **[Decisão, 19/10/2026]**.
- **Vendas:** preço de funcionário com desconto e limite de quantidade, por funcionário e por período. Regra decidida em 19/10/2026: funcionário cadastrado, limite de quantidade por dia e percentual de desconto nos parâmetros **[Decisão]**.
- **Custos:** recebe o valor do consumo interno e o custo médio dos insumos.
- **Parâmetros da loja:** valor de aprovação de compra; locais de armazenamento.

---

## 8. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de cálculo do custo médio.
- Importação de XML de NF-e (pesquisar quando chegar a hora).
- Carga da ficha técnica: depende da planilha que Marlon vai enviar.
