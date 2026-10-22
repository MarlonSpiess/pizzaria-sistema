# Desenho 02: produto com insumos e etapas de produção

Versão 0.1, 22/10/2026. Rascunho para Marlon. Pedido: usar o PCP (fontes em C:\Temp\PCP, publicado em pcp.allexcorp.com.br) como base para o cadastro de produtos (pizza Grande, Broto e calzone) ter insumos e etapas de produção. Li os fontes do PCP (migrations 001 e 016 a 021, serviços de MRP, custo, produção, apontamento e capacidade, CLAUDE.md, a análise de melhorias e a revisão das fichas). Não abri o site publicado; o que vale aqui é o código.

Marcações: **[Decisão]** é de Marlon; **[PCP]** vem do PCP; **[Prática]** é boa prática; **[Suposição]** é minha e precisa de confirmação.

---

## 1. Como o PCP resolve (o que aproveitar)

| Conceito no PCP | O que faz | Serve para a pizzaria? |
|---|---|---|
| `produto_materiais` | Insumo e quantidade por unidade do produto, com `perda_pct` | Sim, é a ficha técnica |
| `produto_roteiro` | Etapas do produto: setor, ordem, tempo padrão, recurso e setup | Sim, as etapas; setup não |
| `setores` com `custo_hora` | Mão de obra do custo = horas da etapa x custo da hora do setor | Sim, com o custo da função vindo do RH |
| `recursos` | Máquina com capacidade própria | Sim, para o forno (2 min, 4 a 6 pizzas) |
| `produto_componentes` | Produto feito de outros produtos, em vários níveis, sem ciclo | Sim, a massa aberta é componente da pizza e do calzone |
| `produto_pecas` com roteiro e material próprios | Nível intermediário de peças | Não, pizza não tem peças |
| MRP, `custo_produto`, capacidade | Necessidade de material, custo e carga | Sim, como Estoques, Custos e entrega calculada |
| Apontamento por etiqueta, idempotente | Lê a etiqueta e conta uma vez | Parcial: nossa unidade é a pizza e o toque é no tablet, mas a ideia de não contar duas vezes serve |
| Tela de qualidade de dados | Avisa ficha sem material, sem roteiro, custo acima do preço | Sim, desde o começo |

## 2. A lição mais cara do PCP

A revisão das fichas do PCP (`docs/revisao_fichas_tecnicas.md`) concluiu que as fichas carregadas **não eram engenharia real**: consumos de exemplo, 27 de 40 produtos com custo de material acima do preço, mão de obra zerada. O sistema calculava certo, o dado é que estava errado, e por isso custo, compras e baixa de estoque perderam o valor.

Regra para nós **[Prática]**: **só entra ficha com dado real**, vinda da planilha de Marlon, sem valores de exemplo. Produto sem ficha aparece como "sem ficha" e não como custo zero.

## 3. O que o plano e o projeto atuais dizem

- Plano Macro v1.0: a ficha técnica é do Núcleo, mantida por Custos e Produção, e só é preenchida na etapa 2 (Estoques).
- Desenho técnico 01 (4.2): `produto` e `preco_produto` existem; **não há ficha técnica nem etapas** na fatia 1B.
- Produção v0.3: as etapas existem como situações da pizza (na lista, em montagem, no forno, acabada) e são **iguais para todo produto**; os tempos vêm do histórico.
- Estoques v0.3: a baixa usa a ficha, que Marlon enviará em planilha (meia Grande ou Broto, sabor, ingrediente e quantidade).

**Avaliação.** Vale antecipar o **cadastro** da ficha e das etapas (sem baixa, sem custo), porque a planilha já existe, o produto fica completo de uma vez e Produção e Estoques nascem com o dado pronto. A baixa de estoque e o custo continuam nas etapas 2 e 5.

## 4. Proposta

### 4.1 Insumos (ficha técnica)

