# QA cego da fatia 1C (Vendas)

Escopo lido: `migrations_pg/004_vendas.sql`, `api/routers/vendas.py`, `api/services/vendas.py`, seção "vendas (fatia 1C)" de `api/schemas.py`, permissões em `api/security.py`, `abaVendas` em `frontend/static/app.js` e `tests/test_vendas.py`.
Os 19 testes de `tests/test_vendas.py` passam. Os cenários abaixo foram reproduzidos com um teste descartável (já removido; nenhum arquivo de produção ou de teste existente foi alterado).

Resumo: nenhum achado de gravidade alta. Há 4 médios e 5 baixos. Verificado e sem falha: injeção SQL (tudo parametrizado), XSS (a função `h` só usa nó de texto e `setAttribute` sem HTML), ids gigantes (devolvem 404, sem 500), perda do lock do pedido em `cancelar` (o código relê com `FOR UPDATE` e confere de novo), Id do dia sob concorrência (a linha de `contador_dia` serializa), metade arredondada para cima, troco só em dinheiro.

## Achados

### 1. Limite de desconto pode ser ultrapassado por arredondamento do percentual (média)
- Onde: `api/services/vendas.py:85` (`pct` com `quantize(Decimal("0.01"))`), comparado em `api/routers/vendas.py:72` e `api/services/vendas.py:126`, e em `routers/vendas.py:45` (`precisa_autorizacao`).
- Cenário (reproduzido): limite do atendente 5%. 99 bebidas de R$ 6,00, subtotal 594,00. Desconto de 29,72 é 5,0034%, arredondado para 5,00, então não pede autorização. O pedido foi criado (201) sem gerente. O limite exato seria 29,70.
- Efeito: o limite é furado por até 0,005 ponto percentual. Em pedido grande são alguns reais por pedido, repetíveis. O mesmo vale para o limite do autorizador.
- Correção: comparar valores em dinheiro, sem arredondar o percentual: `desconto * 100 > subtotal * lim` (ou `desconto > (subtotal * lim / 100)` quantizado para baixo). Mostrar o percentual arredondado só na tela.

### 2. Taxa de entrega reduzida funciona como desconto sem limite nem autorização (média)
- Onde: `api/routers/vendas.py:57-58` e `api/services/vendas.py:83`; schema `taxa_entrega: Optional[Reais]` em `api/schemas.py` (PedidoCalcular).
- Cenário (reproduzido): atendente cria entrega com `taxa_entrega "0,01"` e `taxa_motivo "x"`. Resposta 201, total 35,01, ou seja, R$ 5,99 de abatimento sem gerente. Qualquer texto de motivo basta.
- Efeito: contorna a regra "desconto acima do limite exige gerente". Se isso for decisão de negócio (taxa é outra coisa), falta registrar quem baixou a taxa; hoje só `taxa_motivo` fica no pedido, que ainda por cima pode ser editado no banco (achado 6).
- Correção: tratar `padrao - taxa` como desconto para fins do limite (somar ao percentual), ou exigir autorização de gerente quando a taxa ficar abaixo do padrão. Gravar `usuario_id` e `autorizado_por` também para a taxa.

### 3. Entrega grátis (taxa 0,00) é impossível de registrar (média, funcional)
- Onde: `api/schemas.py`, `Reais = Annotated[str, AfterValidator(_reais_positivo)]` usado em `taxa_entrega`; a checagem `parse_reais(d.taxa_entrega) != 0` em `api/services/vendas.py:79` nunca é alcançada com zero.
- Cenário (reproduzido): `POST /pedidos/calcular` com `tipo=entrega, taxa_entrega="0"` devolve 422 "O preço deve ser maior que zero". Cortesia de entrega vira "0,01", que cai no achado 2 e deixa o total com um centavo falso.
- Correção: usar um tipo `ReaisZeroOuMais` para taxa (aceita 0,00), mantendo a regra de motivo e, se aplicável, de autorização do achado 2.

### 4. Envio duplicado: o botão "Confirmar pedido" não é travado e a API não é idempotente (média)
- Onde: `frontend/static/app.js:753-760` (nenhum `disabled` durante a chamada); `api/routers/vendas.py:49` (sem chave de idempotência).
- Cenário (reproduzido na API): duas chamadas idênticas seguidas criaram os Id do dia 4 e 5, com dois pagamentos. Duplo clique ou toque repetido em rede lenta gera venda e pagamento em dobro. Como pedido e pagamento são só de inserção, a correção exige cancelamento com gerente.
- Correção: desabilitar o botão até a resposta (e em `finally` reabilitar só se falhou); no servidor, aceitar um `Idempotency-Key` gerado na tela por rascunho, com índice único, ou recusar pedido idêntico do mesmo usuário em poucos segundos.

### 5. Trava de tentativas de autorização é compartilhada com o login: um atendente bloqueia o gerente (média)
- Onde: `api/services/vendas.py:114-123` reutiliza `exigir_login_liberado`/`registrar_falha_login`, chave `ip|usuario` (`api/security.py:68`).
- Cenário (por leitura; o teste `test_tentativas_de_autorizacao_sao_limitadas` mostra o bloqueio): numa loja em que os terminais saem pelo mesmo IP (rede local, proxy), um atendente erra 5 vezes a senha informando o usuário do gerente. A partir daí, qualquer autorização e o próprio login do gerente nesse IP voltam 429 durante `LOGIN_JANELA_MIN`, inclusive com a senha certa. Isso pára descontos e cancelamentos.
- Correção: chave separada para autorização (por exemplo prefixo `aut|`) e, de preferência, também limitada por sessão do requerente, para o abuso ficar contido na conta de quem tenta; avisar o gerente da tentativa na auditoria.

