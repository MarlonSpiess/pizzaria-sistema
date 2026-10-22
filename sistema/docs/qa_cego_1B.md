# QA cego da fatia 1B (cadastros)

Revisor independente. Nenhum arquivo de código ou de teste foi alterado. Os 23 testes de `tests/test_cadastros.py` passam. Provas extras foram feitas com pytest em `/tmp/qa1b/` (fora do repositório), usando só o banco de teste via conftest. Achados marcados como "verificado" foram lidos no código e/ou reproduzidos. "Suposição" indica o que não foi executado.

Regras conferidas e sem defeito achado: meia a meia (35,00 + 50,00 = 42,50), arredondamento para cima por metade (0,03 vira 0,02 + 0,02; 35,01 vira 17,51), Broto só com 1 sabor, borda e adicional somam por tamanho, histórico só de inserção pela API com vigência pelo maior id, nenhum float no caminho do dinheiro (NUMERIC no banco, Decimal no código, texto na saída), SQL sempre parametrizado (os f-strings só interpolam nomes de coluna vindos do schema com `extra="forbid"`), filtro por `loja_id` em todas as leituras, permissões negadas por padrão, produção sem acesso, telefone e endereço fora da auditoria, nenhum `innerHTML` no front.

## Achados

### 1. Média: `GET /clientes?q=%00` devolve 500 (NUL não tratado)
- Arquivo: `api/routers/pessoas.py` linhas 252 a 259 (parâmetro `q` entra em `_like` sem passar pelo filtro de controle do `Base`).
- Verificado: a requisição levanta `psycopg.DataError: PostgreSQL text fields cannot contain NUL` e sai como 500 "Erro interno", com `log.exception` a cada chamada. Qualquer usuário com `clientes.ver` (inclusive atendente) gera ruído de erro e stack trace no log à vontade.
- Correção: validar `q` com `_texto_limpo` (422) ou remover `\x00` antes de usar, e envolver a consulta em tratamento de `psycopg.DataError`.

### 2. Média: lista de clientes truncada em 50 sem aviso e sem paginação
- Arquivo: `api/routers/pessoas.py` linha 252 (limite 50) e `frontend/static/app.js` linha 389 (título "Clientes (N)" usa `lista.length`) e linha 374 (nunca envia `limite`).
- Verificado por leitura: com mais de 50 clientes o título mostra "Clientes (50)" como se fosse o total, e não há botão "mais" nem offset. Cliente além da posição 50 só aparece por busca. Também lista clientes inativos misturados sem filtro.
- Correção: devolver o total (ou `tem_mais`), aceitar `offset` e `ativo`, e mostrar "50 de N" no front.

### 3. Média: resposta antiga da busca de clientes pode sobrescrever a nova (estado do front)
- Arquivo: `frontend/static/app.js` linhas 372 a 399 (`listar` é chamada com debounce, sem número de sequência nem `AbortController`).
- Verificado por leitura: digitar "ana" e logo "ana s" dispara dois GET; se o primeiro responder depois, a tabela mostra o resultado de "ana" com o campo mostrando "ana s". Para o atendente isso pode levar a escolher o cliente errado (endereço de entrega errado).
- Correção: guardar um contador, ignorar respostas fora de ordem, ou abortar a requisição anterior.

### 4. Média: telefone aceita letras e texto solto, e não normaliza DDI
- Arquivo: `api/schemas.py` linhas 197 a 201 (`_telefone` só filtra dígitos).
- Verificado: `"ligar 11 98888-7777 depois"` foi aceito (201) e gravado como `11988887777`. Também `"+55 11 98888-7777"` foi aceito como um segundo cliente distinto (`5511988887777`), então o mesmo aparelho pode ter dois cadastros e `por-telefone` com o formato sem 55 não acha o segundo. Quebra a intenção de "único por loja".
- Correção: recusar qualquer caractere fora de `0-9 espaço ( ) - +`; tratar o prefixo 55 (remover quando o total passar de 11 dígitos e começar com 55) ou decidir e documentar a regra. Teste para cada caso.

