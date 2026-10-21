# Desenho técnico 01: Primeiro incremento

Versão 0.2, 21/10/2026. Rascunho para aprovação de Marlon, com as respostas T1, T6, T7 e T10 incorporadas. Parte do [Plano Macro v1.0](../00_Plano_Macro.md), aprovado em 21/10/2026, seção 6 (etapas 0 e 1). Fontes de regra de negócio: [Núcleo e Vendas](../modulos/01_Nucleo_e_Vendas.md), [Produção](../modulos/02_Producao.md) e [Fechamento de Caixa](../modulos/03_Fechamento_de_Caixa.md). Fonte técnica: Kit Aplicação Web (Manual Técnico, citado como [Kit, seção]).

**Critério de sucesso:** Marlon lê este desenho e diz "aprovado" ou aponta o que corrigir; com a aprovação, começa a construção da fatia 1A. Este documento não escreve código; define o que será construído, em que ordem e com quais tabelas e telas.

Marcações: **[Decisão]** é de Marlon; **[Kit]** vem do manual técnico; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. Objetivo e escopo

**Meta.** A menor fatia que a loja usa de ponta a ponta, num dia de operação: entrar no sistema, cadastrar o cardápio, digitar um pedido de balcão com pagamento, levar cada pizza da montagem ao acabamento e fechar o dia.

**Dentro do incremento** (Plano Macro, seção 6):

1. Núcleo: usuários e perfis, login seguro, parâmetros da loja, auditoria, saúde do sistema, backup.
2. Cadastros: cardápio (sabores, tamanhos, bordas, adicionais, bebidas, calzones), clientes, entregadores.
3. Vendas: pedido de balcão, pagamento dividido, troco, desconto e acréscimo, cancelamento, fila de pedidos, apoio ao CF.
4. Produção: fila por função (massa, pizzaiolo, acabamento), forno, etiqueta, entrega e retirada no balcão.
5. Fechamento de Caixa: abertura, sangria e suprimento, contagem cega, diferença, acerto do entregador, relatório do dia.

**Fora do incremento** (entra depois, na ordem do Plano Macro): Anota Aí e qualquer adaptador de canal; baixa de estoque e ficha técnica; contas a pagar e receber; custos; imobilizado; RH; BI; envio de WhatsApp; emissão de CF; espelho na nuvem. As ligações com esses módulos já nascem previstas nos dados (canal, código externo, loja), sem funcionar ainda.

---

## 2. Arquitetura

### 2.1 Decisões herdadas **[Decisão]**

Um servidor local na recepção, FastAPI e PostgreSQL local, HTML puro no navegador. Dois PCs da recepção e quatro tablets falam com o servidor pela rede da loja. Só os canais externos precisam de internet. Um banco por loja, com o identificador da loja em todo registro. Backup diário fora da máquina. Preparado para migrar à nuvem (Fly.io) depois.

### 2.2 Estrutura do projeto **[Kit, seção 3]**

```
pizzaria/
  api/ config.py  database.py  security.py  schemas.py  main.py
       routers/ (um arquivo por entidade)   services/ (regras e cálculos)
  migrations_pg/  NNN_descricao.sql
  scripts/        aplicar_migrations_pg.py  criar_admin.py  backup.py
  frontend/       app.html (recepção)  producao.html (tablets)  static/
  tests/          pytest contra banco pizzaria_teste
  docs/  backups/(fora do git)  CLAUDE.md
```

Código no repositório `MarlonSpiess/pizzaria-sistema`, pasta `sistema/`, ao lado de `planejamento/` **[Suposição]**.

### 2.3 Regras técnicas que valem para tudo **[Kit, seções 1, 5, 6 e 7]**

- Senha de banco e segredos só em variável de ambiente, sem valor padrão no código.
- Entrada validada por schema (pydantic estrito); SQL sempre parametrizado.
- Dinheiro e quantidades em `NUMERIC`; data e hora geradas no servidor, fuso America/Sao_Paulo.
- Valores de lista (situação, forma de pagamento, função) com `CHECK` no banco, nunca só no código.
- Exclusão lógica (`ativo`), nunca apagar pedido, pagamento ou evento.
- Auditoria só de inserção: gatilho recusa UPDATE e DELETE nas tabelas de evento.
- Migrations numeradas, aplicadas uma vez, com checksum; nunca editar migration já aplicada.
- Erros ao usuário em português, sem expor SQL, banco ou caminho.

### 2.4 Pontos em que a loja difere do kit **[Suposição, a confirmar]**

