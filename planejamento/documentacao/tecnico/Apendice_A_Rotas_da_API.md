# Apêndice A: rotas da API e permissão exigida

Gerado automaticamente a partir de `sistema/api/routers/` por `planejamento/documentacao/fonte/gerar_apendice_rotas.py`. Não edite à mão: rode o script de novo quando o código mudar.

Total: 257 rotas.

A permissão é conferida no servidor em cada chamada (`requer` exige a permissão; `requer_alguma` aceita qualquer uma das listadas). Quais perfis têm cada permissão está na seção 5 do Manual Técnico. Além da permissão, várias rotas aplicam regras de negócio (por exemplo, caixa aberto, limite de desconto, aprovação por outra pessoa) que devolvem 400, 403 ou 409.

`/health` (sem login) e as telas (`/`, `/static/*`) ficam fora da API.

## Auditoria (`auditoria.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/auditoria` | `auditoria.ver` |

## Autenticação (`auth.py`)

| Método | Rota | Permissão |
|---|---|---|
| POST | `/api/auth/login` | nenhuma (é a rota que abre a sessão) |
| POST | `/api/auth/logout` | sessão válida (sem permissão específica) |
| GET | `/api/auth/me` | sessão válida (sem permissão específica) |
| POST | `/api/auth/trocar-senha` | sessão válida (sem permissão específica) |

## BI (`bi.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/bi/painel` | `bi.ver` |
| GET | `/api/bi/alertas` | `bi.ver` |
| GET | `/api/bi/dre` | `bi.ver` |
| GET | `/api/bi/dre/serie` | `bi.ver` |
| GET | `/api/bi/dre.csv` | `bi.ver` |
| GET | `/api/bi/lucratividade` | `bi.ver` |
| GET | `/api/bi/producao` | `bi.ver` |
| GET | `/api/bi/vendas-por-forma.csv` | `bi.ver` |

## Caixa, entregas e despacho (`caixa.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/caixa/hoje` | `caixa.ver` |
| GET | `/api/caixa/pendentes` | `caixa.ver` |
| GET | `/api/caixa/motivos` | `caixa.ver` |
| POST | `/api/caixa/motivos/iniciar-padrao` | `caixa.gerir` |
| POST | `/api/caixa/motivos` | `caixa.gerir` |
| PATCH | `/api/caixa/motivos/{mid}` | `caixa.gerir` |
| GET | `/api/caixa/maquininhas` | `caixa.ver` |
| POST | `/api/caixa/maquininhas` | `caixa.gerir` |
| PATCH | `/api/caixa/maquininhas/{mid}` | `caixa.gerir` |
| GET | `/api/caixa/regras-recebimento` | `caixa.ver` |
| POST | `/api/caixa/regras-recebimento` | `caixa.gerir` |
| POST | `/api/caixa/abrir` | `caixa.operar` |
| POST | `/api/caixa/movimentos` | `caixa.operar` |
| POST | `/api/caixa/contagem` | `caixa.operar` |
| POST | `/api/caixa/fechar` | `caixa.operar` |
| GET | `/api/caixa/entregas` | `caixa.ver` |
| POST | `/api/caixa/entregas/{pedido_id}` | `caixa.operar` |
| GET | `/api/caixa/despacho` | `entregas.despachar` |
| GET | `/api/caixa/despacho/entregadores` | `entregas.despachar` |
| POST | `/api/caixa/despacho/{pedido_id}` | `entregas.despachar` |
| POST | `/api/caixa/acertos` | `caixa.operar` |
| GET | `/api/caixa/{data}/relatorio` | `caixa.ver` |

## Canais de venda (`canais.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/canais` | `vendas.gerir` |
| GET | `/api/canais/loja` | `vendas.gerir` |
| PATCH | `/api/canais/loja` | `vendas.gerir` |
| PATCH | `/api/canais/{cid}/ativo` | `canais.configurar` |
| PATCH | `/api/canais/{cid}/aceitar-sozinho` | `canais.configurar` |
| GET | `/api/canais/{cid}/fila` | `vendas.gerir` |
| POST | `/api/canais/fila/{eid}/recusar` | `vendas.gerir` |
| POST | `/api/canais/fila/{eid}/reprocessar` | `vendas.gerir` |
| GET | `/api/canais/{cid}/produtos` | `vendas.gerir` |
| PUT | `/api/canais/{cid}/produtos` | `canais.configurar` |