### 5. Média: histórico de preço é só de inserção apenas por convenção do código
- Arquivo: `migrations_pg/002_cadastros.sql` linhas 180 a 209 (`preco_produto`, `preco_adicional`).
- Verificado: pela conexão do teste, `UPDATE preco_produto SET valor=1` e `DELETE FROM preco_produto` foram permitidos. A auditoria (migração 001, `trg_auditoria_so_insercao`) tem gatilho que bloqueia UPDATE, DELETE e TRUNCATE, mas as tabelas de preço não. Um bug futuro ou acesso direto reescreve o passado, e o "vale o último" muda sem rastro.
- Correção: criar o mesmo gatilho de só inserção (BEFORE UPDATE OR DELETE e TRUNCATE) nas duas tabelas de preço, mais teste que tenta o UPDATE e espera erro.

### 6. Baixa: nomes duplicados por normalização Unicode (NFC contra NFD)
- Arquivo: `api/schemas.py` linha 183 (`_nome`) com índices `uq_produto_nome`, `uq_adicional_nome`, `uq_categoria_nome`, `uq_entregador_nome`.
- Verificado: "Guaraná" (composto) e "Guaraná" (a + acento combinante) foram aceitos como dois produtos (201 e 201). O índice usa `lower(nome)`, que não unifica as formas. Texto colado de outros sistemas gera cadastros que parecem iguais na tela.
- Correção: `unicodedata.normalize("NFC", v)` em `_nome` e nos textos opcionais.

### 7. Baixa: preço zero é aceito em pizza, categoria e adicional
- Arquivo: `api/services/dinheiro.py` linha 7 e `migrations_pg/002_cadastros.sql` (`CHECK valor >= 0`).
- Verificado: pizza com Grande "0" e Broto "0,00" criada com 201. Um erro de digitação vende de graça sem alerta. Se for intencional (brinde), ignore. Suposição sobre a intenção.
- Correção: exigir `> 0` para produto, ou pedir confirmação explícita para zero.

### 8. Baixa: categoria inativada não afeta seus sabores
- Arquivo: `api/routers/cardapio.py` linhas 63 a 78 e `api/services/preco.py` linhas 338 a 348.
- Verificado: após inativar a categoria, a simulação de um sabor ativo dessa categoria continua com 200. Se "inativar categoria" deveria tirar a linha do cardápio, falta a cascata ou o filtro. Suposição sobre a regra desejada, mas o comportamento é real e sem teste.
- Correção: decidir a regra e testá-la (bloquear com aviso, ou considerar `c.ativo` em `_sabor`).

### 9. Baixa: corrida em `PATCH` de preço sem trava
- Arquivo: `api/routers/cardapio.py` linhas 136 e 146 a 148 (e 203 a 211 para adicionais).
- Verificado por leitura e por teste com 3 PATCH simultâneos (todos 200, três linhas de histórico, vale o de maior id): o resultado fica consistente, mas a comparação "preço igual ao atual" usa leitura sem trava, então a auditoria pode registrar `antes` desatualizado, e o maior id pode não ser o último commit. Impacto pequeno.
- Correção: `SELECT ... FOR UPDATE` na linha do produto antes de ler o preço atual.

### 10. Baixa: mesma pessoa ou telefone inativo gera 409 sem explicação
- Arquivo: `api/routers/pessoas.py` linhas 271 a 277 com `uq_cliente_telefone`; `api/database.py` linha 82.
- Verificado por leitura: cliente inativado mantém o telefone, então cadastrar de novo devolve só "Já existe um registro com esses dados." O atendente não sabe que deve reativar nem qual cadastro. Ele não tem como reativar sem achar o cliente.
- Correção: no 409 de cliente, informar "telefone já cadastrado" e, se inativo, indicar reativar (sem expor endereço).

