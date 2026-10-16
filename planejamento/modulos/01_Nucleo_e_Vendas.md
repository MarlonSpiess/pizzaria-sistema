# Detalhamento 01: Núcleo e Vendas

Versão 0.1, 16/10/2026. Rascunho para discussão. Parte do [Plano Macro v0.2](../00_Plano_Macro.md).

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

---

## 2. Núcleo

**Objetivo.** Dar a todos os módulos a mesma base de usuários, permissões, auditoria e cadastros, para que cada fato seja registrado uma só vez.

### 2.1 Submódulos

| Submódulo | Para quê | Origem |
|---|---|---|
| Usuários e perfis | Quem entra, o que pode fazer | [Kit] |
| Segurança de acesso | Login, sessão, bloqueio de tentativas | [Kit] |
| Auditoria | Quem registrou ou alterou cada fato de negócio | [Kit] |
| Parâmetros da loja | Identificador da loja, nome, regime tributário, fuso, formas de pagamento aceitas | [Decisão] e [Prática] |
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
| Pedido | Número, loja, canal, data e hora, cliente, tipo (entrega, retirada, salão [Suposição]), situação, totais, usuário |
| Item do pedido | Produto, tamanho/variação, quantidade, preço na hora da venda, observações |
| Observação de item | Tipo: acréscimo, retirada ou observação livre (os três tipos que o Anota Ai usa, segundo [Fonte 1]) |
| Pagamento | Forma, valor, situação, troco; no caso de pagamento online, o código externo com prefixo ONLINE_ ou OFFLINE_ [Fonte 1] |
| Cliente e endereço | Nome, telefone, endereço de entrega |
| Entrega | Entregador, taxa, saída e retorno (detalhes no módulo de Produção) |
| Cancelamento | Motivo, usuário, momento |
| Código externo | Identificador do pedido, do produto e da forma de pagamento no Anota Ai, para ligar os dois lados |

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

---

## 4. Perguntas em aberto para este detalhamento

Para responder rápido, as que têm recomendação podem ser aceitas com "ok".

- **B1. Cardápio.** Quais tamanhos de pizza existem e como se chamam? Há meio a meio, bordas e adicionais? Pelo manual do Teknisa, produto fracionado precisa ser cadastrado como item separado no Anota Ai [Fonte 1]; recomendo modelar meio a meio como pedido de dois sabores na mesma pizza, e não como produto novo.
- **B2. Preço por canal.** O preço é o mesmo no balcão e no Anota Ai, ou muda? Recomendo permitir preço por canal desde o início.
- **B3. Tipos de pedido.** Além de entrega e retirada, há consumo no salão? Recomendo começar com entrega e retirada.
- **B4. Entrega.** A taxa é fixa, por bairro ou por distância? Os entregadores são funcionários ou terceiros?
- **B5. Pagamentos aceitos.** Quais formas (dinheiro, Pix, débito, crédito, voucher)? Há pagamento dividido em mais de uma forma?
- **B6. Desconto e cancelamento.** Quem pode dar desconto e cancelar? Recomendo atendente até um limite e gerente acima dele, com motivo sempre obrigatório. Qual o limite?
- **B7. Numeração.** O número do pedido reinicia a cada dia ou segue contínuo? Recomendo reiniciar por dia, com data no registro, para a produção chamar "pedido 37".
- **B8. Cliente.** Cadastro por telefone na primeira compra? Qual o mínimo de dados necessário (nome, telefone, endereço)?
- **B9. Quem usa.** Quantas pessoas operam a recepção em cada turno, e todas usam o mesmo login ou cada uma o seu? Recomendo um login por pessoa, para a auditoria funcionar.
- **B10. Anota Ai.** Quem pode pedir o acesso de integração ao Anota Ai? (pergunta A2 do plano)

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
