# QA cego da fatia 1B2 (itens, fichas técnicas, etapas)

Escopo lido: api/routers/receitas.py, parte final de api/schemas.py, api/security.py, api/services/parametros.py, migrations_pg/003_fichas_e_etapas.sql, frontend/static/app.js (abaFichas), tests/test_fichas.py.
Executado: `tests/test_fichas.py` (6 passam) e um script de prova em /tmp/qa1b2/test_prova.py (fora do repositório, nenhum arquivo do repositório foi alterado).
Marca "[suposição]" indica o que não foi executado de ponta a ponta.

## Resumo dos pontos que passaram (verificados)

- Permissões: atendente, massa, pizzaiolo e acabamento recebem 403 em itens, fichas e etapas; perfil desconhecido é negado; `deve_trocar_senha` bloqueia (security.py linhas 142 a 150).
- NUL e caracteres de controle em nome: 422. NFD vira NFC e colide com o NFC (409). Maiúscula colide (409).
- Quantidade acima de 999999999,9999 e tempo acima de 9999,99: 422. Ids gigantes (10**30) em caminho e corpo: 404 ou 400, sem 500.
- Gatilho do banco recusa UPDATE e DELETE em ficha_versao e ficha_linha. Perda padrão em branco usa 10; com o parâmetro em 0, grava 0.00 (correto).
- CSP sem unsafe-inline (main.py linha 70). O front só usa `h()` com nó de texto; não vi `innerHTML`.
- SQL parametrizado; os únicos f-strings montam nomes de coluna vindos do schema (`sets`) ou constantes.

## Achados

### 1. [ALTA] A leitura da ficha arredonda a quantidade para 2 casas e a edição corrompe o dado

- Arquivo: api/routers/receitas.py linha 101 (`fmt(r["quantidade"])`), api/services/dinheiro.py (`fmt` quantiza com `CENTAVO`, 0.01). Coluna é NUMERIC(14,4).
- Prova: salvei quantidades 0,0125 / 0,004 / 1,2345. O banco guardou 0.0125, 0.0040, 1.2345. A resposta do PUT e do GET devolveu "0.01", "0" e "1.23". O front (app.js linha 497) preenche o campo com esse valor devolvido; ao clicar em Salvar de novo, a ficha grava 0,01 / 0 / 1,23 em silêncio (e "0" dá 422 e o usuário não entende por quê).
- Impacto: pizzaria usa gramas e quilos (0,25 kg ok, mas 0,0125 kg de orégano não). Qualquer quantidade com 3 ou 4 casas é exibida errada e perde precisão na primeira edição. Quando entrar custo, o custo calculado do banco e o mostrado divergem.
- Correção: formatar quantidade com `Decimal.normalize`/`format(..., "f")` sobre o valor NUMERIC original (4 casas, tirando zeros à direita), nunca com `fmt` de reais. Teste: ida e volta de "0,0125".

### 2. [MÉDIA] Ciclo de preparos não é detectado sob concorrência

- Arquivo: api/routers/receitas.py linhas 133 a 145 (`_tem_ciclo` e `_salvar`), sem lock entre a checagem e o INSERT.
- Cenário: A e B são preparos. Duas requisições simultâneas, `PUT preparo/A [B]` e `PUT preparo/B [A]`. Simulei a intercalação com duas conexões: as duas chamadas de `_tem_ciclo` retornam False antes de qualquer commit; depois as duas versões entram e formam A contém B contém A. Em READ COMMITTED nada impede.
- Impacto: o cálculo futuro de custo e baixa recursiva entra em laço infinito.
- Correção: no início de `_salvar` para `preparo`, `SELECT pg_advisory_xact_lock(<chave fixa de ficha de preparo>)` (um lock global basta nesta loja) antes da checagem; a checagem passa a ser serializada. Adicionar teste com duas threads.
- Observação: a checagem em si está correta para ciclos diretos e indiretos (teste cobre A, B).

### 2b. [BAIXA] `_tem_ciclo` ignora loja_id e lê a versão mais recente sem filtrar