## Cardápio (`cardapio.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/categorias` | `cardapio.ver` |
| POST | `/api/categorias` | `cardapio.editar` |
| PATCH | `/api/categorias/{cid}` | `cardapio.editar` |
| GET | `/api/produtos` | `cardapio.ver` |
| POST | `/api/produtos` | `cardapio.editar` |
| PATCH | `/api/produtos/{pid}` | `cardapio.editar` |
| GET | `/api/produtos/{pid}/historico-precos` | `cardapio.editar` |
| GET | `/api/adicionais` | `cardapio.ver` |
| POST | `/api/adicionais` | `cardapio.editar` |
| PATCH | `/api/adicionais/{aid}` | `cardapio.editar` |
| POST | `/api/precos/pizza` | `cardapio.ver` |

## Compras (`compras.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/compras/fornecedores` | `compras.ver` |
| POST | `/api/compras/fornecedores` | `compras.operar` |
| PATCH | `/api/compras/fornecedores/{fid}` | `compras.operar` |
| GET | `/api/compras/precos/{item_id}` | `compras.ver` |
| GET | `/api/compras/necessidades` | `compras.ver` |
| POST | `/api/compras/listas` | `compras.operar` |
| GET | `/api/compras/listas` | `compras.ver` |
| GET | `/api/compras/listas/{lid}` | `compras.ver` |
| POST | `/api/compras/listas/{lid}/itens` | `compras.operar` |
| PATCH | `/api/compras/listas/{lid}/itens/{liid}` | `compras.operar` |
| GET | `/api/compras/listas/{lid}/por-fornecedor` | `compras.ver` |
| POST | `/api/compras/listas/{lid}/cotacoes` | `compras.operar` |
| GET | `/api/compras/listas/{lid}/mapa` | `compras.ver` |
| POST | `/api/compras/listas/{lid}/definir` | `compras.operar` |
| POST | `/api/compras/listas/{lid}/aprovar` | `compras.aprovar` |
| POST | `/api/compras/listas/{lid}/cancelar` | `compras.operar` |
| GET | `/api/compras/pedidos` | `compras.ver` |
| GET | `/api/compras/pedidos/{pid}` | `compras.ver` |
| POST | `/api/compras/pedidos` | `compras.operar` |
| POST | `/api/compras/pedidos/{pid}/cancelar` | `compras.operar` |
| GET | `/api/compras/recebimentos` | `compras.ver` |
| POST | `/api/compras/recebimentos` | `compras.operar` |

## Contas e fluxo de caixa (`contas.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/contas/contas-bancarias` | `contas.ver` |
| POST | `/api/contas/contas-bancarias` | `contas.operar` |
| PATCH | `/api/contas/contas-bancarias/{cid}` | `contas.operar` |
| GET | `/api/contas/tipos-despesa` | `contas.ver` |
| POST | `/api/contas/tipos-despesa` | `contas.operar` |
| POST | `/api/contas/tipos-despesa/iniciar-padrao` | `contas.operar` |
| PATCH | `/api/contas/tipos-despesa/{tid}` | `contas.operar` |
| GET | `/api/contas/canais` | `contas.ver` |
| POST | `/api/contas/canais` | `contas.operar` |
| PATCH | `/api/contas/canais/{cid}` | `contas.operar` |
| GET | `/api/contas/recorrentes` | `contas.ver` |
| POST | `/api/contas/recorrentes` | `contas.operar` |
| PATCH | `/api/contas/recorrentes/{rid}` | `contas.operar` |
| POST | `/api/contas/sincronizar` | `contas.operar` |
| GET | `/api/contas/titulos` | `contas.ver` |
| POST | `/api/contas/titulos` | `contas.operar` |
| POST | `/api/contas/titulos/{tid}/aprovar` | `contas.aprovar` |
| POST | `/api/contas/titulos/{tid}/cancelar` | `contas.operar` |
| POST | `/api/contas/titulos/{tid}/baixas` | `contas.operar` |
| POST | `/api/contas/extrato` | `contas.operar` |
| GET | `/api/contas/conciliacao/{conta_id}` | `contas.ver` |
| POST | `/api/contas/conciliacao` | `contas.operar` |
| GET | `/api/contas/fluxo` | `contas.ver` |