- Tabela `item` mínima (insumo, preparo, embalagem, revenda, material de consumo; unidade). Saldo e compra só chegam em Estoques **[Plano Macro]**.
- `ficha_insumo`: produto (ou adicional, ou preparo), item, quantidade, perda % opcional, vigência (só inserção, como o preço).
- **Base da ficha = meia Grande ou Broto** (como a planilha de Marlon) **[Suposição]**: Broto consome 1x; Grande de um sabor, 2x; Grande de dois sabores, uma vez a ficha de cada sabor. Assim cada sabor tem uma ficha só.
- Borda e adicional têm ficha própria, por tamanho.
- Bebida e acompanhamento: ficha de um item (revenda), 1 para 1.

### 4.2 Massa como componente

- A massa é o único preparo em lote **[Decisão H9]**. Ela vira um **preparo** com ficha própria (farinha, água, fermento, sal...), em duas formas: massa aberta Grande e Broto, e massa com borda.
- A pizza e o calzone consomem **massa aberta**, não farinha. Isso evita baixar a farinha duas vezes: a farinha é baixada no lote de massa (fase 1) **[Decisão H12]**.

### 4.3 Etapas de produção

- Cadastro de **etapas** (massa fase 1, massa fase 2, montagem, forno, acabamento), com ordem, **função** responsável (massa, pizzaiolo, acabamento) e recurso opcional (forno).
- `produto_etapa`: quais etapas o produto percorre e o **tempo padrão** de cada uma. Por padrão a etapa é do **tipo** de produto (pizza, calzone); sabor só ganha exceção se houver motivo.
- Os tempos alimentam a entrega calculada **[Decisão H4]** e, depois, o custo de mão de obra (custo da hora da função, de RH).
- O forno é um **recurso** com capacidade (tempo e pizzas por vez), já previsto nos parâmetros **[Decisão H7]**.

### 4.4 Fora desta proposta

Peças, setup por lote, pedido para OP agrupada por lote mínimo e leitura de QR: não se aplicam à pizzaria hoje.

## 5. Efeito nas fatias

| Fatia | Mudança |
|---|---|
| 1B (feita) | Nada se perde. Entra uma extensão "1B2" no cadastro: `item`, `ficha_insumo`, `etapa`, `produto_etapa`, telas e carga da planilha, sem baixa |
| 1C Vendas | Sem mudança |
| 1D Produção | Usa as etapas e os tempos cadastrados em vez de fixos no código |
| Etapa 2 Estoques | Baixa pela ficha que já estará carregada |
| Custos | Material + mão de obra por produto, no estilo `custo_produto` do PCP |

## 6. Perguntas

- **U1.** A ficha da planilha vale para meia Grande ou Broto, e a Grande consome o dobro? (recomendo: sim)
- **U2.** A massa vira preparo com ficha própria, e a pizza consome massa aberta em vez de farinha? (recomendo: sim)
- **U3.** As etapas são por tipo de produto (pizza, calzone), com exceção por sabor só quando houver? (recomendo: sim)
- **U4.** O tempo de cada etapa começa digitado por você e depois passa a ser a média real medida? (recomendo: sim)
- **U5.** O calzone percorre as mesmas etapas da pizza, ou tem etapas ou tempos diferentes? Quais?
- **U6.** Borda e cada adicional têm insumos próprios por tamanho (queijo da borda, por exemplo)? (recomendo: sim)
- **U7.** A embalagem (caixa, etiqueta) entra na ficha por tamanho? (recomendo: sim)
- **U8.** Perda % por insumo na ficha, opcional e vazia no começo, além das perdas registradas na produção? (recomendo: sim)
- **U9.** Posso antecipar só o **cadastro** da ficha e das etapas (sem baixa de estoque nem custo) como extensão 1B2, antes da Vendas? (recomendo: sim)
- **U10.** Quando você envia a planilha da ficha técnica? Ela é a condição para carregar dado real.