- receitas.py linhas 115 e 117. Em uma loja só é inócuo; se virar multiloja, filtrar por `loja_id`. [suposição sobre multiloja futura]

### 3. [MÉDIA] Item inativado depois de usado trava a ficha inteira e some da tela

- Arquivos: receitas.py linhas 129 a 132; app.js linhas 495 e 496.
- Prova (script): ficha de produto com itens X e A; inativei X. O GET ainda devolve X na ficha. Reenviar exatamente a mesma ficha dá 400 "Há item inexistente ou inativo". A ficha não aparece na lista de qualidade (continua "com ficha").
- Front: `ativos` só tem itens ativos, então `item.value = l.item_id` não casa nenhuma opção (select fica sem seleção, valor ""), e `Number("")` vira 0. O usuário vê uma linha com select vazio e ao salvar recebe a mensagem 400 sem saber qual linha. [parte do front deduzida da leitura do código, não executada em navegador]
- Impacto: para mudar a quantidade de queijo, o gerente precisa descobrir e apagar o item inativo, apagando um ingrediente que talvez ainda se use. Também permite inativar um preparo ou insumo em uso sem aviso.
- Correção: (a) ao salvar, aceitar item inativo que já estava na versão atual (só recusar inativo novo); (b) o front deve incluir o item inativo da linha existente nas opções, marcado como "(inativo)"; (c) incluir em /fichas/qualidade uma lista "fichas com item inativo"; (d) avisar ao inativar item que está em ficha vigente.

### 4. [MÉDIA] Etapa inativada depois de usada: mesmo problema no modelo e na exceção

- Arquivos: receitas.py linhas 248 a 253 (`_validar_etapas`), 240 a 245 (`_passos` não devolve `ativo`); app.js linhas 548 e 553.
- Prova: inativei a primeira etapa do modelo padrão. `GET /modelo-etapas/pizza` continua trazendo a etapa; reenviar o modelo como está dá 400. No front o select de `ativas` não tem a opção, vira vazio e `Number("")` é 0.
- Impacto: o modelo de pizza fica impossível de salvar até apagar a etapa inativa, e produtos continuam "com etapas" mesmo que o modelo só tenha etapas inativas (a consulta de produtos_sem_etapas, linhas 328 a 331, só testa existência de linha em etapa_modelo).
- Correção: igual ao 3: tolerar inativa que já está na lista salva, devolver `ativo` em `_passos`, mostrar "(inativa)" no front, e contar só etapas ativas em /fichas/qualidade. Ou recusar inativar etapa em uso (409 com a lista de onde é usada).

### 5. [MÉDIA] /fichas/qualidade não lista borda e adicional sem ficha por tamanho

- Arquivo: receitas.py linhas 316 a 332. A resposta tem quatro chaves (produtos, preparos, bases, produtos_sem_etapas) e nenhuma para adicional.
- Regra esperada: adicional e borda têm ficha por tamanho e "sem ficha aparece em qualidade, nunca como custo zero". Uma borda ativa sem ficha Grande ou Broto passa despercebida e, na fatia de custo, tende a virar custo zero.
- Correção: nova chave `adicionais_sem_ficha` com (adicional ativo, tamanho) cuja versão mais recente não tem linha; mostrar no front (subQualidade, linhas 582 a 590).
- Também faltam: produto com ficha cujas linhas apontam item inativo (ver 3) e preparo usado em ficha mas sem ficha própria (preparo "vazio" referenciado). [este último é sugestão de regra, não verificado como exigência]

### 6. [MÉDIA] Edição concorrente sem controle de versão: o último a salvar apaga as mudanças do outro

- Arquivos: receitas.py `_salvar` (126 a 145), app.js linha 510.
- Cenário: duas pessoas abrem a ficha de uma pizza (versão 10). Uma salva (versão 11). A outra, ainda com a tela da versão 10, salva (versão 12) e a mudança da primeira some da ficha vigente (só fica no histórico). Nada avisa. A ordem "vale a mais recente" usa `id`, que é a ordem de alocação, não de commit (duas transações podem gravar fora de ordem). [a parte da ordem de commit é raciocínio, não executada]
- Correção: o PUT recebe `versao_base` (a `versao_id` lida); se diferente da atual, 409 "A ficha mudou desde que você abriu". Para ordenar de verdade, serializar por dono com `pg_advisory_xact_lock(hash do dono)`.