| Ponto | Kit | Proposta para a loja |
|---|---|---|
| Servidor | gunicorn no Fly, uvicorn local | O servidor local roda no Windows como serviço (uvicorn ou waitress, a testar), que sobe sozinho com o PC (decisão H11 de Produção). gunicorn só no futuro espelho Fly |
| Origem única | Front e API na mesma origem [Kit, seção 7] | Igual: o servidor entrega as telas e a API; nada de CORS |
| Telas dos tablets | PWA em alguns apps | Páginas leves em tela cheia, sem instalar nada no tablet; PWA depois se precisar |
| Atualização das filas | Não há padrão no kit | Consulta a cada 3 segundos (polling) no começo; se pesar, troca por eventos do servidor. Não depende de internet |
| Impressora de etiqueta | PDF com reportlab [Kit, seção 11] | Etiqueta gerada em PDF e impressa pelo navegador; o modelo da impressora decide o formato (pendente) |
| Segundo PC servidor | Não há | Mesma instalação no segundo PC, parada; troca manual no começo (contingência H11) |
| Horário de funcionamento | Servidor ligado 24 horas | **Os PCs não são servidores dedicados**: rede só local e uso por volta de 10 horas por dia **[Decisão T1, 21/10/2026]**. O sistema sobe quando o PC liga e desliga o banco de forma limpa antes de o PC apagar; nada roda de madrugada |
| Tablet | Navegador comum | Tablet Android 14 ou superior, 1 a 2 GB de RAM e 32 GB de armazenamento **[Decisão T7]**: páginas leves, sem framework pesado, poucos dados por consulta |
| Impressora de etiqueta | PDF pelo navegador | **Impressora térmica Bluetooth, modelo simples [Decisão T7].** Navegador de tablet não imprime direto em Bluetooth e, pelo que sei, o Web Bluetooth só funciona em página segura (HTTPS), que a rede local comum não oferece **[Suposição, a testar]**. Caminhos a testar antes da 1D: (a) HTTPS local com certificado próprio, (b) aplicativo de impressão no tablet que recebe o comando, (c) impressora ligada por cabo ou Wi-Fi a um PC. O teste usa o modelo real de Marlon |

---

## 3. Fatias de construção

Cada fatia entrega algo que se usa e termina com backup antes, testes, dois QAs (um com contexto e um cego) e a validação de entrega de 4 pontos **[Kit, seções 13 e 14]**; o usuário pode dispensar QAs caso a caso.

| Fatia | Entrega | Pronto quando |
|---|---|---|
| 1A Núcleo | Servidor, banco, migrations, login, perfis, usuários, parâmetros, auditoria, saúde, backup | O administrador entra, cria usuários, e o backup diário restaura num banco de teste |
| 1B Cadastros | Cardápio e preços, adicionais, bordas, bebidas, clientes, entregadores | Marlon cadastra 3 sabores de cada categoria e o preço da meia e meia sai certo |
| 1C Vendas | Pedido de balcão, pagamento, desconto, cancelamento, fila, apoio ao CF | A recepção digita e paga um pedido de ponta a ponta, nos dois PCs |
| 1D Produção | Fila por função, forno, acabamento, etiqueta, entrega e retirada | Uma pizza vai da recepção ao despacho passando pelos tablets |
| 1E Caixa | Abertura, sangria, contagem cega, acerto do entregador, relatório | O dia fecha com diferença apontada e justificada |

Ordem justificada: cada fatia só usa o que a anterior já entregou. A massa em duas fases e o pedido urgente entram na 1D, depois da fila básica de pizzaiolo e acabamento **[Suposição]**.

---

## 4. Dados

Convenções: toda tabela leva `loja_id`, `criado_em`, `criado_por`; tabelas de negócio levam `ativo`; chaves primárias `BIGSERIAL`. Nomes finais podem mudar na construção sem mudar a regra.

### 4.1 Núcleo (fatia 1A)

| Tabela | O que guarda |
|---|---|
| `loja` | Identificador, nome, regime tributário, fuso |
| `usuario` | Login, nome, senha (bcrypt), perfil, ativo, deve trocar senha |
| `sessao` | Token (só o SHA-256), usuário, expiração |
| `login_falha` | Chave IP e usuário, hora; base do bloqueio após 5 falhas em 15 minutos |
| `parametro` | Chave, valor, vigente desde; histórico mantido |
| `auditoria` | Quem, quando, o quê, antes e depois; só inserção |
| `schema_version` | Migrations aplicadas e checksum |