### 6. Trigger do pedido deixa mudar campos que a regra diz serem imutáveis e não impede transições de situação (baixa)
- Onde: `migrations_pg/004_vendas.sql:119-135` (`pedido_so_situacao`). A comparação não inclui `taxa_motivo`, `observacoes`, `id_canal`, `criado_por`, `entrega_calculada`, e não valida a situação.
- Cenário (reproduzido com conexão direta): `UPDATE pedido SET observacoes='alterada'`, `SET criado_por=NULL`, `SET situacao='cancelado'` e depois `SET situacao='recebido'` foram todos aceitos. O pedido volta de cancelado para recebido com o registro em `cancelamento` ainda existente. A mensagem do trigger também diz "apenas situação, urgência, entrega e número do CF", o que não é o que o código faz.
- Efeito: só atinge quem tem acesso direto ao banco ou código futuro, por isso baixa. Mas o requisito é que a trilha seja confiável.
- Correção: incluir `criado_por`, `taxa_motivo`, `observacoes`, `id_canal` na lista congelada; recusar saída de `cancelado` e retrocesso de situação (ordem de `SITUACOES`); exigir, ao mudar para `cancelado`, que exista linha em `cancelamento`.

### 7. Nada no banco garante que os pagamentos somam o total; estorno de pedido cancelado não existe (baixa)
- Onde: `migrations_pg/004_vendas.sql:67-77` (tabela `pagamento`), `api/routers/vendas.py:192-218` (cancelar).
- Cenário (reproduzido): `INSERT INTO pagamento (...) VALUES (pedido, 'pix', 999, now())` num pedido de 35,00 foi aceito (o trigger só barra UPDATE e DELETE). Em pedido cancelado os pagamentos continuam como entrada; qualquer soma de caixa da fatia 1E que não filtre `situacao <> 'cancelado'` conta venda cancelada. Além disso `pagamento.valor` guarda o valor bruto recebido (com troco dentro), então somar `valor` sem descontar `troco` superestima o caixa.
- Correção: trigger de restrição adiado (`DEFERRABLE INITIALLY DEFERRED`) conferindo `sum(valor - troco) = total` por pedido; gravar linha de estorno (valor negativo ou tabela própria, só de inserção) no cancelamento; documentar que o líquido é `valor - troco`.

### 8. Verificação morta de perfil em `criar` (baixa)
- Onde: `api/routers/vendas.py:77-78`: `"vendas.criar" not in PERMISSOES...` nunca é verdadeira, pois a rota já exige `vendas.criar`.
- Efeito: dá a falsa impressão de que "urgente" tem controle de perfil. Hoje qualquer atendente marca urgente (também em `/urgente`).
- Correção: remover, ou trocar pela permissão pretendida (`vendas.gerir`) se urgente for restrito.

### 9. Estado de tela sobrevive ao logout (baixa)
- Onde: `frontend/static/app.js:32-37` (`sair` não zera `estado.rascunho`, `estado.subv`); rascunho criado em `app.js:658`.
- Cenário: o atendente A deixa um pedido em montagem (cliente com nome e endereço, itens) e sai; o atendente B entra no mesmo navegador e vê e confirma o rascunho de A. Dados pessoais de cliente permanecem em memória.
- Correção: em `sair`, `estado.rascunho = null; estado.subv = null`.

### 10. Mensagens de autorização distinguem credencial válida de inválida (baixa)
- Onde: `api/services/vendas.py:123` ("Autorização recusada...") e `:128` ("O desconto passa do limite de quem está autorizando.") e, em `routers/vendas.py:74-75`, o limite do solicitante.
- Cenário: quem testa senhas descobre que a senha de um gerente está certa quando a resposta muda para a mensagem do limite (essa ramificação também não conta falha e não passa pela trava).
- Efeito: só vale depois de acertar a senha, por isso baixa; mas o ramo do limite não é contado e permite confirmar credencial válida sem custo.
- Correção: contar como falha também o ramo do limite, ou usar a mesma mensagem genérica nos dois casos.

## Lacunas de teste (não são falhas de código)
- Limite exatamente no teto e um centavo acima, com subtotal que gere percentual de 3 casas (cobriria o achado 1).
- Meia a meia com preços que geram meio centavo (ex.: 33,33 e 41,67), verificando que cada metade sobe e a soma bate com o item gravado.
- Taxa de entrega abaixo do padrão por atendente (achado 2) e taxa 0,00 (achado 3).
- Duplo envio (achado 4) e cancelamento concorrente (dois cancelamentos simultâneos do mesmo pedido: um 200, outro 409; e cancelamento por atendente contra mudança de situação para despachado durante a autorização).
- Limite de desconto não definido (vale 0): desconto de 0,01 deve exigir gerente.
- Gerente autorizando com perfil subgerente (limite 10%) para desconto de 15%: deve ser recusado.
- Autorizador inativo, com `deve_trocar_senha` ou de perfil errado (só o atendente é testado).
- Atomicidade: falha no meio da gravação (por exemplo item inválido depois do pedido) não deixa `contador_dia` incrementado nem pedido parcial.
- Pagamentos: duas linhas em dinheiro com troco, 6 pagamentos, valor 0,01, e a conta de que `sum(valor - troco) = total` para todo pedido criado.
- Frontend: nenhum teste de XSS ou de comportamento da `abaVendas` (a verificação desta revisão foi só por leitura do código).
- Triggers: testar `UPDATE` das colunas do achado 6 e `INSERT` de pagamento que não soma o total.
