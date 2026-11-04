# Manual Técnico do Sistema Integrado da Pizzaria

Versão 2.0, 04/11/2026. Descreve o sistema como ele está no código do PR #2 (branch `claude/project-thread-qkmkh7`, commit `a55b10d`), com 3 módulos, 1 login e acesso rígido por função conferido no servidor. Substitui, para o que é técnico, o README antigo de `sistema/` (que ainda falava só da fatia 1A).

**Público:** quem instala, mantém ou continua o desenvolvimento. Marlon é o dono do projeto e quem decide as regras de negócio.

**Critério de sucesso deste manual:** uma pessoa técnica que nunca viu o projeto consegue instalar, operar, fazer backup, entender a arquitetura, achar a rota e a tabela de qualquer função e saber o que ainda está pendente, sem precisar perguntar a Marlon.

**Como ler as marcações:** **[Construído]** existe no código e tem teste; **[Estrutura]** existe no código, mas depende de algo externo para funcionar de verdade; **[Pendente]** falta decisão ou informação externa. Nada marcado como pendente foi inventado aqui.

Apêndices gerados do código (não editar à mão):

- [Apêndice A: rotas da API e permissão exigida](Apendice_A_Rotas_da_API.md)
- [Apêndice B: permissões por perfil](Apendice_B_Permissoes_por_Perfil.md)

---

## 1. Visão geral

O sistema é uma aplicação web única que roda no PC da loja e atende, pela rede local, os 2 PCs da recepção, os tablets da produção e o PC do escritório. Cada pessoa entra com o seu login pessoal e vê só as áreas e telas da sua função.

| Área (módulo) | Para quem | O que cobre |
|---|---|---|
| 🍕 Produção | massa, pizzaiolo, acabamento e gerência | Massa, Montagem, Forno, Acabamento com etiqueta, Despacho, Andamento e Motivos |
| 🧾 Vendas | atendente e gerência | Pedidos (novo pedido, pedidos do dia), Caixa e entregas, Canais (loja aberta, Anota Ai, iFood no futuro), Clientes, Entregadores |
| 🏢 Administrativo (na tela, "Admin") | gerência, proprietário e administrador; o atendente só consulta o Cardápio | Painel, Cardápio, Fichas e etapas, Estoque, Compras, Contas, BI, Custos, Imobilizado, RH, Usuários, Parâmetros, Auditoria |

Os 9 módulos do planejamento original (RH, Imobilizado, Estoques e Compras, Contas, Custos, Vendas, Produção, Fechamento de Caixa e BI) continuam existindo como partes do código. A decisão de 03/11/2026 só os reorganizou em 3 áreas de uso, um login e um servidor. A correspondência está na seção 9.

---

## 2. Arquitetura

### 2.1 Princípio

Uma loja, um login, um banco e as mesmas regras de acesso pedem **um servidor único com módulos separados no código** (monólito modular). Separar em vários servidores aumentaria a manutenção sem ganho de segurança, porque a barreira real é a permissão conferida em cada rota. Decisão aprovada por Marlon em 04/11/2026 ([Plano_Aplicacoes_e_Servidores.md](../../arquitetura/Plano_Aplicacoes_e_Servidores.md)).

### 2.2 Peças

| Peça | Tecnologia | Onde roda (beta) | Situação |
|---|---|---|---|
| Servidor de aplicação (API e telas) | Python 3.11 ou mais novo, FastAPI, Uvicorn | PC da loja, porta 8080 | [Construído] |
| Banco de dados | PostgreSQL 16 ou mais novo | PC da loja | [Construído] |
| Telas | HTML, CSS e JavaScript sem framework (`frontend/app.html`, `static/app.js`), servidas pela mesma origem da API (sem CORS) | Navegador dos PCs e tablets | [Construído] |
| Varredor de canais | Tarefa em segundo plano dentro do mesmo processo, a cada 1 segundo | PC da loja | [Estrutura]: só liga quando há canal configurado |
| Adaptador do Anota Ai | `api/services/anotaai.py` | PC da loja | [Pendente] da documentação da API |
| Impressão de etiqueta | `window.print()` no tablet do acabamento | Tablet | [Pendente] teste da impressora térmica Bluetooth |

```
 Tablets (massa, pizzaiolo, acabamento)      PCs da recepção        PC do escritório
            \                                      |                       /
             \______________ rede local (http://IP-DO-PC:8080) ___________/
                                         |
                       PC da loja: Uvicorn + FastAPI (API /api e telas /)
                         |                  |                      |
                  PostgreSQL local    Varredor de canais ----> API do Anota Ai (internet)
                                       (1 segundo)              [Pendente: token e documentação]
```

O sistema **chama** o Anota Ai; o Anota Ai não chama o sistema (decisão de Marlon, 04/11/2026). Por isso o beta continua na loja, sem endereço público, sem nuvem e sem HTTPS.

### 2.3 Organização do código (`sistema/`)