## Custos (`custos.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/custos/produtos` | `custos.ver` |
| GET | `/api/custos/produtos/{pid}` | `custos.ver` |
| GET | `/api/custos/fatores` | `custos.ver` |
| PUT | `/api/custos/fatores/{item_id}` | `custos.gerir` |
| GET | `/api/custos/cmv` | `custos.ver` |
| POST | `/api/custos/cmv/fechar` | `custos.gerir` |
| GET | `/api/custos/resultado` | `custos.ver` |

## Estoque (`estoque.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/estoque/locais` | `estoque.ver` |
| POST | `/api/estoque/locais/iniciar-padrao` | `estoque.gerir` |
| POST | `/api/estoque/locais` | `estoque.gerir` |
| PATCH | `/api/estoque/locais/{lid}` | `estoque.gerir` |
| GET | `/api/estoque/itens` | `estoque.ver` |
| GET | `/api/estoque/itens/{iid}` | `estoque.ver` |
| PUT | `/api/estoque/itens/{iid}/config` | `estoque.gerir` |
| GET | `/api/estoque/movimentos` | `estoque.ver` |
| POST | `/api/estoque/movimentos` | `estoque.mover` |
| GET | `/api/estoque/alertas` | `estoque.ver` |
| GET | `/api/estoque/inventarios` | `estoque.ver` |
| POST | `/api/estoque/inventarios` | `estoque.mover` |
| GET | `/api/estoque/inventarios/{iid}` | `estoque.ver` |
| PUT | `/api/estoque/inventarios/{iid}/contagem` | `estoque.mover` |
| POST | `/api/estoque/inventarios/{iid}/conferir` | `estoque.mover` |
| POST | `/api/estoque/inventarios/{iid}/fechar` | `estoque.gerir` |

## Imobilizado (`imobilizado.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/imobilizado/categorias` | `imobilizado.ver` |
| POST | `/api/imobilizado/categorias` | `imobilizado.operar` |
| POST | `/api/imobilizado/categorias/iniciar-padrao` | `imobilizado.operar` |
| PATCH | `/api/imobilizado/categorias/{cid}` | `imobilizado.operar` |
| GET | `/api/imobilizado/bens` | `imobilizado.ver` |
| GET | `/api/imobilizado/bens/{bid}` | `imobilizado.ver` |
| POST | `/api/imobilizado/bens` | `imobilizado.operar` |
| PATCH | `/api/imobilizado/bens/{bid}` | `imobilizado.operar` |
| POST | `/api/imobilizado/bens/{bid}/baixa` | `imobilizado.aprovar` |
| POST | `/api/imobilizado/bens/{bid}/conferencias` | `imobilizado.operar` |
| GET | `/api/imobilizado/inventario` | `imobilizado.ver` |
| POST | `/api/imobilizado/bens/{bid}/planos` | `imobilizado.operar` |
| GET | `/api/imobilizado/planos` | `imobilizado.ver` |
| PATCH | `/api/imobilizado/planos/{pid}` | `imobilizado.operar` |
| PUT | `/api/imobilizado/bens/{bid}/limites` | `imobilizado.operar` |
| POST | `/api/imobilizado/bens/{bid}/leituras` | `imobilizado.operar` |
| GET | `/api/imobilizado/alertas` | `imobilizado.ver` |
| GET | `/api/imobilizado/os` | `imobilizado.ver` |
| GET | `/api/imobilizado/os/{oid}` | `imobilizado.ver` |
| POST | `/api/imobilizado/os` | `imobilizado.operar` |
| POST | `/api/imobilizado/os/{oid}/iniciar` | `imobilizado.operar` |
| POST | `/api/imobilizado/os/{oid}/pecas` | `imobilizado.operar` |
| POST | `/api/imobilizado/os/{oid}/aprovar` | `imobilizado.aprovar` |
| POST | `/api/imobilizado/os/{oid}/fechar` | `imobilizado.operar` |
| POST | `/api/imobilizado/os/{oid}/cancelar` | `imobilizado.operar` |
| GET | `/api/imobilizado/custos-manutencao` | `imobilizado.ver` |

## Parâmetros (`parametros.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/parametros` | `parametros.ver` |
| GET | `/api/parametros/formas-pagamento` | `vendas.criar` |
| PUT | `/api/parametros/{chave}` | `parametros.editar` |
| GET | `/api/parametros/{chave}/historico` | `parametros.ver` |

