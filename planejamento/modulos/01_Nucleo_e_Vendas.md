# Detalhamento 01: Núcleo e Vendas

Versão 0.2, 16/10/2026. Inclui as respostas B1 a B10 de Marlon. Rascunho para discussão. Parte do [Plano Macro v0.2](../00_Plano_Macro.md).

**Critério de sucesso:** ao fim deste documento, Marlon consegue dizer "é isso" ou "falta isto" sobre o que o Núcleo e o módulo de Vendas fazem, quais dados guardam e como se ligam aos outros módulos. Telas desenhadas e tabelas finais vêm depois da sua aprovação.

Marcações: **[Decisão]** é de Marlon; **[Kit]** vem do Kit Aplicação Web; **[Fonte]** tem fonte pesquisada (seção 7); **[Prática]** é boa prática de sistemas de gestão, sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Vendas pelo **balcão (neste sistema)** e pelo **Anota Ai**. Pedido local é digitado só neste sistema **[Decisão]**.
- O cupom fiscal (CF) é emitido por software de terceiro. Hoje a venda é **digitada duas vezes**; no futuro este sistema emitirá o CF **[Decisão]**.
- Uma loja por banco; um futuro aplicativo central lerá os bancos de todas as lojas **[Decisão]**.
- Regime tributário é parâmetro da loja **[Decisão]**.
- 2 PCs na recepção, ambos ligados ao Anota Ai, e 4 tablets na produção **[Decisão]**.
- Roda local, com espelho na nuvem previsto para depois **[Decisão]**. Stack do kit: FastAPI, PostgreSQL, HTML **[Decisão]**.
- Ainda não há token nem contato com o Anota Ai **[Decisão]**.
- Tamanhos Grande e Broto; a Grande pode ter 2 sabores; há bordas e adicionais **[Decisão B1]**.
- O preço é o mesmo no balcão e no Anota Ai, mas varia por categoria (Tradicionais e Especiais) e por tamanho **[Decisão B2]**.
- Só retirada e entrega, sem consumo no salão **[Decisão B3]**.
- Taxa de entrega variável; entregadores são terceiros **[Decisão B4]**.
- Pagamentos: dinheiro, Pix, cartão de crédito e cartão de débito **[Decisão B5]**.
- Desconto e cancelamento seguem a sugestão (atendente até um limite, gerente acima, motivo obrigatório); o limite é um percentual nos parâmetros do sistema **[Decisão B6]**.
- Número do pedido reinicia por dia; o código interno deve chegar ao Anota Ai por API e ao cliente por WhatsApp "ou algo similar" **[Decisão B7]**.
- Cadastro de cliente na primeira compra, com nome, telefone e endereço **[Decisão B8]**.
- Login pessoal e intransferível **[Decisão B9]**.
- Só o administrador geral e o desenvolvedor pedem acesso ao Anota Ai **[Decisão B10]**.

---

## 2. Núcleo

**Objetivo.** Dar a todos os módulos a mesma base de usuários, permissões, auditoria e cadastros, para que cada fato seja registrado uma só vez.

### 2.1 Submódulos

| Submódulo | Para quê | Origem |
|---|---|---|
| Usuários e perfis | Quem entra, o que pode fazer | [Kit] |
| Segurança de acesso | Login, sessão, bloqueio de tentativas | [Kit] |
| Auditoria | Quem registrou ou alterou cada fato de negócio | [Kit] |
| Parâmetros da loja | Identificador da loja, nome, regime tributário, fuso, formas de pagamento aceitas, limite de desconto por perfil (em %) | [Decisão] e [Prática] |
| Cadastro de itens | Insumos, preparos e produtos de venda | Plano macro, seção 2.2 |
| Cardápio e preços | O que se vende, em que tamanho, por qual preço, em qual canal | [Prática] |
| Pessoas | Clientes, fornecedores, funcionários, entregadores | Plano macro, seção 2.2 |
| Saúde do sistema | Verificação de que o servidor e o banco respondem | [Kit] |

A ficha técnica (receita de cada produto) é cadastro do Núcleo, mas só é preenchida quando os módulos de Custos e Estoques forem detalhados. Vendas não depende dela.

### 2.2 Regras de segurança herdadas do kit