| Pasta ou arquivo | Conteúdo |
|---|---|
| `api/main.py` | Cria a aplicação, middlewares (limite de corpo de 1 MB, gzip, cabeçalhos de segurança e CSP), `/health`, registra os routers em `/api`, serve as telas e liga e desliga o varredor |
| `api/config.py` | Toda a configuração por variável de ambiente (seção 6.3). Nenhum segredo no código |
| `api/database.py` | Pool de conexões (psycopg 3), `agora()` e `hoje()` no fuso de Brasília, tradução de erros do banco |
| `api/security.py` | Perfis, matriz de permissões, sessão, bloqueio de login, `requer` e `requer_alguma` |
| `api/schemas.py` | Validação de entrada (Pydantic) |
| `api/routers/` | Uma rota por assunto: auth, usuarios, parametros, auditoria, sistema, cardapio, pessoas, receitas, vendas, producao, caixa, canais, vendas_fechadas, estoque, compras, contas, custos, imobilizado, rh, bi |
| `api/services/` | Regras de negócio: preço, vendas, produção, caixa, estoque, compras, contas, custos, imobilizado, parâmetros, dinheiro, backup, canais, ingredientes (vendas fechadas), varredor, anotaai |
| `migrations_pg/` | Migrações SQL numeradas (seção 3) |
| `scripts/` | Aplicar migrações, criar administrador, carregar cardápio e ficha técnica, backup, restaurar em banco de teste, papel restrito do app |
| `tests/` | Suíte pytest contra PostgreSQL real (seção 8) |
| `docs/` | Relatórios de QA cego e respostas, por fatia |
| `start_api.bat`, `stop_api.bat`, `set_env.bat.example` | Subir o servidor no Windows, ver quem usa a porta, modelo de variáveis |

### 2.4 Regras transversais

- **Dinheiro e quantidades** em `NUMERIC` e `Decimal`; nunca ponto flutuante.
- **Horário** em `TIMESTAMPTZ`, gerado em Python no fuso `America/Sao_Paulo`.
- **Histórico só de inserção** em auditoria, eventos de pedido e de produção, movimentos de caixa e de estoque, versões de ficha técnica e preços. Correção é um novo registro, não uma edição.
- **Exclusão lógica** (`ativo`) em cadastros; nada financeiro ou de estoque é apagado.
- **Uma loja por banco**; `loja_id` em todo registro (`LOJA_ID`, padrão 1), para um futuro aplicativo central ler vários bancos.
- **Parâmetros da loja** com histórico, sem valor fixo no código (seção 7.3).

---

## 3. Banco de dados e migrações

### 3.1 Como as migrações funcionam

`scripts/aplicar_migrations_pg.py` aplica cada arquivo `migrations_pg/NNN_*.sql` uma única vez, em ordem, registra em `schema_version` com checksum e usa trava (`pg_try_advisory_lock`) para impedir duas execuções ao mesmo tempo. Cada migração roda numa transação: falhou, nada fica pela metade. `start_api.bat` aplica as migrações antes de subir.

Regras para escrever uma migração nova:

1. Nunca editar uma migração já aplicada (o checksum acusa). Criar a próxima numeração.
2. Sem `BEGIN`, `COMMIT`, `ROLLBACK`, `CREATE INDEX CONCURRENTLY` ou `VACUUM` (o script recusa).
3. Idempotente (`IF NOT EXISTS`) e curta.
4. Rodar com o papel dono do banco (`MIGRATE_DB_USER`), nunca com o papel do app.
5. Depois de aplicar, rodar `papel_app.sql` de novo (seção 3.4).

`--dry-run` mostra o que seria aplicado sem alterar nada.

### 3.2 Migrações existentes (até a 018)

