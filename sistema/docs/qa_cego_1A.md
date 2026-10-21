# QA cego da fatia 1A (Núcleo)

Revisão independente de `/home/claude/pizzaria-sistema/sistema`. Nenhum arquivo do código foi alterado.
Testes existentes: 35 passam (`pytest -q`, banco `pizzaria_teste`). Ataques próprios rodados contra a API real (uvicorn, banco `pizzaria_qa_teste`), scripts em `/tmp/qa_cego/`.

Legenda: CONFIRMADO = reproduzido rodando; LEITURA = confirmado lendo o código; SUSPEITA = não reproduzido.

## Resumo por severidade

| Severidade | Quantidade |
|---|---|
| Crítico | 0 |
| Alto | 1 |
| Médio | 9 |
| Baixo | 13 |
| Suspeitas | 4 |

## O que foi conferido e está correto (CONFIRMADO)

- Login: 401 com texto idêntico para usuário inexistente, senha errada e inativo; tempos 0,350 s, 0,334 s e 0,357 s (bcrypt sempre roda, sem enumeração por tempo).
- Bloqueio 429 na 6ª tentativa (após 5 falhas), inclusive com senha certa depois; rajada de 30 tentativas simultâneas na mesma chave: 1 contada, 29 recebem 429 (o limite não é furado por concorrência).
- Token guardado como SHA-256; sessão cai na hora ao desativar, ao mudar perfil e ao redefinir senha (token antigo devolve 401).
- Proprietário recebe 403 ao criar, alterar, reativar, promover para administrador e redefinir senha de administrador; auto-promoção a administrador também recusada.
- PATCH com campos extras (`senha_hash`, `loja_id`, `deve_trocar_senha`) recusado com 422 (extra=forbid). Nomes de coluna do UPDATE dinâmico vêm só do schema; sem injeção.
- Perfis sem permissão recebem 403 em todas as rotas protegidas; sem token 401; usuário com troca pendente recebe 403 fora de /auth.
- Front: nenhum innerHTML, texto de usuário só como nó de texto. Payload `<img onerror>` gravado em `loja_nome` fica inofensivo no código lido (não executei navegador).
- `/api/inexistente` devolve 404 JSON; CSP sem unsafe-inline; docs desligados.
- Auditoria recusa UPDATE, DELETE e TRUNCATE para papel comum e não guarda senha.
- IDOR: todas as consultas de usuário filtram por `loja_id`; `/api/usuarios/99999999999999999999` devolve 404 limpo.

## Achados

### ALTO

#### A-01. Corrida deixa a loja sem administrador ativo (CONFIRMADO)
- Arquivo: `api/routers/usuarios.py` linhas 59 a 67.
- Problema: a checagem "restantes > 0" (SELECT count) e o UPDATE não são atômicos e não há trava. Dois administradores ativos que se desativam ao mesmo tempo passam ambos na checagem (cada um enxerga o outro como restante) e a loja fica com 0 administradores ativos. O mesmo vale para rebaixar de perfil. Não existe garantia no banco.
- Reprodução: `/tmp/qa_cego/race.py` (duas threads com Barrier: adm1 faz PATCH `{"ativo":false}` em adm2 e adm2 em adm1). Resultado na 2ª tentativa: ambos 200 e `count(administrador ativo) = 0`.
- Consequência: critério 2 violado; recuperação só por `scripts/criar_admin.py --promover` no servidor.
- Correção: dentro da mesma transação, antes do count, travar os administradores (`SELECT id FROM usuario WHERE loja_id=%s AND perfil='administrador' AND ativo ORDER BY id FOR UPDATE`) ou `pg_advisory_xact_lock` fixo para toda mudança de administrador. Defesa no banco: constraint trigger deferida que recusa o commit se não sobrar administrador ativo. Observação: sem corrida, a regra das linhas 59 a 64 é código morto (quem age é sempre um administrador ativo e diferente do alvo, então `restantes >= 1`), por isso nunca foi exercitada pelos testes (ver M-09).

### MÉDIO