Perfis iniciais: administrador, proprietário, gerente, subgerente, atendente, massa, pizzaiolo, acabamento. Subgerente tem as permissões do gerente, exceto aprovar diferença de caixa **[Decisão, 19/10/2026]**. Perfil lido sempre do cadastro atual; o que não está liberado é negado **[Kit, 6.4]**.

Parâmetros desta fatia: limite de desconto por perfil (%), valor padrão por entrega e diária do entregador, formas de pagamento aceitas, fundo de troco padrão, tolerância de diferença de caixa, valor de sangria que exige gerente, tempo de forno e pizzas por vez, número de maquininhas e taxa por forma. Valores iniciais de limites ficam vazios até Marlon definir **[Decisão]**.

### 4.2 Cadastros (fatia 1B)

| Tabela | O que guarda |
|---|---|
| `categoria_pizza` | Tradicionais, Especiais (e outras futuras) |
| `produto` | Tipo (pizza, calzone, bebida, acompanhamento), nome, categoria, ativo |
| `preco_produto` | Produto, tamanho, valor, vigente desde; o preço da Grande e da Broto de cada sabor |
| `adicional` | Borda ou extra, nome, valor |
| `canal` | Balcão e futuros; é cadastro, não código fixo **[Decisão C7]** |
| `codigo_externo` | Produto ou forma de pagamento, canal, código no parceiro (vazio até o Anota Aí) |
| `cliente` | Nome, telefone, endereço; cadastro na primeira compra **[Decisão B8]** |
| `entregador` | Nome, telefone, terceiro, ativo |

Não há `ficha_tecnica` nesta etapa; o espaço no Núcleo fica para a etapa 2 **[Plano Macro]**. O preço fica em tabela própria com vigência para o cardápio mudar sem alterar venda antiga (o preço é copiado ao item, abaixo).

### 4.3 Vendas (fatia 1C)

| Tabela | O que guarda |
|---|---|
| `pedido` | Id interno único, Id do dia, loja, canal, cliente, tipo (retirada ou entrega), situação, subtotal, desconto, acréscimo, taxa de entrega, total, observações, entrega calculada e real, número do CF informado, usuário |
| `item_pedido` | Pedido, sequência, produto, tamanho, sabor 1, sabor 2, preço copiado, observações |
| `item_adicional` | Item, adicional, valor copiado |
| `pagamento` | Pedido, forma, valor, troco, situação, maquininha |
| `ajuste_pedido` | Desconto ou acréscimo, valor, motivo, usuário, quem autorizou |
| `cancelamento` | Pedido, motivo, usuário, autorizador, momento |
| `contador_dia` | Loja, data, último número; gera o Id do dia sem repetir em duas recepções ao mesmo tempo |

**Id do pedido.** Número interno único e sequencial, exibido com o identificador da loja, mais o Id do dia que reinicia a cada dia **[Decisão B7 e H3]**. O Id do dia sai de `contador_dia`, atualizado na mesma transação do pedido, para os dois PCs não gerarem o mesmo número **[Prática]**.

**Preço da pizza.**

- Um sabor: valor do sabor no tamanho escolhido.
- Grande com dois sabores: metade do valor da Grande de cada sabor **[Decisão C2 e D1]**. Exemplo de Marlon: 35,00 e 50,00 resultam em 42,50.
- Adicionais e borda somam ao item; desconto e acréscimo vêm no fechamento, com motivo.
- **Arredondamento:** cálculo em `NUMERIC` com duas casas; metade de valor com centavo ímpar arredonda para cima por sabor **[Suposição, pergunta T4]**.

**Situações do pedido** (Produção, seção 7, mais o pagamento): recebido, em produção, acabado, despachado ou retirado, cancelado. Mudança de situação grava evento.

**Pagamento dividido** soma exatamente o total do pedido; só o dinheiro tem troco **[Decisão D4]**.

**Limites do atendente.** Desconto acima do percentual do perfil, cancelamento de pedido pago e estorno exigem login de gerente ou subgerente na hora, com motivo **[Decisão B6 e I10]**.

### 4.4 Produção (fatia 1D)

| Tabela | O que guarda |
|---|---|
| `pizza_producao` | Item de origem, sabores, tamanho, adicionais, situação, posição na fila, urgente, pizza original (refação) |
| `evento_producao` | Mudança de etapa, usuário, hora; só inserção; base dos tempos |
| `retrocesso` | Pizza, motivo (falta de insumo, saída do pizzaiolo, erro na borda, outros), usuário |
| `motivo_retrocesso`, `motivo_perda` | Listas de motivos em tabela |
| `lote_massa` | Tamanho, quantidade, responsável, hora (fase 1) |
| `estoque_massa_aberta` | Quantidade por tamanho e tipo, contada pelo operador |
| `perda` | Massa ou pizza, quantidade, motivo, usuário |
| `etiqueta_impressa` | Pizza, quando, por quem |