| Nº | Arquivo | Fatia | Tabelas criadas ou alteradas |
|---|---|---|---|
| 001 | `001_nucleo.sql` | 1A Núcleo | loja, usuario, sessao, login_falha, parametro, auditoria, backup_registro |
| 002 | `002_cadastros.sql` | 1B Cadastros | categoria_pizza, produto, preco_produto, adicional, preco_adicional, cliente, entregador |
| 003 | `003_fichas_e_etapas.sql` | 1B2 Fichas e etapas | item, ficha_versao, ficha_linha, etapa, etapa_modelo, produto_etapa |
| 004 | `004_vendas.sql` | 1C Vendas | contador_dia, pedido, item_pedido, item_adicional, pagamento, ajuste_pedido, cancelamento, evento_pedido |
| 005 | `005_producao.sql` | 1D Produção | motivo_retrocesso, motivo_perda, pizza_producao, evento_producao, retrocesso, lote_massa, contagem_massa, perda, etiqueta_impressa |
| 006 | `006_caixa.sql` | 1E Caixa | maquininha, regra_recebimento, motivo_movimento, caixa_dia, movimento_caixa, estorno, contagem_caixa, entrega, acerto_entregador |
| 007 | `007_estoques.sql` | 2A Estoques | local_estoque, item_estoque, lote_estoque, movimento_estoque, custo_item, inventario, inventario_linha, baixa_origem, pendencia_estoque |
| 008 | `008_compras.sql` | 2B Compras | fornecedor, preco_compra, lista_compra, lista_compra_item, cotacao_resposta, lista_compra_escolha, pedido_compra, pedido_compra_item, recebimento, recebimento_item |
| 009 | `009_contas.sql` | 3 Contas | conta_bancaria, tipo_despesa, canal_repasse, recorrente, titulo, baixa_titulo, extrato_linha, conciliacao |
| 010 | `010_custos.sql` | 4 Custos | item_custo, fechamento_cmv |
| 011 | `011_imobilizado.sql` | 5 Imobilizado | categoria_bem, bem, baixa_bem, depreciacao_bem, conferencia_bem, plano_manutencao, limite_leitura, leitura_bem, ordem_servico, os_peca |
| 012 | `012_rh.sql` | 6 RH | funcao_rh, escala_tipo, funcionario, contrato, beneficio_funcionario, turno, ponto, banco_horas, ausencia, documento_rh, folha_resumo |
| 013 | `013_canais.sql` | Canais | canal_venda, entrada_canal (fila de entrada), mapa_produto_canal (ID externo por produto) |
| 014 | `014_avisos_canal.sql` | Canais | aviso_canal (fila de avisos de status com tentativas) |
| 015 | `015_eventos_aviso_anotaai.sql` | Canais | Troca os eventos de aviso para `pronto` e `finalizado`, conforme o manual do Anota Ai; descarta avisos antigos não enviados |
| 016 | `016_importacao_canal.sql` | Canais | Estados da entrada (pendente, importando, importada, bloqueada, recusada), `pedido_id`, `importando_desde`, `importacao_tentativas`; flag `aceitar_sozinho` no canal |
| 017 | `017_loja_aberta.sql` | Canais | `loja.loja_aberta` e `loja.loja_aberta_desde` (flag manual da gerência, desligada por padrão) |
| 018 | `018_vendas_fechadas.sql` | Vendas fechadas | ingrediente_em_falta (histórico de falta e reabertura); em mapa_produto_canal: `pausado_no_canal`, `sincronizado_em`, `erro_sincronia` |

São 101 tabelas. O sabor com venda fechada **não é guardado**: é calculado a partir dos ingredientes em falta e da ficha técnica mais recente (incluindo preparos, até 5 níveis), para nunca ficar fora de sincronia.

### 3.3 Máquinas de estado principais

| Entidade | Estados | Quem muda |
|---|---|---|
| Pedido (`pedido.situacao`) | recebido → em producao → acabado → despachado ou retirado; cancelado a partir de qualquer estado antes de despachado | Produção move até acabado (o acabamento marca o pedido acabado); o balcão marca despachado ou retirado; a gerência pode mover à mão |
| Pizza ou calzone (`pizza_producao.situacao`) | na lista → em montagem → no forno → saiu do forno → acabada; perdida; cancelada | Pizzaiolo (montagem e retrocesso), acabamento (saiu do forno, acabada, refazer). A refação cria pizza nova ligada à original (`original_id`), na frente da fila; refazer pizza já perdida não duplica perda nem baixa; a perdida deixa de contar como pendente do pedido |
| Caixa do dia (`caixa_dia.situacao`) | aberto → contado → fechado | Atendente abre, conta e fecha; diferença acima da tolerância exige aprovação de gerente, proprietário ou administrador que não fez a contagem (subgerente não) |
| Ingrediente em falta (`ingrediente_em_falta`) | em falta (sem `reaberto_em`) → reaberto | Gerência (`vendas.gerir`), em Estoque > Alertas |
| Entrada do canal (`entrada_canal.situacao`) | pendente → importando → importada; bloqueada; recusada | Varredor e importação; a gerência decide as bloqueadas (tentar de novo ou recusar) |
| Aviso ao canal (`aviso_canal`) | pendente (com `proxima_tentativa`) → enviado; para após 20 tentativas com erro registrado | Varredor |
| Lista de compras | rascunho → cotando → definida → aprovada; cancelada | Gerência |
| Título (contas) | aberto → parcial → baixado; cancelado | Gerência; acima do limite, administrador ou proprietário aprova |
| Ordem de serviço | aberta → em_execucao → fechada; cancelada | Gerência; acima do limite, administrador ou proprietário aprova |

### 3.4 Papel restrito do aplicativo

O app conecta com um papel sem privilégio de dono (`pizzaria_app`). `scripts/papel_app.sql` dá leitura e escrita nas tabelas e **tira** `UPDATE`, `DELETE` e `TRUNCATE` da auditoria e do registro de backup. Assim nem um erro no código consegue apagar a auditoria. As migrações usam o papel dono (`MIGRATE_DB_USER`). O script tem `ALTER DEFAULT PRIVILEGES` para tabelas e sequências, então tabelas novas criadas pelo papel dono já ficam acessíveis ao app; mesmo assim, rodar o `papel_app.sql` de novo depois de cada migração é seguro (é repetível) e recomendado. Só vale se `DB_USER=pizzaria_app`; o padrão do código é `postgres`.