### 11. Baixa: telefone em URL e query string (log de acesso)
- Arquivo: `api/routers/pessoas.py` linhas 252 e 262 (`/clientes/por-telefone/{telefone}` e `?q=`).
- Suposição, não executado: o log de acesso do servidor HTTP ou de um proxy registra a URL com telefone completo, fora da auditoria mas dentro do espírito de "telefone nunca vai para o log". O código não configura log de acesso próprio.
- Correção: aceitar o telefone por POST/corpo, ou desligar/mascarar o log de acesso nessas rotas.

### 12. Baixa: front envia 0 como id quando nada foi escolhido
- Arquivo: `frontend/static/app.js` linhas 269 (`Number(cat.value)`) e 354 (`Number(s1.value)`).
- Verificado por leitura: sem categoria ativa, o cadastro de sabor manda `categoria_id: 0` e recebe "Categoria não encontrada."; no simulador sem sabor 1 manda `sabor1_id: 0` e recebe "Sabor não encontrado." em vez de pedir a escolha. Sem dano, só mensagem enganosa.
- Correção: validar no front e mostrar "Escolha o sabor" / "Cadastre uma categoria ativa antes".

### 13. Baixa: trocar a categoria no formulário apaga os preços já digitados
- Arquivo: `frontend/static/app.js` linha 267 (`padrao` sobrescreve `g` e `b`, inclusive limpa se a categoria não tem padrão).
- Verificado por leitura: digitar preços e depois mudar a categoria substitui ou zera os campos sem aviso.
- Correção: só preencher campos vazios ou ainda não editados.

### 14. Baixa: busca por cliente com dígitos no nome vira busca por telefone
- Arquivo: `api/routers/pessoas.py` linhas 256 a 258.
- Verificado por leitura: `q="Rua 5"` ou "Maria 2" também acrescenta `telefone LIKE '%5%'`, devolvendo clientes não relacionados. Não pesquisa endereço e não ignora acentos ("jose" não acha "José").
- Correção: usar telefone só se `q` tiver 4 ou mais dígitos e poucos caracteres não numéricos; considerar `unaccent`.

### 15. Baixa: emoji com ZWJ e marcas de formatação são recusados em nomes
- Arquivo: `api/schemas.py` linhas 27 a 31 (categoria Cf).
- Verificado: nome com emoji composto (ZWJ) retorna 422. Pode ser desejado (anti bidirecional). Mensagem genérica não diz qual caractere. Registrado só como decisão a confirmar.

## Lacunas de teste (verificado por leitura de `tests/test_cadastros.py`)
- Nenhum teste de isolamento multi-loja (produto, cliente ou adicional de outra loja devolve 404 em GET, PATCH, histórico e simulação).
- Nenhum teste de concorrência (telefone duplicado simultâneo, PATCH de preço simultâneo).
- Nenhum teste de tentativa de UPDATE/DELETE em tabelas de preço (hoje passaria, achado 5).
- Sem teste de `q` com NUL, `limite` fora da faixa, nem de mais de 50 clientes.
- Telefone: não há teste dos limites de 8 e 15 dígitos aceitos, de letras misturadas, nem de prefixo 55.
- Arredondamento: só dois casos; falta centavo ímpar mínimo (0,01 e 0,03), valor máximo e preço zero.
- Atendente: não testa `PATCH /clientes`, `GET /clientes/por-telefone`, nem que `PATCH /entregadores` e `/categorias` dão 403.
- Sem teste de usuário com `deve_trocar_senha` nestas rotas, nem de categoria inativa com sabores existentes.
- Auditoria de produto, adicional e categoria não é conferida para ausência de campos indevidos.
- Não existe teste automatizado do front (edição inline, campos nulos, busca fora de ordem).

## Resumo
A regra de preço, o arredondamento, o histórico pela API, as permissões, o isolamento por loja e a auditoria sem dados pessoais estão corretos e provados; nenhum achado de severidade alta.
Os pontos a corrigir primeiro são o 500 com NUL em `q`, o telefone aceitando texto e DDI, a falta de gatilho de só inserção nos preços e os problemas de busca e lista truncada no front.