- Senha com bcrypt; login com a mesma resposta e o mesmo tempo para usuário inexistente e senha errada; bloqueio após 5 falhas em 15 minutos [Kit, Manual Técnico 6.2].
- Sessão guardada em tabela, token armazenado como SHA-256, sessão encerrada ao trocar senha ou desativar usuário [Kit, 6.3].
- Perfil sempre lido do cadastro atual, negando por padrão o que não está liberado [Kit, 6.4].
- Toda entrada validada por schema; SQL só parametrizado; texto de usuário nunca vira HTML sem escape [Kit, seções 1, 7 e 10.2].
- Segredos (senha do banco, token do Anota Ai) só em variável de ambiente [Kit, 1].
- Toda escrita de negócio registra o usuário; tabela de auditoria aceita só inserção [Kit, 7].
- Exclusão lógica: nada de apagar pedido ou pagamento [Prática].

### 2.3 Perfis propostos [Suposição]

| Perfil | Pode |
|---|---|
| Administrador | Tudo, inclusive usuários e parâmetros |
| Gerente | Vendas, cancelamentos e descontos acima do limite, relatórios |
| Atendente (recepção) | Criar e consultar pedidos, receber pagamento |
| Estação (tablet da produção) | Ver e avançar pedidos da sua estação; sem acesso a valores |

---

## 3. Vendas

**Objetivo.** Registrar toda venda, de qualquer canal, uma única vez, com itens, valores, forma de pagamento e situação, e entregá-la pronta para Produção, Estoques, Fechamento de Caixa e Contas a Receber.

### 3.1 Fluxo de um pedido

1. **Entrada.** O pedido nasce no balcão (digitado por um atendente) ou chega do Anota Ai.
2. **Conferência.** O sistema valida que todo item existe no cardápio e tem preço. O manual de integração do parceiro Teknisa mostra que o Anota Ai recusa pedido com produto inexistente ou preço zerado [Fonte 1]; adotamos a mesma regra, com aviso ao atendente em vez de e-mail [Suposição].
3. **Confirmação.** O pedido ganha número e fica "recebido". Neste ponto gera a OP para a Produção.
4. **Pagamento.** Registrado na entrada (online) ou na entrega/retirada (dinheiro, cartão, Pix).
5. **Conclusão.** Entregue ou retirado. Fim do fluxo de Vendas.
6. **Cancelamento.** Possível até a conclusão, com motivo obrigatório e usuário registrado; pedido cancelado nunca é apagado.

### 3.2 Canais

| Canal | Como entra | Situação |
|---|---|---|
| Balcão | Atendente digita no sistema (2 PCs) | Definido |
| Anota Ai | Integração; token e ID da loja fornecidos pelo Anota Ai [Fonte 1] | Bloqueado: sem token nem contato |

**Proposta para destravar o Anota Ai sem esperar o token [Prática].** Definir um formato interno de pedido, igual para qualquer canal. O balcão já grava nesse formato. Quando houver token, só se escreve o "adaptador" que converte o pedido do Anota Ai para esse formato. Enquanto isso, o módulo funciona completo só com o balcão, e podemos testar o adaptador com um pedido de exemplo.

**Receber o Anota Ai num ponto só.** Como os dois PCs ficam ligados ao Anota Ai, o recebimento fica no servidor da loja; os dois PCs veem a mesma fila. Assim o mesmo pedido não entra duas vezes.

### 3.3 Dados guardados (candidatos)

| Registro | O que guarda |
|---|---|
| Pedido | Número, loja, canal, data e hora, cliente, tipo (entrega ou retirada), situação, totais, usuário |
| Item do pedido | Produto, tamanho/variação, quantidade, preço na hora da venda, observações |
| Observação de item | Tipo: acréscimo, retirada ou observação livre (os três tipos que o Anota Ai usa, segundo [Fonte 1]) |
| Pagamento | Forma, valor, situação, troco; no caso de pagamento online, o código externo com prefixo ONLINE_ ou OFFLINE_ [Fonte 1] |
| Cliente e endereço | Nome, telefone, endereço de entrega |
| Entrega | Entregador, taxa, saída e retorno (detalhes no módulo de Produção) |
| Cancelamento | Motivo, usuário, momento |
| Código externo | Identificador do pedido, do produto e da forma de pagamento no Anota Ai, para ligar os dois lados |

**Cardápio e preço (B1 e B2).**

- Produto de venda: pizza, com **tamanho** (Grande ou Broto) e **categoria** (Tradicionais ou Especiais). O preço base vem da combinação categoria e tamanho, igual no balcão e no Anota Ai.
- A pizza **Grande** aceita 2 sabores; a Broto, 1 sabor [Decisão B1; que a Broto aceite só 1 é suposição minha].
- **Borda** e **adicional** são itens cobrados à parte, com preço próprio.
- Preço por canal fica fora do início: como o preço é o mesmo, basta uma tabela de preços; se algum dia mudar, cria-se a segunda tabela [Prática].
- Falta a lista de sabores por categoria e os preços (pergunta C1) e a regra de preço da pizza de 2 sabores (C2).