---

## 4. API

### 4.1 Convenções

- Tudo em `/api/...`, JSON, mesma origem das telas.
- Autenticação por `Authorization: Bearer <token>`. O token vem de `POST /api/auth/login` e é guardado no banco só como SHA-256.
- Erros: 400 dado inválido, 401 sem sessão, 403 sem permissão ou regra de autorização, 404 não encontrado, 409 conflito de estado (ex.: caixa não aberto), 413 corpo acima de 1 MB, 422 validação, 429 excesso de tentativas de login. Mensagens em português, prontas para a tela.
- `/health` responde 200 se servidor e banco estão no ar, 503 se o banco caiu. Não exige login e não devolve dado sensível.
- `/docs` e `/openapi.json` só existem com `DOCS_ENABLED=1`. Deixe desligado na loja: eles listam todas as rotas.

### 4.2 Rotas por área

São 250 rotas. A lista completa, com a permissão de cada uma, está no [Apêndice A](Apendice_A_Rotas_da_API.md). Resumo por área de uso:

| Área | Grupos de rotas |
|---|---|
| Comum | `/auth` (login, logout, me, trocar senha), `/rh/meus-dados` |
| Produção | `/producao/fila`, `/producao/pizzas/*` (próxima, produzida, retroceder, saiu do forno, acabada, perder, refazer), `/producao/perdidas` (pizzas perdidas aguardando refação: acabamento e gerência), `/producao/pedidos`, `/producao/massa/*`, `/producao/motivos/*`, `/caixa/despacho*` |
| Vendas | `/pedidos/*` (calcular, criar, listar, situação, urgente, CF, cancelar), `/caixa/*` (abrir, movimentos, contagem, fechar, entregas, acertos, motivos, maquininhas, regras de recebimento, relatório), `/canais/*` (incluindo `/canais/loja`), `/vendas-fechadas/*`, `/clientes/*`, `/entregadores/*`, `/parametros/formas-pagamento` |
| Administrativo | `/categorias`, `/produtos`, `/adicionais`, `/precos/pizza`, `/itens`, `/fichas/*`, `/etapas`, `/modelo-etapas`, `/estoque/*`, `/compras/*`, `/contas/*`, `/custos/*`, `/imobilizado/*`, `/rh/*`, `/bi/*`, `/usuarios/*`, `/parametros/*`, `/auditoria`, `/sistema/backup` |

### 4.3 Rotas que filtram pelo perfil

Algumas leituras são compartilhadas por várias funções e a própria rota corta o que a função não deve ver:

- `GET /producao/fila`: montagem vê só "na lista" e "em montagem"; acabamento vê "no forno" e "saiu do forno" ("acabada" só se pedir pelo filtro) e o estado do forno; gerência vê tudo. Situação fora do conjunto recebe 403. O nome do cliente só vai para acabamento e gerência (a etiqueta usa).
- `GET /producao/pedidos`: só acabamento e gerência.
- `GET /caixa/despacho`: pedido, situação e nome do entregador, **sem total e sem valor**. Avisa quando o caixa não está aberto. `POST /caixa/despacho/{pedido}` usa sempre o valor padrão da entrega.
- `POST /pedidos/{id}/situacao`: o balcão só marca "despachado ou retirado"; os demais estados exigem `vendas.gerir`. Pedido de **entrega vindo de canal** só vai para "despachado ou retirado" com entregador atribuído (o acerto depende disso).

---

## 5. Segurança e controle de acesso

### 5.1 Princípio

Cada função só vê e só acessa o que é dela, e **a regra vale no servidor, não só no menu** (decisão de Marlon, 03/11/2026). Esconder um botão não protege nada, porque o código das telas é público e qualquer um pode chamar a rota direto. Toda rota de negócio confere a permissão do perfil **atual** de quem chama; só `/auth/login` e `/health` dispensam login, e `/auth/logout`, `/auth/me` e `/auth/trocar-senha` exigem apenas sessão válida (menor privilégio, negado por padrão).

### 5.2 Perfis

| Perfil | Área ao entrar | O que pode, em resumo |
|---|---|---|
| administrador | última área | Tudo |
| proprietário | última área | Tudo |
| gerente | última área | Tudo da operação e do escritório, menos: usuários, editar parâmetros, configurar canais, aprovar em Contas e em Imobilizado, ver salários |
| subgerente | última área | O mesmo do gerente, menos aprovar diferença de caixa, autorizar sangria acima do limite e aprovar em RH |
| atendente | Vendas | Novo pedido, pedidos do dia, caixa (abrir, lançar, contar, fechar), entregas e acerto, clientes; consulta cardápio e entregadores; Meus dados |
| massa | Produção | Só a tela Massa (lote, contagem, perda de massa); Meus dados |
| pizzaiolo | Produção | Só a tela Montagem (pegar, produzida, retroceder, perda); Meus dados |
| acabamento | Produção | Só Forno, Acabamento e Despacho (sem valores); Meus dados |

