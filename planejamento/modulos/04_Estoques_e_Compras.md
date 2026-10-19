# Detalhamento 04: Estoques e Compras

Versão 0.1, 19/10/2026. Rascunho para discussão, montado com o que Marlon já decidiu, com o plano macro e com boas práticas marcadas. Parte do [Plano Macro](../00_Plano_Macro.md), seção 4.3. Depende de [Núcleo e Vendas](01_Nucleo_e_Vendas.md), [Produção](02_Producao.md) e [Fechamento de Caixa](03_Fechamento_de_Caixa.md), todos aprovados.

**Critério de sucesso:** Marlon responde as perguntas da seção 6, corrige o desenho e diz "é assim". Só então o módulo vira v0.2 para aprovação.

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
| Pedido de compra | Do que falta ao pedido ao fornecedor |
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

### 6.2 Em aberto

| # | Pergunta | Minha recomendação |
|---|---|---|
| J1 | Quais são os locais de armazenamento (freezer, câmara fria, estoque seco, outros)? | Cadastrar os locais que existirem, nos parâmetros |
| J2 | Quantos itens aproximadamente (insumos, embalagens, bebidas, material de limpeza)? Há planilha ou lista hoje? | Carregar por planilha na primeira vez |
| J3 | Hoje existe contagem de estoque? Com que frequência (diária, semanal, mensal)? | Contagem rápida diária dos itens críticos e completa mensal |
| J4 | Quais itens têm validade que importa (queijo, molho, frios, bebida)? Controla lote? | Lote e validade só para os perecíveis marcados no item |
| J5 | Como o consumo é baixado: pela ficha técnica de cada pizza ao concluir o pedido, ou por contagem periódica, ou os dois? | Os dois: ficha técnica no dia a dia e inventário para corrigir a diferença |
| J6 | Há ficha técnica hoje (receita com gramas de cada insumo por sabor e tamanho)? Quem pode informar os valores? | Começar pelos sabores mais vendidos e crescer |
| J7 | Quem compra? Um comprador, o gerente ou o dono? Há aprovação do pedido de compra acima de um valor? | Pedido aprovado pelo gerente acima de um valor nos parâmetros |
| J8 | Como compra: fornecedores fixos com pedido por WhatsApp ou telefone, ou cotação entre vários? Quantos fornecedores? | Pedido registrado por fornecedor, cotação só quando você quiser |
| J9 | Como chega a nota (papel, XML por e-mail)? Quer importar o XML da NF-e ou digitar? | Digitar no começo e importar XML depois |
| J10 | Compras são pagas à vista, a prazo ou ambos? Quem confere o recebimento? | Registrar prazo e forma por fornecedor e o conferente por entrega |
| J11 | Compra de dinheiro do caixa (feira, mercado) para reposição urgente entra aqui como compra? | Sim, como compra sem pedido, ligada à sangria do caixa |
| J12 | Há refeição de funcionário ou consumo interno que deva sair do estoque? | Sim, como saída "consumo interno", com valor para o RH e Custos |
| J13 | O estoque mínimo e o ponto de pedido: você define por item ou quer sugestão pelo consumo médio? | Sugestão pelo consumo médio, com você aprovando |
| J14 | O preço de custo do insumo é o da última compra ou a média? | Custo médio móvel, com o último preço visível |

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Tabelas finais e regras de cálculo do custo médio.
- Importação de XML de NF-e (pesquisar quando chegar a hora).
- Carga da ficha técnica: depende da planilha que Marlon vai enviar.