## Clientes e entregadores (`pessoas.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/clientes` | `clientes.ver` |
| GET | `/api/clientes/por-telefone/{telefone}` | `clientes.ver` |
| POST | `/api/clientes` | `clientes.editar` |
| PATCH | `/api/clientes/{cid}` | `clientes.editar` |
| GET | `/api/entregadores` | `entregadores.ver` |
| POST | `/api/entregadores` | `entregadores.editar` |
| PATCH | `/api/entregadores/{eid}` | `entregadores.editar` |

## Produção (`producao.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/producao/fila` | `producao.montagem` ou `producao.forno` ou `producao.acabamento` ou `producao.gerir` |
| GET | `/api/producao/perdidas` | `producao.acabamento` ou `producao.gerir` |
| GET | `/api/producao/pedidos` | `producao.acabamento` ou `producao.gerir` |
| POST | `/api/producao/pizzas/proxima` | `producao.montagem` |
| POST | `/api/producao/pizzas/{pid}/produzida` | `producao.montagem` |
| POST | `/api/producao/pizzas/{pid}/retroceder` | `producao.montagem` |
| POST | `/api/producao/pizzas/{pid}/saiu-do-forno` | `producao.forno` |
| POST | `/api/producao/pizzas/{pid}/acabada` | `producao.acabamento` |
| POST | `/api/producao/pedidos/{ped_id}/acabado` | `producao.acabamento` |
| POST | `/api/producao/pizzas/{pid}/perder` | `producao.perda` |
| POST | `/api/producao/pizzas/{pid}/refazer` | `producao.refazer` |
| POST | `/api/producao/pizzas/{pid}/montagem-errada` | `producao.montagem` ou `producao.acabamento` ou `producao.gerir` |
| POST | `/api/producao/pizzas/{pid}/sem-ingredientes` | `producao.montagem` |
| GET | `/api/producao/avulsas` | `producao.acabamento` ou `producao.gerir` |
| POST | `/api/producao/avulsas/{pid}/descartar` | `producao.acabamento` ou `producao.gerir` |
| GET | `/api/producao/avisos` | `producao.massa` ou `producao.montagem` ou `producao.forno` ou `producao.acabamento` ou `producao.gerir` |
| POST | `/api/producao/avisos/{aid}/resolver` | `producao.gerir` ou `producao.acabamento` |
| GET | `/api/producao/massa` | `producao.massa` ou `producao.gerir` |
| POST | `/api/producao/massa/lote` | `producao.massa` |
| POST | `/api/producao/massa/contagem` | `producao.massa` |
| POST | `/api/producao/massa/perda` | `producao.perda_massa` |
| GET | `/api/producao/motivos` | `producao.montagem` ou `producao.perda` ou `producao.perda_massa` ou `producao.refazer` ou `producao.gerir` |
| POST | `/api/producao/motivos/iniciar-padrao` | `producao.gerir` |
| POST | `/api/producao/motivos/{tipo}` | `producao.gerir` |
| PATCH | `/api/producao/motivos/{tipo}/{mid}` | `producao.gerir` |

## Itens, fichas técnicas e etapas (`receitas.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/itens` | `ficha.ver` |
| POST | `/api/itens` | `ficha.editar` |
| PATCH | `/api/itens/{iid}` | `ficha.editar` |
| GET | `/api/fichas/produto/{pid}` | `ficha.ver` |
| PUT | `/api/fichas/produto/{pid}` | `ficha.editar` |
| GET | `/api/fichas/adicional/{aid}/{tamanho}` | `ficha.ver` |
| PUT | `/api/fichas/adicional/{aid}/{tamanho}` | `ficha.editar` |
| GET | `/api/fichas/preparo/{iid}` | `ficha.ver` |
| PUT | `/api/fichas/preparo/{iid}` | `ficha.editar` |
| GET | `/api/fichas/base/{tamanho}` | `ficha.ver` |
| PUT | `/api/fichas/base/{tamanho}` | `ficha.editar` |
| GET | `/api/etapas` | `ficha.ver` |
| POST | `/api/etapas` | `ficha.editar` |
| PATCH | `/api/etapas/{eid}` | `ficha.editar` |
| POST | `/api/etapas/iniciar-padrao` | `ficha.editar` |
| GET | `/api/modelo-etapas/{tipo}` | `ficha.ver` |
| PUT | `/api/modelo-etapas/{tipo}` | `ficha.editar` |
| GET | `/api/produtos/{pid}/etapas` | `ficha.ver` |
| PUT | `/api/produtos/{pid}/etapas` | `ficha.editar` |
| DELETE | `/api/produtos/{pid}/etapas` | `ficha.editar` |
| GET | `/api/fichas/qualidade` | `ficha.ver` |