A matriz completa permissão por perfil está no [Apêndice B](Apendice_B_Permissoes_por_Perfil.md). A tela repete a mesma regra (lista `ABAS` e `SUBS_PRODUCAO` em `app.js`) só para não mostrar o que daria erro.

Regras que chamam atenção:

- O **acabamento não vê o valor do pedido** e só despacha com o **caixa do dia aberto**.
- O **Andamento** (visão geral da cozinha) é só da gerência. O atendente não acessa Produção; a hora de entrega calculada aparece em Vendas > Pedidos do dia.
- **Canais:** ativar canal, ligar "aceitar sozinho" e editar o mapa de produtos é só de administrador e proprietário (`canais.configurar`). A gerência (`vendas.gerir`) vê a fila, recusa, manda tentar de novo, liga e desliga **loja aberta** e fecha ou reabre vendas por ingrediente.
- **Alerta de estoque** (negativo, zerado, repor, abaixo do mínimo): visto por quem tem `estoque.ver` (administrador, proprietário, gerente, subgerente), em Estoque > Alertas e no BI.
- **Aprovação por outra pessoa:** quem contou o caixa não aprova a própria diferença; desconto acima do limite, taxa de entrega abaixo da padrão e cancelamento de pedido pago pelo atendente exigem login e senha de um gerente ou subgerente na hora; sangria acima do limite exige gerente, proprietário ou administrador.

### 5.3 Login e sessão

- Senha com bcrypt; mínimo de 8 caracteres; troca obrigatória no primeiro acesso.
- Sessão em tabela (não na memória), validade de 12 horas (`SESSION_TTL_HOURS`). O perfil é relido a cada chamada: usuário desativado perde a sessão na hora.
- Bloqueio de 5 falhas em 15 minutos por IP e usuário (`LOGIN_MAX_FALHAS`, `LOGIN_JANELA_MIN`), com trava para tentativas simultâneas. Usuário inexistente gasta o mesmo tempo que o existente.
- Cabeçalhos: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, CSP restrita a `'self'`, `Cache-Control: no-store` na API.

### 5.4 Segredos

Senhas do banco e o token do Anota Ai só em variável de ambiente (`set_env.bat`, fora do git). O token do canal nunca vai para o banco.

### 5.5 Antes de qualquer acesso de fora da loja [Pendente]

HTTPS (não existe no código), `DOCS_ENABLED` desligado, `CLIENT_IP_HEADER` definido se houver proxy (senão todos os clientes aparecem com o IP do proxy e o bloqueio de login vale para todos). Decisão de nuvem e HTTPS é de Marlon e hoje não é necessária.

---

## 6. Instalação

O roteiro passo a passo, para quem instala no PC da loja, está em [Roteiro_de_Instalacao_Loja.md](../../instalacao/Roteiro_de_Instalacao_Loja.md). Resumo técnico:

### 6.1 Pré-requisitos

- Windows no PC da loja, ligado durante o expediente, com IP fixo reservado no roteador.
- Python 3.11 ou mais novo; PostgreSQL 16 ou mais novo.
- Tablets Android 14 ou mais novo, com navegador Chrome.

### 6.2 Passos

1. Criar o banco `pizzaria` e o papel `pizzaria_app` (sem superusuário).
2. `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt` (FastAPI 0.158.2, Uvicorn 0.53.0, Pydantic 2.13.5, psycopg 3.3.6, psycopg-pool 3.3.3, bcrypt 5.0.0).
3. Copiar `set_env.bat.example` para `set_env.bat` e preencher.
4. `python scripts\aplicar_migrations_pg.py`, depois `psql -U postgres -d pizzaria -v app_role=pizzaria_app -f scripts\papel_app.sql`, depois `python scripts\criar_admin.py --usuario admin --nome "..." --loja-nome "..."` (senha pedida sem eco).
5. `start_api.bat` (aplica migrações e sobe em `0.0.0.0:8080` com `--no-proxy-headers`).
6. Firewall do Windows: liberar a porta 8080 **só para rede privada**. Nunca abrir para a internet.