Situações da pizza: na lista, em montagem, no forno, acabada, perdida. A unidade de trabalho é a pizza **[Decisão]**. Pizzaiolo recebe sempre a próxima da lista; retroceder uma posição exige motivo; marcar como produzida a põe "no forno", que aceita várias pizzas ao mesmo tempo **[Decisão G e H7]**. O acabamento marca pizza e pedido como acabados; o pedido sempre à mão. O balcão marca entregue ou retirado e grava a hora real **[Decisão]**. Refação de pizza errada é nova pizza ligada à original, com motivo **[Decisão H10]**.

**Entrega calculada** (pizzas na frente divididas pelos pizzaiolos ativos, mais forno, acabamento e deslocamento) começa com valores iniciais nos parâmetros e passa a usar o histórico da loja quando houver dados **[Decisão H4, Suposição do método]**.

### 4.5 Fechamento de Caixa (fatia 1E)

| Tabela | O que guarda |
|---|---|
| `caixa_dia` | Data, aberto por, fundo de troco, situação, fechado por, aprovado por |
| `movimento_caixa` | Sangria ou suprimento, valor, motivo, autorizador, comprovante |
| `contagem_caixa` | Valor contado por forma de pagamento, sem ver o esperado, e depois o esperado e a diferença |
| `acerto_entregador` | Entregador, pedidos, dinheiro recebido, troco levado, valor por entrega, diária, total devido |
| `justificativa_diferenca` | Diferença, texto, responsável |

Um caixa por dia e uma gaveta por loja **[Decisão I1 e I2]**. A contagem é cega: o operador só vê a diferença depois de informar o contado; o gerente aprova diferenças acima da tolerância, e o subgerente não aprova **[Decisão I5 e 19/10/2026]**. Pedido pago sem CF informado só avisa **[Decisão I11]**. Valores realizados ficam prontos para Contas e BI, que entram depois.

---

## 5. Telas

**Recepção (2 PCs, `app.html`)**

| Tela | Perfis | Conteúdo |
|---|---|---|
| Entrar | todos | Usuário e senha; erro sempre igual |
| Novo pedido | atendente, gerente | Cliente (busca por telefone), itens, sabores, borda e adicionais, entrega ou retirada, taxa, pagamento dividido, troco, desconto com motivo |
| Fila de pedidos | atendente, gerente | Todos do dia, com situação e Id do dia em destaque; igual nos dois PCs |
| Detalhe do pedido | atendente, gerente | Itens, pagamentos, histórico, cancelar, apoio ao CF, aviso por WhatsApp com 1 clique |
| Entregas e despacho | atendente, gerente | Pedidos acabados, atribuição de entregador, marcar entregue ou retirado |
| Cardápio e preços | gerente | Sabores, categorias, tamanhos, bordas, adicionais |
| Caixa | atendente, gerente | Abrir, sangria, suprimento, contar, ver diferença, acerto de entregador, relatório |
| Usuários e parâmetros | administrador, proprietário | Cadastros e valores da loja |

**Tablets (`producao.html`, tela cheia, login pessoal)**

| Função | Mostra |
|---|---|
| Massa | Total de massas por tamanho a preparar, lançamento da fase 1, contagem de massa aberta, perda |
| Pizzaiolo | A próxima pizza (sabores, borda, adicionais, observações), marcar produzida, retroceder com motivo |
| Acabamento | Duas listas (pedidos em aberto, pedidos das pizzas no forno), marcar pizza acabada, imprimir etiqueta, marcar pedido acabado |

Tablets não mostram valores em dinheiro **[Decisão C6, parte de valores é suposição]**. O desenho visual segue a skill `frontend-design` do kit; protótipo de telas antes da construção da 1C e da 1D **[Suposição]**.

---

## 6. Interfaces (API interna)

Rotas em `/api`, um router por entidade, validação e perfis aplicados em todas: `/auth`, `/usuarios`, `/parametros`, `/produtos`, `/precos`, `/adicionais`, `/clientes`, `/entregadores`, `/pedidos` (criar, listar do dia, pagar, ajustar, cancelar, situação), `/producao` (próxima pizza, produzir, retroceder, acabar, etiqueta), `/caixa`, `/health`. A API interna da Produção que os tablets chamam é a mesma API; os canais externos futuros entram por adaptador que converte para o formato interno do pedido **[Decisão, Produção seção 1]**. Rotas de API são registradas antes das telas, para uma tela não interceptar uma listagem **[Kit, seção 7]**.