#### M-01. Auditoria "só inserção" é contornável por quem tem a credencial do app (CONFIRMADO)
- Arquivo: `migrations_pg/001_nucleo.sql` linhas 69 a 80; `api/config.py` linha 17 (usuário padrão `postgres`).
- Problema: a proteção é só trigger. Sem REVOKE UPDATE/DELETE/TRUNCATE e sem papel restrito criado pela migration. Rodando como superusuário/dono: `SET session_replication_role = replica; UPDATE auditoria ...` funcionou, e `ALTER TABLE auditoria DISABLE TRIGGER ...` seguido de DELETE funcionou. `has_table_privilege(current_user,'auditoria','UPDATE')` = true.
- Correção: migration cria papel de aplicação que não é dono (`pizzaria_app`), com apenas SELECT e INSERT em `auditoria` (e USAGE nas sequences); REVOKE UPDATE, DELETE, TRUNCATE de PUBLIC; dono do schema distinto (já há `MIGRATE_DB_USER`); documentar que o app nunca roda como `postgres`. Teste: conectar com o papel do app e tentar UPDATE/DELETE/TRUNCATE/DISABLE TRIGGER.

#### M-02. PATCH /usuarios com campo nulo gera 500 (CONFIRMADO)
- Arquivos: `api/schemas.py` linhas 79 a 96 (`Optional[...] = None` aceita `null` explícito); `api/routers/usuarios.py` linhas 51, 66 e 67.
- Reprodução: `PATCH /api/usuarios/5` com `{"nome":null}`, `{"perfil":null}` ou `{"ativo":null}` (como administrador). Resposta 500; log: `NotNullViolation`.
- Correção: no schema, rejeitar `None` quando o campo vier no corpo (validador com `model_fields_set`, ou tipos não opcionais com `exclude_unset`). No router, envolver o UPDATE com `try/except psycopg.Error` como no `criar`. Teste de regressão para os 3 campos.

#### M-03. Senha com mais de 72 bytes (acentos) gera 500 em criar usuário, redefinir e trocar senha (CONFIRMADO)
- Arquivos: `api/schemas.py` linhas 13 a 18 (limite em caracteres, não em bytes); `api/security.py` linha 34; chamadas em `usuarios.py` 38 e 82, `auth.py` 55.
- Reprodução: `POST /api/usuarios` com `"senha": "ç"*72` (144 bytes). Resposta 500, log `ValueError: password cannot be longer than 72 bytes` (bcrypt 5.0.0). Confirmado só em criar usuário; redefinir e trocar senha usam a mesma função e o mesmo validador (LEITURA).
- Correção: validar `len(v.encode("utf-8")) <= 72` e devolver mensagem de validação (422). Teste com acentos e emoji.

#### M-04. Caractere NUL em texto gera 500 (CONFIRMADO)
- Arquivos: `api/schemas.py` 84 a 89 e `usuarios.py` 67 (PATCH `nome` sem captura de erro de banco); `api/services/parametros.py` 62 a 65 (`loja_nome`); `api/routers/auth.py` 18 e 19 (`usuario` do login sem validação de tamanho nem de caracteres).
- Reprodução: `PATCH {"nome":"a\u0000b"}`, `PUT /parametros/loja_nome {"valor":"a\u0000b"}`, `POST /auth/login {"usuario":"a\u0000b",...}`: todos 500 (`DataError: PostgreSQL text fields cannot contain NUL`). O `criar` trata (400), os outros não.
- Correção: validador comum que recusa `\x00` e demais caracteres de controle em todo texto; `LoginIn.usuario` com `max_length` e a mesma regex do cadastro (usuário fora do padrão vira 401 sem tocar o banco); capturar `psycopg.Error` em todas as escritas.

#### M-05. Parâmetro `decimal_pos` é gravado em notação científica (CONFIRMADO)
- Arquivo: `api/services/parametros.py` linha 75 (`Decimal.normalize()`).
- Reprodução: `PUT /parametros/forno_tempo_min {"valor":"10"}` grava `"1E+1"`; `"100"` grava `"1E+2"`. O valor gravado e devolvido deixa de ser um número legível e quebra qualquer consumidor que espere o formato do catálogo (o padrão é `"2"`).
- Correção: formatar com `format(v.normalize(), "f")` ou quantizar para casas fixas; teste com 10, 100 e 2,50.

#### M-06. Limite de 1 MB do corpo é contornável com transferência em partes (CONFIRMADO)
- Arquivo: `api/main.py` linhas 42 a 44 (só olha `Content-Length`).
- Reprodução: `POST /api/auth/login` com corpo chunked de 30 MB sem Content-Length: aceito e processado (401). Com Content-Length de 2 MB: 413. A rota de login é anônima, então o alvo é a memória do processo.
- Correção: aplicar o limite lendo o fluxo (middleware ASGI que conta bytes e aborta com 413), ou limite no proxy; tamanho máximo também nos campos (`usuario` e `senha` do login).