### 7. [MÉDIA] Front: respostas fora de ordem podem gravar a ficha de um item em outro

- Arquivo: app.js linhas 488 a 520. `abrir()` lê `sel.value` no clique de Salvar (linha 510), não o caminho com que a tela foi montada. `abrir` não descarta resposta antiga.
- Cenário: o usuário escolhe o produto A (GET lento), troca para B (GET rápido, tela de B montada), a resposta de A chega depois e substitui o editor por linhas de A, enquanto o select mostra B. Salvar faz `PUT /fichas/B` com as linhas de A. [raciocínio sobre ordem de resposta; não reproduzido em navegador]
- Correção: `const caminho = sel.value` capturado dentro de `abrir`, usado no PUT; contador de sequência (`const meu = ++seq; ... if (meu !== seq) return;`) depois de cada await.

### 8. [BAIXA] Gatilho só cobre UPDATE e DELETE: dá para inserir linha em versão antiga e para truncar

- Arquivo: migrations_pg/003_fichas_e_etapas.sql linhas 48 a 53.
- Prova (conexão direta no banco de teste): `INSERT INTO ficha_linha (versao_id, ...)` apontando para a primeira versão foi aceito; `TRUNCATE ficha_linha CASCADE` foi aceito (desfiz com rollback). A auditoria já tem gatilho de TRUNCATE na 001 (linhas 78 a 80), as fichas não.
- Impacto: a versão deixa de ser imutável (uma versão antiga ganha ingrediente depois de usada em venda/produção futura); o histórico perde valor de prova.
- Correção: BEFORE TRUNCATE em ficha_versao e ficha_linha; BEFORE INSERT em ficha_linha que recusa quando `versao_id` não é a versão mais recente do dono ou quando a versão tem mais de uma transação (ex.: comparar `xmin` com `txid_current()` da versão). Teste no estilo de `test_versoes_de_ficha_sao_so_insercao`.

### 9. [BAIXA] Ficha aceita dono inativo

- receitas.py `_dono` (linhas 68 a 90): produto, adicional e preparo inativos aceitam PUT (provado: 200 para produto inativo e para preparo inativo). Não é erro de integridade grave (o produto inativo sai da qualidade), mas a tela de fichas lista produtos inativos. Decidir a regra: recusar com 400 ou permitir e documentar.

### 10. [BAIXA] A ordem das linhas da ficha não é a ordem digitada

- receitas.py linha 99 (`ORDER BY i.nome`); a tela monta na ordem do servidor. Não existe coluna de ordem em ficha_linha. A ordem de montagem importa no chão da loja (molho, queijo, recheio) e o usuário não consegue fixá-la. Se a ordem é requisito, adicionar `ordem` em ficha_linha; senão, documentar que é alfabética.

### 11. [BAIXA] Perda padrão é congelada no dado e a tela mostra o valor como se tivesse sido digitado

- receitas.py linha 135 e 142; app.js linha 498. Ao salvar com perda em branco, grava o padrão vigente (10.00). Ao reabrir, o campo mostra "10,00", e salvar de novo mantém 10 fixo; uma mudança futura do parâmetro não alcança essa ficha. Isso pode ser o desejado (versão guarda o valor usado), mas o texto do campo ("padrão") some e o usuário acredita que "em branco" segue o parâmetro. Decisão a registrar; se a intenção é seguir o parâmetro, guardar NULL e resolver na leitura/custo.
- `or "10"` (linha 135) também transforma um parâmetro vazio em 10 duplicando o padrão do catálogo; usar uma constante única.

### 12. [BAIXA] Nome aceita espaços internos repetidos e espaço não separável