---

## 7. Segurança e instalação

- Login pessoal e intransferível; nenhuma senha padrão; primeiro administrador criado por script, com senha digitada sem eco **[Kit, 6.6]**.
- Servidor aberto só na rede da loja; firewall do Windows liberando só a porta do sistema; sem exposição direta à internet.
- **Backup [Decisão T6, 21/10/2026]:** `pg_dump` diário **ao fechar o dia** (o PC não fica ligado de madrugada), gravado no PC e copiado para o **Google Drive**; segunda cópia mantida no computador de Marlon. Sistema avisa na tela se o último backup tem mais de 1 dia. Teste de restauração faz parte da fatia 1A **[Decisão P8, Kit]**. Credenciais do Drive ficam em variável de ambiente, nunca no git.
- Atualização do sistema: backup antes, migrations, subida, `/health`; rotina escrita no instalador.
- Relógio do servidor certo e fuso fixo; todas as horas gravadas pelo servidor.

---

## 8. Riscos e como tratar

| Risco | Tratamento |
|---|---|
| PC servidor desligado com o banco em uso (sem energia ou apagado por engano) | O PostgreSQL recupera após queda, mas o backup do dia pode faltar: botão "fazer backup agora" e aviso de backup atrasado; nobreak recomendado **[Prática]** |
| Queda do PC servidor em pleno movimento | Segundo PC com a mesma instalação e cópia recente do banco; ensaio de troca antes de usar de verdade |
| Queda da rede da loja | Roteador e cabos conferidos antes; tablets e PCs reconectam sozinhos; avisar na tela quando perder conexão |
| Atendente digita pedido em dois PCs ao mesmo tempo | Contador do dia na transação; teste de corrida na suíte |
| Preço do cardápio muda com pedido aberto | Preço copiado ao item do pedido |
| Impressora de etiqueta sem driver ou sem conexão | Modelo definido antes da 1D; Wi-Fi mais Bluetooth ou cabo (H11); reimpressão registrada |
| Dados de teste misturados aos reais | Banco de teste separado, que a suíte recusa rodar fora de `*_teste` **[Kit, seção 13]** |
| Carga do cardápio atrasa | A 1B funciona com 3 sabores; a carga completa depende da lista D2 |

---

## 9. Perguntas para Marlon

Cada uma com a recomendação entre parênteses.

- **T1, respondida:** servidores não dedicados, só na rede local, uns 10 horas por dia **[Decisão]**.
- **T2 (em aberto):** os tablets usam o navegador em tela cheia, sem instalar aplicativo? (sim, no começo)
- **T3 (em aberto):** as filas dos tablets podem atualizar a cada 3 segundos, sem tempo real instantâneo? (sim)
- **T4 (em aberto):** na pizza Grande de dois sabores, arredondar a metade de cada sabor para cima quando sobrar meio centavo? (sim, e o total fica sempre com duas casas)
- **T5 (em aberto):** pedido urgente, massa em duas fases e pedido agendado entram na fatia 1D depois da fila básica? (sim)
- **T6, respondida:** Google Drive e uma cópia no computador de Marlon **[Decisão]**.
- **T7, respondida:** impressora térmica Bluetooth simples; tablet Android 14 ou superior com 1 a 2 GB de RAM e 32 GB **[Decisão]**. Falta o modelo exato da impressora para o teste de impressão (seção 2.4).
- **T8 (em aberto):** posso criar a pasta `sistema/` no repositório para o código, com testes e instruções de instalação? (sim)
- **T9 (em aberto):** a fatia 1A pode começar assim que você aprovar este desenho, sem esperar a lista de sabores e preços? (sim, ela só é necessária na 1B)
- **T10, respondida:** sim, protótipo clicável das telas antes da construção da 1C e da 1D **[Decisão]**.

---

## 10. O que este documento ainda não cobre

- Nomes finais de colunas, índices e gatilhos (saem das migrations, fatia a fatia).
- Desenho visual das telas e fluxo exato de cliques.
- Instalador e rotina diária de ligar e desligar o servidor.
- Estoques e Compras, Contas, Custos, Imobilizado, RH e BI (etapas 2 a 6).
- Adaptador do Anota Aí (depende de o token ser pedido por Marlon) e emissão de CF.
- Formato da etiqueta (depende do modelo da impressora).