#### M-07. Backups simultâneos colidem no mesmo arquivo e não há trava (CONFIRMADO)
- Arquivo: `api/services/backup.py` linhas 29 a 38.
- Problema: o nome tem resolução de segundos. 5 cliques quase simultâneos geraram 5 respostas "sucesso" com o MESMO arquivo; o tamanho final (21707) difere do primeiro reportado (21567), isto é, um pg_dump sobrescreveu o outro enquanto era copiado. Sem exclusão mútua. Além disso a requisição é síncrona (até 900 s) e segura uma conexão do pool e uma thread.
- Correção: `pg_try_advisory_lock` (409 "backup em andamento"), nome com milissegundos ou sufixo único, gravar em `.tmp` e renomear só após sucesso, apagar arquivo parcial se o pg_dump falhar ou estourar o tempo, e de preferência rodar fora da conexão do request.

#### M-08. Usuário de login sem limite: 500 e inchaço da tabela de falhas (CONFIRMADO)
- Arquivos: `api/schemas.py` 25 a 32; `api/security.py` 60, 61 e 83; migration linha 39 (índice em `chave`).
- Reprodução: login com `usuario` de 60 KB incompressível: 500 (`ProgramLimitExceeded: index row requires 60032 bytes, maximum size is 8191`). Com 100 KB repetitivo: 401 e a chave inteira é gravada em `login_falha` (até cerca de 1 MB por tentativa). Um atacante anônimo varia o nome para encher o disco; a limpeza só apaga linhas com mais de 1 dia.
- Correção: `max_length` e regex no `LoginIn.usuario`; gravar `sha256(chave)` em vez da chave; limitar linhas por IP.

#### M-09. Lacunas relevantes nos testes (LEITURA)
- `tests/test_permissoes_usuarios.py`:
  - `test_redefinir_senha_forca_troca_e_encerra_sessoes` descarta o cabeçalho (`entrar(...)[0]`) e nunca prova que a sessão antiga caiu.
  - `test_nao_desativa_a_si_mesmo_nem_o_ultimo_administrador` só exercita a regra de auto-desativação; a regra do último administrador (usuarios.py 59 a 64) nunca é atingida.
  - Proprietário só é testado criando administrador; faltam PATCH, reativar, promover e redefinir senha de administrador, e alteração do próprio perfil.
  - Sem teste de PATCH com `null`, campos extras ou corpo vazio.
- `tests/test_auth.py`: `test_token_guardado_como_hash` só confere que o token cru não está na tabela, não que é o SHA-256; faltam testes de sessão expirada, de usuário inativo com senha certa contando falha, de concorrência no login e de 429 em `/auth/trocar-senha`.
- Sem testes de concorrência (último administrador, backup), de entrada hostil (NUL, unicode, tamanho), de `deslocamento` enorme, de papel de banco restrito para a auditoria e de formato dos valores de parâmetro (M-05).
- `test_backup_e_restauracao` só confere `count(usuario)` no banco restaurado; não verifica auditoria, triggers nem parâmetros.
- Os testes compartilham um banco e `test_nao_desativa...` desativa todos os administradores existentes (acoplamento por ordem de execução).

### BAIXO