### 6.3 Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | localhost, 5432, pizzaria, postgres | Conexão do app (use `pizzaria_app`) |
| `DB_PASS` | (obrigatória) | Senha do app; sem ela o servidor não sobe |
| `MIGRATE_DB_USER`, `MIGRATE_DB_PASS` | DB_USER e DB_PASS | Papel dono, só para `aplicar_migrations_pg.py` (o `criar_admin.py` usa `DB_USER`) |
| `PIZZARIA_ADMIN_SENHA` | vazio | Senha do primeiro administrador sem pergunta (`criar_admin.py`); evite deixar gravada |
| `LOJA_ID` | 1 | Identificador da loja neste banco |
| `PIZZARIA_PORT` | 8080 | Porta (`start_api.bat`) |
| `SESSION_TTL_HOURS` | 12 | Validade da sessão |
| `LOGIN_MAX_FALHAS`, `LOGIN_JANELA_MIN` | 5, 15 | Bloqueio de login |
| `CLIENT_IP_HEADER` | vazio | Só atrás de proxy confiável |
| `DOCS_ENABLED` | 0 | Liga `/docs`; manter 0 na loja |
| `DB_POOL_MAX`, `DB_POOL_TIMEOUT`, `DB_STATEMENT_TIMEOUT`, `DB_LOCK_TIMEOUT` | 10, 5, 30, 10 | Pool e tempos do banco (segundos) |
| `BACKUP_DIR`, `BACKUP_DIRS_EXTRA`, `BACKUP_RETENCAO`, `BACKUP_ATRASO_HORAS`, `PG_DUMP_PATH` | backups, vazio, 30, 24, pg_dump | Backup |
| `ANOTAAI_URL`, `ANOTAAI_TOKEN` | vazio | Integração Anota Ai; vazias, nada é chamado |
| `CANAIS_INTERVALO_S` | 1 | Intervalo do varredor (mínimo 1 segundo) |

### 6.4 Primeira carga

Usuários e perfis, parâmetros, cardápio e fichas técnicas (scripts `carregar_cardapio.py` e `carregar_ficha_tecnica.py`, que simulam antes de aplicar com `--aplicar`), tipos de despesa, conta bancária, regras de recebimento e estoque inicial. A ordem e os cuidados estão no roteiro de instalação (seção 7). Os arquivos de carga ficam em `planejamento/carga/` (`cardapio.csv` e `ficha_tecnica_normalizada.csv`).

---

## 7. Operação

### 7.1 Rotina diária (o que o sistema espera)

1. Ligar o PC da loja; `start_api.bat` sobe sozinho se estiver no Agendador de Tarefas.
2. A recepção abre o caixa do dia (fundo de troco). Sem caixa aberto não há despacho e, se o parâmetro mandar, não há venda. Depois da contagem ou do fechamento do caixa de hoje, não há venda nem cancelamento, e o caixa do dia não reabre.
3. A gerência liga **loja aberta** em Vendas > Canais (flag manual, decisão de Marlon de 04/11/2026), que indica que a loja já recebe pedidos e entra no critério de "aceitar sozinho". Ela não muda sozinha: desligar ao encerrar.
4. Durante o dia: pedidos, produção, despacho, acerto dos entregadores.
5. No fim: acertar todos os entregadores, contagem cega, fechamento, backup.

### 7.2 Integração com o Anota Ai

| Item | Como funciona | Situação |
|---|---|---|
| Varredura | A cada 1 segundo, só com o canal **ativo** e o adaptador configurado. Só um processo por canal (trava no banco). Enquanto há uma entrada "importando", a varredura espera | [Estrutura] |
| Falha do canal | Espera crescente (2, 4, 8 até 60 segundos), registro no log, nada cai | [Estrutura] |
| Importar | Ler o pedido na fila do Anota Ai, ver se a loja pode produzir, aceitar no Anota Ai (prazo de 15 minutos, senão o Anota Ai cancela) e criar o pedido no sistema | [Pendente] da API para aceitar e criar |
| Importação travada | Após 120 segundos volta para a fila; na 3ª queda vira "bloqueada" para a gerência decidir (tentar de novo ou recusar) | [Construído] |
| Aceitar sozinho | Flag por canal, desligada por padrão, só administrador e proprietário. Ligada, aceita sem a gerência quando: canal ativo, **loja aberta**, caixa **de hoje** aberto, todos os itens no mapa de produtos (produto ativo) e nenhum sabor com venda fechada. "Caixa de hoje" é o caixa com a data do dia: depois da meia-noite, com o caixa da véspera ainda aberto, nada é aceito sozinho | [Estrutura]: a regra está escrita e testada, mas ainda não é chamada, porque a importação depende da API |
| Avisos de status | Fila com tentativas e reenvio sem duplicar. Retirada: "pronto" quando o pedido fica acabado, "finalizado" quando o cliente retira. Entrega: "pronto" quando o entregador sai | [Estrutura] |
| Finalizar entrega | O **acerto do entregador** no caixa enfileira "finalizado" dos pedidos de canal que ele levou (e "pronto", se faltou). "Finalizado" espera o "pronto" ser enviado (ou esgotar as 20 tentativas). Entre tentativas, a espera cresce até 300 segundos. Pedido de canal só é despachado com o entregador atribuído (decisão de Marlon, 04/11/2026) | [Construído] a fila; [Estrutura] o envio |
| Fechar vendas por ingrediente | A gerência marca um ingrediente em falta (ex.: ovo), hoje pelo botão em Estoque > Alertas; o sistema mostra os sabores que o usam e os marca como fechados. **O fechamento vale para o balcão e para o canal:** `POST /pedidos` responde 409 com o sabor e o ingrediente; `POST /pedidos/calcular` não recusa, devolve `aviso_venda_fechada` para a tela deixar remover o item; `GET /produtos` traz `venda_fechada` e `motivo_fechada` (a tela desabilita o sabor). O cartão "Vendas fechadas agora" (em Estoque > Alertas, lê `GET /vendas-fechadas`) tem o botão Reabrir. O varredor compara o mapa com o que deveria estar pausado no canal e corrige a diferença (pausar ou reabrir), com erro registrado por produto. Reabrir faz o inverso. Pedido com sabor fechado não é aceito sozinho | [Construído] o fechamento; [Pendente] a chamada de pausar da API |
| Alerta de estoque | Ingrediente **negativo**, **zerado**, **para repor** (ponto de pedido) ou **abaixo do mínimo** (estoque mínimo do cadastro), nesta ordem de gravidade, para tratativa física ou ajuste. Vale para qualquer item com estoque mínimo. Todas as faixas têm o botão "Fechar vendas dos sabores"; no zerado e no negativo, mostra também quantos sabores usam o item. No BI, zerado ou negativo é alerta de gravidade alta | [Construído] |
| Estoque negativo | Permitido: a baixa automática pela ficha técnica e a saída manual de perda e de consumo interno não são barradas por falta de saldo. A **transferência** entre locais continua bloqueada sem saldo | [Construído] |
| Cancelamento | Existe no Anota Ai; o sistema ainda não avisa | [Pendente] |
| Limite de chamadas | Uma consulta por segundo pode passar do limite deles | [Pendente] perguntar no chamado |