Regras de dado: preço do item é **copiado** para o pedido (mudar o cardápio não altera venda antiga); dinheiro em `NUMERIC`; data e hora geradas pelo servidor, no fuso America/Sao_Paulo; cada registro leva o identificador da loja [Kit, 5.4] e [Decisão].

### 3.4 Digitação dupla do cupom fiscal

Hoje o atendente digita a mesma venda no nosso sistema e no software do CF. Isso é um risco real: as duas digitações podem divergir, e a diferença só aparece no fechamento [Prática]. Proposta em duas partes, ambas pequenas:

1. **Tela de apoio ao CF:** mostra o pedido pronto para digitar no outro software, na mesma ordem e com os mesmos totais (e, se útil, copiar o texto ou imprimir).
2. **Campo "CF emitido":** o atendente informa o número do cupom depois de emitir. O Fechamento de Caixa lista pedidos pagos sem CF informado, e a diferença entre vendas e CFs fica visível [Suposição].

Quando o nosso sistema passar a emitir o CF, o campo vira automático. Detalhar a emissão fiscal é um projeto à parte e não entra aqui.

### 3.5 Telas da recepção (2 PCs)

- **Novo pedido:** escolher produto, tamanho, observações; cliente e endereço quando for entrega; forma de pagamento.
- **Fila de pedidos:** todos os pedidos do dia, de qualquer canal, com situação e canal à vista; os dois PCs veem a mesma fila.
- **Detalhe do pedido:** itens, pagamentos, histórico de situações, cancelar, apoio ao CF.
- **Cardápio e preços** (perfil gerente).

O desenho visual vem depois da aprovação deste documento; segue a skill `frontend-design` do kit.

### 3.6 O que Vendas entrega aos outros módulos

| Para | O que | Quando |
|---|---|---|
| Produção | OP do pedido, com itens e observações | Na confirmação |
| Estoques | Consumo de insumos pela ficha técnica | Ao concluir o pedido [Suposição] |
| Fechamento de Caixa | Valor esperado por forma de pagamento | Ao receber o pagamento |
| Contas a Receber | Recebíveis de cartão, Pix e canal online | Ao receber o pagamento |
| BI | Receita, ticket médio, volume por canal | Consulta |

Cada ligação funciona também sem o módulo vizinho (princípio do plano macro): sem Produção, o pedido simplesmente não gera OP; sem Estoques, não baixa insumo.

### 3.7 Número do pedido e aviso ao cliente (B7)

**Número.** Reinicia a cada dia **[Decisão]**. Por isso o sistema guarda dois identificadores: um interno, único para sempre, e o número do dia (por exemplo "37"), que a produção e o cliente usam. A busca por número exige a data [Prática].

**Aviso ao cliente.** Marlon pediu que o código chegue ao Anota Ai por API e ao cliente por WhatsApp ou similar, e aceita sugestões. O que encontrei:

| Opção | Como funciona | Prós e contras |
|---|---|---|
| Retorno ao Anota Ai por API | Nosso sistema envia o código ao Anota Ai | **Não encontrei documentação pública** de envio de dados ao Anota Ai; o manual do Teknisa descreve só a entrada de pedidos [Fonte 1]. Depende do token e da documentação que o Anota Ai fornecer. Não confirmado |
| Link de WhatsApp com mensagem pronta | O sistema monta um link que abre o WhatsApp com a mensagem escrita; o atendente confirma o envio | Sem custo de API e sem aprovação; custa 1 clique por pedido [Prática] |
| API oficial do WhatsApp | Envio automático pelo sistema | Mensagem fora da janela de 24 horas só com modelo aprovado pela Meta; exige número dedicado e provedor ou integração própria [Fonte 4]. A cobrança por mensagem muda em 1/10/2026; um site de parceiro usa R$ 0,043 por mensagem como estimativa, não como valor oficial [Fonte 3] |
| SMS | Mensagem de texto | Não pesquisei |

**Recomendação [Prática].** No beta, exibir o número do dia em destaque na tela da recepção e na identificação impressa, e oferecer o link de WhatsApp de 1 clique. Deixar a API oficial do WhatsApp e o retorno ao Anota Ai para depois do token e de uma conta de volume real. A decisão e o custo estão na pergunta C5.

---

## 4. Perguntas

