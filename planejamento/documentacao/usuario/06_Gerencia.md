# Manual do Usuário: Gerência (gerente e subgerente)

Versão 2.0, 04/11/2026. Leia antes o [manual comum](00_Comum_a_Todos.md). Para a operação de balcão e caixa, use também os manuais do [atendente](04_Atendente.md) e do [caixa](05_Caixa.md).

**As suas áreas:** 🍕 Produção, 🧾 Vendas e 🏢 Administrativo. Troque de área no seletor no alto do menu lateral (o trilho de ícones). Ao entrar, o sistema abre na última área que você usou.

## 1. O que só a gerência faz, e os limites

| Ação | Gerente | Subgerente |
|---|---|---|
| Autorizar desconto acima do limite do atendente (login e senha na hora) | Sim, até o próprio limite | Sim, até o próprio limite |
| Autorizar cancelamento de pedido pago feito pelo atendente | Sim | Sim |
| Autorizar sangria acima do limite (e lançar sangria sem pedir autorização) | Sim | **Não** |
| Aprovar diferença de caixa acima da tolerância (se não fez a contagem) | Sim | **Não** |
| Aprovar no RH (exemplo: hora extra), até o limite de hora extra do mês e lançamentos de até 62 dias | Sim | **Não** |
| Aprovar lista de compras acima do valor do parâmetro | Sim | Sim |
| Aprovar título a pagar ou ordem de serviço acima do limite; dar baixa em bem (sempre) | Não (administrador ou proprietário) | Não |
| Editar parâmetros, gerir usuários, ver salários e folha | Não (administrador ou proprietário) | Não |
| Ativar canal, ligar "aceitar sozinho", editar o mapa de produtos | Não (administrador ou proprietário) | Não |

## 2. Produção

Você vê todas as telas da cozinha: **Massa**, **Montagem**, **Forno**, **Acabamento**, **Despacho**, e mais duas que são só suas:

- **Andamento:** todos os pedidos em aberto, com cliente, tipo, pizzas acabadas, situação e entrega calculada. É a visão geral da cozinha.
- **Motivos:** motivos de retrocesso e de perda. Na primeira vez, toque em "Criar os motivos combinados". Motivo de retrocesso marcado como "Avisa Estoques" indica que o retrocesso foi por falta de insumo. Inative um motivo em vez de apagar.

**Montagem errada e falta de ingrediente:** o pizzaiolo tem os botões Montagem errada no sabor, Problemas no formato/esteira e Sem ingredientes. A pizza errada vira **avulsa** (vendida pela recepção no Novo pedido, cartão "Pizzas avulsas prontas", com as características do item de origem, preço do cardápio e as regras de desconto; ou descartada no Acabamento com motivo); a falta de ingrediente manda a pizza para o fim da lista. Tudo aparece no cartão **Avisos da Produção**, no alto das telas da cozinha; toque em **Resolver** quando tomar a providência (exemplo: repor o ingrediente ou fechar a venda do sabor). Para "Sem ingredientes" funcionar, precisa existir em Motivos um motivo de retrocesso que avisa o estoque (exemplo: Falta de insumo). O BI de Produção mostra avulsas geradas, vendidas, descartadas e abertas. Estoque: apontar o erro não baixa nada; a venda da avulsa baixa a ficha inteira como saída de venda; o descarte baixa como perda.

A estimativa de entrega usa os parâmetros de produção (minutos de montagem e de acabamento, pizzaiolos ativos, tempo de forno, deslocamento). Mantenha-os atualizados para a hora de entrega ficar certa.

## 3. Vendas

Além de tudo o que o atendente faz:

- **Pedidos do dia:** você pode avançar o pedido para qualquer situação seguinte à mão (o atendente só marca despachado ou retirado).
- **Canais:** uma aba por canal (Anota Ai; iFood aparece desativado).
  - **Fila de entrada:** pedidos que chegaram do canal, com há quantos minutos esperam. A partir de 10 minutos aparecem em destaque, porque o Anota Ai cancela sozinho o pedido não aceito em 15 minutos.
  - Estados: na fila, importando, importada, **bloqueada** (a loja não pode produzir, ou a importação falhou 3 vezes) e recusada.
  - Pedido bloqueado: escolha **Tentar de novo** ou **Recusar** (com motivo).
  - **Aceitar** um pedido à mão ainda não tem botão: depende da chamada de aceitar da API do Anota Ai. Até lá, aceite pelo aplicativo do Anota Ai.
  - **Mapa de produtos:** consulta do ID externo de cada produto no canal. Sem ID externo, um pedido com esse produto não é aceito sozinho.
  - Hoje a tela avisa: "Integração ainda não conectada: falta o token do canal".