## RH (`rh.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/rh/funcoes` | `rh.ver` |
| POST | `/api/rh/funcoes` | `rh.operar` |
| POST | `/api/rh/iniciar-padrao` | `rh.operar` |
| PATCH | `/api/rh/funcoes/{fid}` | `rh.operar` |
| GET | `/api/rh/escalas` | `rh.ver` |
| POST | `/api/rh/escalas` | `rh.operar` |
| PATCH | `/api/rh/escalas/{eid}` | `rh.operar` |
| GET | `/api/rh/funcionarios` | `rh.ver` |
| POST | `/api/rh/funcionarios` | `rh.operar` |
| PATCH | `/api/rh/funcionarios/{fid}` | `rh.operar` |
| POST | `/api/rh/funcionarios/{fid}/desligar` | `rh.operar` |
| GET | `/api/rh/funcionarios/{fid}/contratos` | `rh.salarios` |
| POST | `/api/rh/funcionarios/{fid}/contratos` | `rh.salarios` |
| GET | `/api/rh/funcionarios/{fid}/beneficios` | `rh.salarios` |
| POST | `/api/rh/funcionarios/{fid}/beneficios` | `rh.salarios` |
| PATCH | `/api/rh/beneficios/{bid}` | `rh.salarios` |
| GET | `/api/rh/turnos` | `rh.ver` |
| PUT | `/api/rh/turnos` | `rh.operar` |
| DELETE | `/api/rh/turnos/{tid}` | `rh.operar` |
| GET | `/api/rh/escalados` | `rh.ver` |
| PUT | `/api/rh/ponto` | `rh.operar` |
| GET | `/api/rh/ponto/saldo` | `rh.ver` |
| POST | `/api/rh/banco-horas` | `rh.aprovar` |
| GET | `/api/rh/ausencias` | `rh.ver` |
| POST | `/api/rh/ausencias` | `rh.operar` |
| POST | `/api/rh/documentos` | `rh.operar` |
| GET | `/api/rh/alertas` | `rh.ver` |
| GET | `/api/rh/meus-dados` | `rh.proprio` |
| GET | `/api/rh/folha/previa` | `rh.salarios` |
| POST | `/api/rh/folha/resumo` | `rh.salarios` |
| POST | `/api/rh/folha/lancar` | `rh.salarios` |

## Sistema (backup) (`sistema.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/sistema/backup` | `sistema.backup.ver` |
| POST | `/api/sistema/backup` | `sistema.backup.rodar` |

## Usuários (`usuarios.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/usuarios` | `usuarios.gerir` |
| POST | `/api/usuarios` | `usuarios.gerir` |
| PATCH | `/api/usuarios/{uid}` | `usuarios.gerir` |
| POST | `/api/usuarios/{uid}/redefinir-senha` | `usuarios.gerir` |

## Pedidos (Vendas) (`vendas.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/pedidos/avulsas-disponiveis` | `vendas.criar` |
| POST | `/api/pedidos/calcular` | `vendas.criar` |
| POST | `/api/pedidos` | `vendas.criar` |
| GET | `/api/pedidos` | `vendas.ver` |
| GET | `/api/pedidos/{pid}` | `vendas.ver` |
| POST | `/api/pedidos/{pid}/situacao` | `vendas.criar` |
| POST | `/api/pedidos/{pid}/urgente` | `vendas.criar` |
| PATCH | `/api/pedidos/{pid}/cf` | `vendas.criar` |
| POST | `/api/pedidos/{pid}/cancelar` | `vendas.criar` |

## Vendas fechadas por ingrediente (`vendas_fechadas.py`)

| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/vendas-fechadas/ingredientes` | `vendas.gerir` |
| GET | `/api/vendas-fechadas/ingredientes/{item_id}/sabores` | `vendas.gerir` |
| PUT | `/api/vendas-fechadas/ingredientes/{item_id}/falta` | `vendas.gerir` |
| GET | `/api/vendas-fechadas` | `vendas.gerir` |