### 4.1 Respondidas em 16/10/2026

| # | Tema | Resposta de Marlon |
|---|---|---|
| B1 | Cardápio | Grande e Broto; Grande com até 2 sabores; há bordas e adicionais |
| B2 | Preço por canal | Igual nos dois aplicativos; varia por categoria (Tradicionais e Especiais) e tamanho |
| B3 | Tipos de pedido | Só retirada e entrega |
| B4 | Entrega | Taxa variável; entregadores terceiros |
| B5 | Pagamentos | Dinheiro, Pix, crédito e débito |
| B6 | Desconto e cancelamento | Sugestão aceita; limite em % nos parâmetros |
| B7 | Numeração | Reinicia por dia; código interno ao Anota Ai por API e ao cliente por WhatsApp ou similar |
| B8 | Cliente | Cadastro na primeira compra com nome, telefone e endereço |
| B9 | Logins | Pessoal e intransferível |
| B10 | Acesso ao Anota Ai | Só o administrador geral e o desenvolvedor |

Ficaram sem resposta: quantas pessoas operam a recepção por turno (parte da B9) e se há pagamento dividido (parte da B5); entram em C4 e C6.

### 4.2 Em aberto

- **C1. Cardápio.** Quais sabores há em Tradicionais e em Especiais, e quais os preços por tamanho, das bordas e dos adicionais? Pode enviar o cardápio em foto ou planilha.
- **C2. Dois sabores.** Na Grande de 2 sabores, o preço é o do sabor mais caro, a média dos dois ou outra regra? As duas primeiras são comuns [Prática]; recomendo o mais caro por ser mais simples de explicar ao cliente.
- **C3. Taxa de entrega.** O atendente digita o valor a cada pedido ou há tabela por região? Como o entregador terceiro é pago (por entrega, diária ou outro)?
- **C4. Pagamento.** Há pagamento dividido em mais de uma forma? Dinheiro registra o valor recebido e calcula o troco? Recomendo que sim aos dois.
- **C5. Aviso ao cliente.** Começamos com o link de WhatsApp de 1 clique (recomendado) e deixamos a API oficial para depois? O cliente do Anota Ai já recebe aviso do próprio Anota Ai?
- **C6. Login nos tablets e na recepção.** Quantas pessoas operam a recepção por turno? Nos tablets da produção, cada pizzaiolo entra com o login pessoal do turno? Recomendo que sim, com sessão longa, para a auditoria saber quem fez cada etapa.
- **C7. Pedido de acesso ao Anota Ai.** Como só o administrador geral e o desenvolvedor pedem o acesso, o pedido será feito por você? Posso redigir o texto do pedido para você enviar.

Limites de desconto: o sistema terá os campos em %; os valores iniciais ficam vazios até você definir.

Perguntas do plano macro que ficam para depois deste módulo: A4 (RH), A5 e A6 (Produção e impressora), A7 (confirmar a maior dor).

---

## 5. Ordem de trabalho proposta depois da aprovação

Por dependência: usuários e perfis, parâmetros da loja, cadastro de itens e cardápio, pedido de balcão, fila de pedidos, pagamento, cancelamento, apoio ao CF, adaptador do Anota Ai (quando houver token). Cada etapa com backup antes e teste de entrega, no padrão do kit (Manual Técnico, seções 13 e 14).

---

## 6. O que este documento ainda não responde

- Como será o instalador e a rotina diária do servidor local (qual PC, ligar e desligar, backup).
- Layout das telas e fluxo exato de cliques.
- Emissão fiscal pelo nosso sistema (projeto futuro, a pesquisar quando chegar a hora, incluindo o tipo de documento fiscal exigido no seu estado e município).

---

## 7. Fontes

1. Teknisa, "Manual AnotaAi": https://universidade.teknisa.com/wp-content/uploads/2025/12/Manual_AnotaAi.pdf (integração de um parceiro; não é documentação oficial da API do Anota Ai).
2. Kit Aplicação Web (Allex Corp, 16/10/2026): `01_Manual_Tecnico.md`, seções citadas.
3. Digisac, "Preço da API Oficial do WhatsApp: o que muda a partir de 1º de outubro" (22/09/2026): https://digisac.com.br/blog/preco-whatsapp-api-outubro-2026 (fornecedor de software; o valor em reais é estimativa de parceiros, não da Meta).
4. Drag, "API oficial do WhatsApp": https://www.dragapp.com/pt-br/blog/api-oficial-do-whatsapp/ (fornecedor de software; confirmar em fonte primária da Meta antes de contratar).