- schemas.py `_nome` (linhas 190 a 195): só faz NFC e `strip`; pela leitura, "Queijo  mussarela" (dois espaços) e "Queijo mussarela" seriam dois itens distintos [não executado; o script testou só um espaço a mais em posição diferente]. Normalizar `" ".join(v.split())`. A unicidade usa `lower(nome)` no banco; se o servidor PostgreSQL não usar locale UTF-8 o `lower` de letras acentuadas pode falhar [suposição, no banco de teste maiúscula acentuada colidiu corretamente].

### 13. [BAIXA] Itens não permitem corrigir classe ou unidade

- schemas.py `ItemUpdate` só aceita nome e ativo. Um item cadastrado com unidade errada só pode ser inativado e recadastrado, e aí some das fichas (ver 3). Considerar permitir correção de unidade enquanto o item não estiver em ficha, e mostrar no front o motivo.

### 14. [BAIXA] Front: etapas sem "Descer", item na própria ficha e mensagens de erro

- app.js linha 551: só há "Subir"; para descer a última etapa é preciso subir a seguinte.
- A ficha de preparo oferece o próprio preparo como ingrediente (a lista `ativos` não o exclui); o backend recusa com 400, a tela poderia evitar a opção.
- Linha duplicada de item gera 422 genérico "Até 60 linhas, sem repetir o item." sem indicar a linha.

### 15. [BAIXA] Operações sem tradução de erro e corrida no "iniciar padrão"

- receitas.py linhas 228 a 234: checa "já tem etapa" e insere sem lock. Duas chamadas simultâneas: a segunda recebe 409 por `uq_etapa_nome` (as etapas usam `_grava`), mas os INSERT de `etapa_modelo` (linha 234) usam `conn.execute` direto; uma violação ali viraria 500. Também `DELETE`/`INSERT` de `salvar_modelo` e de `salvar_etapas_do_produto` concorrentes na mesma chave: a segunda cai em `UNIQUE (tipo, ordem)`, traduzido por `_grava` como 409 (aceitável). Usar `pg_advisory_xact_lock` no iniciar-padrão e trocar para `_grava`. [não reproduzido com threads]
- `salvar_modelo` valida as etapas antes do DELETE sem travar: uma etapa inativada entre a validação e o INSERT entra no modelo [raciocínio].

## Lacunas de teste (tests/test_fichas.py)

- Nenhum teste de ida e volta de quantidade com 3 ou 4 casas (teria pego o achado 1; o teste usa só "75,5").
- Nenhum teste de ciclo concorrente, de ciclo indireto com três preparos, nem de ciclo passando por preparo inativo.
- Nenhum teste de item inativado depois de usado (reenviar ficha vigente), nem de etapa inativada depois de usada.
- Nenhum teste de `adicional` na qualidade, de `bases_sem_ficha`, de `preparos_sem_ficha` nem de `produtos_sem_etapas`.
- Nenhum teste de INSERT em versão antiga ou TRUNCATE; só UPDATE e DELETE.
- Nenhum teste de valores nos limites (999999999,9999; 9999,99; perda 100) nem de NFD/NUL/espaços em nome de item e etapa.
- Nenhum teste de que `perda_padrao_pct` alterado vale na próxima ficha, nem de perda 0 explícita (hoje "0" cai no ramo `is not None`, correto, mas sem teste).
- Permissões testadas só em GET /itens, GET e PUT de ficha de produto e GET /etapas; faltam POST/PATCH de itens e etapas, modelo, exceção de produto e /fichas/qualidade para os perfis negados, e `deve_trocar_senha`.
- Sem teste de front (ordem das linhas, select de item inativo, resposta fora de ordem).

## Resumo (duas linhas)

Regras centrais de permissão, versões só de inserção por UPDATE/DELETE, perda padrão e validação de entrada estão corretas, mas a leitura da ficha arredonda quantidade a 2 casas e corrompe a edição (alta), e há ciclo de preparos possível sob concorrência, item/etapa inativados que travam o salvamento e adicional fora da qualidade (médias).
Faltam testes de ida e volta de quantidade, concorrência, inativação depois do uso e TRUNCATE/INSERT em versão antiga; os 6 testes existentes passam.