- **Loja aberta** (no topo de Vendas > Canais): chave manual. Toque para ligar quando a loja já pode receber pedidos e desligue ao encerrar; ela **não muda sozinha**. Sem loja aberta, nenhum pedido do canal é aceito sozinho.
- **Fechar vendas por ingrediente** (em Administrativo > Estoque > Alertas, seção 4): vale para o balcão (o sabor não pode ser vendido) e para o canal (não aceita sozinho e prepara a pausa no Anota Ai, que depende da API).

## 4. Administrativo

| Menu | Para que serve |
|---|---|
| **Painel** | Boas-vindas e backup (ver o último e "Fazer backup agora"). Os números do dia ficam em BI > Painel do dia |
| **Cardápio** | Sabores de pizza, preços por categoria (Tradicional, Especial e outras), bordas e adicionais, calzones, bebidas e outros, simulador de preço. É o cardápio único da loja. Todo preço novo guarda o histórico |
| **Fichas e etapas** | Fichas técnicas (quanto de cada insumo vai em cada produto, por tamanho), itens (insumos e preparos), etapas de produção, e "O que falta" (produtos sem ficha) |
| **Estoque** | Saldos, lançar movimento (perda, consumo interno, estoque inicial, transferência), inventário (contar, conferir, fechar; é por ele que se ajusta o saldo), alertas, locais |
| **Compras** | Lista de compras (necessidades, itens avulsos, cotação por fornecedor, definir e aprovar), pedidos de compra, recebimento com a nota, fornecedores |
| **Contas** | Fluxo de caixa de 30 dias (7 em destaque), a pagar, a receber, lançar título, conciliação com o extrato, cadastros (contas bancárias, tipos de despesa, canais de repasse, despesas recorrentes) |
| **BI** | Painel do dia, DRE por competência, lucratividade por sabor e categoria, produção; exportação em CSV |
| **Custos** | Custo dos produtos pela ficha técnica, CMV teórico e real do mês (fechamento), resultado do mês, fator de correção por insumo |
| **Imobilizado** | Alertas de manutenção, bens, ordens de serviço (abrir, iniciar, peças, fechar), plano de manutenção, leituras, inventário de bens, categorias |
| **RH** | Equipe, escala, ponto e banco de horas (você lança o ponto), ausências e documentos, cadastros (funções e escalas) |
| **Parâmetros** | Consulta dos parâmetros da loja (só administrador e proprietário editam) |
| **Auditoria** | Quem fez o quê e quando, em todo o sistema |

### Como o estoque se move sozinho

- A **pizza acabada** baixa os insumos pela ficha técnica; a **pizza perdida** baixa como perda o que já tinha entrado na montagem.
- **Pizza perdida na montagem:** a gerência também vê o cartão **Pizzas perdidas para refazer** na tela do Acabamento e pode tocar em **Refazer** (motivo obrigatório). A pizza nova entra na frente da fila; o motivo da refação fica na auditoria.
- **Bebidas e acompanhamentos** saem do estoque quando o pedido fica acabado.
- A baixa automática **nunca trava a produção**. Se faltar saldo, o estoque fica **negativo**, para a falta aparecer. Produto sem ficha gera uma pendência em Estoque > Alertas.
- **Alerta de estoque** (Estoque > Alertas, e alerta no BI): ingrediente **NEGATIVO**, **ZERADO**, **repor** (chegou ao ponto de pedido) ou **abaixo do mínimo** (estoque mínimo do cadastro), do mais grave para o menos grave. Vale para qualquer item com estoque mínimo, não só ingrediente. Trate na loja (conferir, repor) e, se for o caso, ajuste o saldo por um Inventário.
- **Fechar vendas dos sabores:** no alerta, toque no botão do item. O sistema mostra os sabores afetados (exemplo: ovo fecha Portuguesa, Paulista, Baiana) e pede confirmação. **O que isso faz hoje:** o balcão não consegue vender esses sabores (aparecem como VENDA FECHADA e o sistema recusa o pedido), pedidos do canal com eles não são aceitos sozinhos e a pausa no Anota Ai fica preparada (depende da API). Para reabrir, use **Reabrir vendas** no cartão **Vendas fechadas agora**, no topo de Estoque > Alertas; o cartão continua lá mesmo depois que o item é reposto e sai do alerta. Perda e consumo interno também podem deixar o saldo negativo; transferência entre locais não.

Mantenha o **estoque mínimo** de cada ingrediente preenchido em Estoque > Saldos (configuração do item). Sem ele, o alerta de "baixo" não funciona.

## 5. Rotina sugerida

| Quando | O quê |
|---|---|
| Abertura | Conferir caixa aberto, ligar loja aberta, ver alertas de estoque (fechar sabores se preciso) e de manutenção |
| Pico | Andamento da cozinha, fila de entrada do canal (prazo de 15 minutos), autorizações |
| Fechamento | Desligar loja aberta, acerto de todos os entregadores, contagem cega, aprovar diferença (gerente), CF dos pedidos, backup |
| Semanal | Lista de compras, inventário, ponto da equipe |
| Mensal | Fechamento do CMV, DRE, resultado do mês, folha gerencial (administrador) |