Fatos confirmados pelo manual de uso do Anota Ai: [Anota_Ai_Fatos_do_Manual.md](../../arquitetura/Anota_Ai_Fatos_do_Manual.md). O que só a documentação da API responde: endereços, autenticação, formato do pedido, identificador do pedido, como o ID externo do produto e a forma de pagamento aparecem, chamadas de aceitar, pronto, finalizar, cancelar e pausar produto.

O **iFood** fica para depois: o menu Canais é genérico (um canal por aba, mesmo desenho de fila e mapa) e o iFood vem desligado. Não há adaptador: ligá-lo não faz nada. [Pendente] acesso ao portal.

### 7.3 Parâmetros da loja

Ficam em Administrativo > Parâmetros, com histórico. Só administrador e proprietário editam. Os principais:

| Grupo | Parâmetros |
|---|---|
| Vendas | formas de pagamento aceitas, limites de desconto por perfil (atendente, subgerente, gerente; vazio = 0, qualquer desconto pede autorização), taxa de entrega, vender só com caixa aberto |
| Entregas | valor padrão por entrega, diária padrão do entregador |
| Caixa | fundo de troco padrão, tolerância de diferença, limite de sangria sem gerente |
| Produção | tempo de forno (2 min), pizzas por vez no forno, minutos de montagem e de acabamento, pizzaiolos ativos, deslocamento da entrega (estimativa de entrega), tamanho de massa do calzone |
| Estoque e compras | dias de alerta de validade (7), perda padrão das fichas (10%), valor de compra que exige aprovação |
| Contas, imobilizado e RH | valor de título que exige aprovação, valor mínimo de bem, valor de ordem de serviço que exige aprovação, encargos estimados, limite de hora extra |
| BI | meta de CMV (vazio = sem meta), alertas ligados (CMV, estoque, caixa, atraso, manutenção) |

### 7.4 Backup (a cópia diária fora da máquina foi adiada por Marlon)

`python scripts\backup.py` faz `pg_dump`, copia para as pastas de `BACKUP_DIRS_EXTRA` e mantém os últimos 30. O painel tem o botão "Fazer backup agora" (`sistema.backup.rodar`) e mostra o último backup. Testar a restauração sem tocar no banco em uso: `python scripts\restaurar_em_teste.py <arquivo.dump> pizzaria_restauracao_teste`. A rotina diária fora da máquina está adiada; até lá, rodar ao fechar o dia e copiar para um pen drive.

### 7.5 Solução de problemas

| Sintoma | Verificar |
|---|---|
| Tablet não abre a página | `start_api.bat` aberto, IP do PC, regra do firewall para rede privada |
| "Erro de conexão com o banco" ou `/health` 503 | Serviço do PostgreSQL parado ou senha errada no `set_env.bat` |
| 429 no login | 5 falhas em 15 minutos; aguardar |
| "Troque a senha antes de continuar" | Primeiro acesso ou senha redefinida |
| Porta ocupada | `stop_api.bat` mostra o PID; `taskkill /PID <pid> /F` |
| Varredor não liga | Normal enquanto `ANOTAAI_URL` e `ANOTAAI_TOKEN` estiverem vazios (o log diz "Varredor de canais desligado") |
| Baixa de estoque não aconteceu | Estoque > Alertas mostra pendências "sem ficha" e "erro de baixa"; a produção nunca é travada por isso |