- B-01. Rajada de login degrada o serviço (CONFIRMADO, latência): 60 logins simultâneos com usuários distintos, cada um segurando conexão do pool durante o bcrypt (`auth.py` 17 a 24); `/auth/me` de um administrador levou 4,3 s durante a rajada (sem 503 nessa carga). Mitigar: limite por IP antes do bcrypt e liberar a conexão antes de verificar a senha.
- B-02. Bloqueio por (IP, usuário) (LEITURA, concorrência CONFIRMADA): a chave inclui o IP, então não há limite por usuário nem por IP no total (um mesmo usuário atacado de muitos IPs, ou um IP testando muitos usuários, não é contido), e em concorrência a requisição seguinte recebe 429 sem ser contada (29 de 30). Atrás de NAT, quem erra 5 vezes bloqueia todos do mesmo IP para aquele usuário. Avaliar contador adicional por usuário (limite mais alto) e por IP.
- B-03. Limpar um parâmetro apaga o padrão do catálogo (CONFIRMADO): `PUT /parametros/forno_tempo_min {"valor":null}` passa a devolver `null`, e não `"2"` (`services/parametros.py` 93 a 98: a linha gravada vence o padrão). Idem para `formas_pagamento_aceitas`. Definir se "limpar" deve voltar ao padrão.
- B-04. `deslocamento` enorme na auditoria gera 500 (CONFIRMADO): `GET /api/auditoria?deslocamento=99999999999999999999`, `bigint out of range` (`routers/auditoria.py` linha 14, sem `le`). Correção: `le=1_000_000`.
- B-05. Detalhe técnico em respostas (CONFIRMADO): `database.py` linha 87 devolve o nome da coluna em NotNullViolation; o backup devolve a pasta e o `strerror` (`cópia para /proc/xx/yy falhou: No such file or directory`) e a última linha do stderr do pg_dump (`services/backup.py` 40 e 53), visíveis ao gerente. O aviso de falha deve existir, mas com texto fixo e detalhe só no log.
- B-06. A tela mostra "Backup em dia" em verde mesmo quando todas as cópias extras falharam (LEITURA): `frontend/static/app.js` linha 105 só considera `atrasado`; `copias_falha` só entra no texto. Também não alerta se `copias_ok = 0`.
- B-07. `Decimal` aceita formatos inesperados (CONFIRMADO): `"1_0"` vira 10.00, dígitos árabes viram 12.00, `"1e1"` vira 10.00 (`services/parametros.py` linha 38). Validar com regex ASCII `^\d+([.,]\d+)?$`.
- B-08. Nomes sem filtro de caracteres de controle, quebra de linha ou marcas bidirecionais (LEITURA): `schemas.py` 59 a 64 só valida tamanho; risco de nomes enganosos na auditoria e em relatórios. Vale também para `loja_nome`.
- B-09. Política de senha só de tamanho (LEITURA): `12345678` e a senha igual ao usuário são aceitas (`schemas.py` 13 a 18).
- B-10. Backup: o `.dump` com hashes de senha vai sem criptografia para pasta de nuvem; dump parcial permanece na pasta se o pg_dump falhar ou estourar o tempo e entra na contagem de retenção (`backup.py` 39 a 43 e 56 a 57); nenhuma verificação da cópia (tamanho ou checksum). Arquivo criado com permissão 644.
- B-11. A auditoria não cobre login (sucesso e falha), logout, backup manual nem negativas de permissão; a alteração de usuário grava só o id em `entidade_id`, não o login (`usuarios.py` 71 e 72).
- B-12. `requirements.txt` sem versões fixas (fastapi, bcrypt, pydantic...), o que já muda comportamento (bcrypt 5 recusa senha acima de 72 bytes). Fixar versões.
- B-13. A redefinição de senha pela interface usa `window.prompt` (`app.js` linha 149): a senha provisória aparece em texto claro na tela. Usar campo `type=password`.

### SUSPEITAS (não reproduzidas)

- S-01. `api/security.py` linha 54: com `CLIENT_IP_HEADER` configurado, usa o PRIMEIRO valor de `X-Forwarded-For`, que o cliente controla quando o proxy apenas acrescenta; permitiria girar o IP e burlar o bloqueio. Usar o último valor confiável. Com o padrão (cabeçalho vazio) não ocorre: 7 tentativas com XFF diferentes foram bloqueadas normalmente.
- S-02. `security.py` linha 70: `hashtext` de 32 bits como chave do advisory lock; colisão entre chaves distintas devolveria 429 indevido (probabilidade baixa).
- S-03. `backup.py` com `pg_dump` de até 15 minutos: a conexão do request fica "idle in transaction" (o SELECT da sessão abriu transação) e ocupa thread e pool; não há `idle_in_transaction_session_timeout`.
- S-04. `backup.py` linha 31: `destino.mkdir` sem captura de `OSError` (pasta sem permissão) geraria 500 sem registro em `backup_registro`.

## Ordem sugerida de correção

1. A-01 (trava e constraint trigger de último administrador).
2. M-01 (papel de banco restrito e REVOKE), M-02, M-03, M-04 (validação de entrada e captura de `psycopg.Error` em todas as escritas).
3. M-05, M-06, M-07, M-08.
4. Testes de M-09 junto com cada correção (concorrência, entrada hostil, papel restrito).
5. Baixos e suspeitas.

## Ambiente de QA

O banco `pizzaria_qa_teste` foi alterado durante os ataques (inclusive a tabela de auditoria, no teste de M-01) e é descartável. O servidor de teste (porta 8197) pode continuar de pé; encerrar pelo PID.