---

## 8. Testes e qualidade

- Suíte pytest em `sistema/tests/` (20 arquivos de teste, incluindo `test_vendas_fechadas.py`, `test_acesso_rigido.py` com a matriz de rota por perfil e `test_varredor.py` com adaptador falso). O resultado da última execução completa fica registrado no PR #2.
- Exige PostgreSQL local; o banco de teste precisa terminar em `_teste` e é recriado a cada execução. Variáveis `TEST_DB_PASS`, `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_USER`, `TEST_DB_NAME`.
- Rodar: `python -m pytest -q` (cerca de 5 minutos).
- **Regra permanente do projeto (03/11/2026):** todo código passa por dois revisores, um cego (sem contexto) e outro conferindo contra o código e os documentos aprovados. Os relatórios de QA cego de cada fatia estão em `sistema/docs/`.

---

## 9. Dos 9 módulos às 3 áreas

| Módulo do Plano Macro | Onde ficou | Documento de origem |
|---|---|---|
| 0 Núcleo | Comum (login, Meus dados) e Administrativo > Usuários, Parâmetros, Auditoria | [01_Nucleo_e_Vendas.md](../../modulos/01_Nucleo_e_Vendas.md) |
| 6 Vendas | Vendas > Pedidos, Clientes, Entregadores, Canais | [01_Nucleo_e_Vendas.md](../../modulos/01_Nucleo_e_Vendas.md) |
| 7 Produção | Produção (uma tela por função) | [02_Producao.md](../../modulos/02_Producao.md) |
| 8 Fechamento de Caixa | Vendas > Caixa e entregas | [03_Fechamento_de_Caixa.md](../../modulos/03_Fechamento_de_Caixa.md) |
| 3 Estoques e Compras | Administrativo > Estoque e Compras | [04_Estoques_e_Compras.md](../../modulos/04_Estoques_e_Compras.md) |
| 4 Contas e Fluxo de Caixa | Administrativo > Contas | [05_Contas_e_Fluxo_de_Caixa.md](../../modulos/05_Contas_e_Fluxo_de_Caixa.md) |
| 5 Custos | Administrativo > Custos; Fichas e etapas | [06_Custos.md](../../modulos/06_Custos.md) |
| 2 Imobilizado | Administrativo > Imobilizado | [07_Imobilizado.md](../../modulos/07_Imobilizado.md) |
| 1 RH | Administrativo > RH; Meus dados para todos | [08_RH.md](../../modulos/08_RH.md) |
| 9 BI | Administrativo > Painel e BI | [09_BI.md](../../modulos/09_BI.md) |

A estrutura de menus aprovada está em [01_Estrutura_de_Menus.md](../../menus/01_Estrutura_de_Menus.md). Diferenças entre o desenho de menus e o que está construído hoje: Entregas segue dentro de "Caixa e entregas", Retiradas e Painel de operação ainda não têm menu próprio, Etapas segue em "Fichas e etapas", e a consulta de Perdas e refações ainda não existe.

---

## 10. Pendências

| # | Pendência | Depende de |
|---|---|---|
| 1 | Token e documentação da API do Anota Ai (aceitar, criar pedido, pronto, finalizar, cancelar, pausar produto, limite de chamadas) | Marlon, por chamado no Anota Ai |
| 2 | iFood | Acesso ao portal |
| 3 | Nuvem e HTTPS | Decisão de Marlon; hoje não é necessário |
| 4 | Teste da impressora térmica Bluetooth pelo navegador do tablet | Marlon, na loja |
| 5 | Backup diário fora da máquina | Adiado por Marlon |
| 6 | Aviso de cancelamento ao Anota Ai | API |
| 7 | Cópia em C:\Maria Gabriela\Pizzaria | Pasta disponível |
| 8 | Valor por entrega diferente do padrão só pela API (sem tela) | Decidir se precisa de tela |
| 9 | Novos botões do pizzaiolo com a pizza ativa (Finalizada a montagem; Montagem errada no sabor; Problemas no formato/esteira; Sem ingredientes), definidos por Marlon em 04/11/2026; a pizza errada no forno pode ser vendida avulsa e há alerta para massa e acabamento | Em implementação no PR #2; manuais atualizados quando terminar |
| 10 | Itens do cardápio ainda pendentes: nomes de abreviações, fichas de bordas, adicionais e bebidas, massa, etapas, tempos, fator de correção | Marlon |

**Recomendação:** antes do primeiro dia de uso, priorizar o teste da impressora e o pedido do token do Anota Ai, porque são os dois pontos que podem mudar o desenho (caminho de impressão e formato do pedido); o resto do sistema já roda na loja sem eles.
