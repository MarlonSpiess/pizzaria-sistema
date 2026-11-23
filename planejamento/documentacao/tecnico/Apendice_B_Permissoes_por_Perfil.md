# Apêndice B: permissões por perfil

Gerado automaticamente de `PERMISSOES` em `sistema/api/security.py` por `planejamento/documentacao/fonte/gerar_apendice_permissoes.py`. Não edite à mão. Perfil sem a permissão recebe 403 do servidor (negado por padrão).

| Permissão | administrador | proprietario | gerente | subgerente | atendente | massa | pizzaiolo | acabamento |
|---|---|---|---|---|---|---|---|---|
| `auditoria.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `bi.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `caixa.aprovar` | ✔ | ✔ | ✔ |  |  |  |  |  |
| `caixa.gerir` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `caixa.operar` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `caixa.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `canais.configurar` | ✔ | ✔ |  |  |  |  |  |  |
| `cardapio.editar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `cardapio.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `clientes.editar` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `clientes.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `compras.aprovar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `compras.operar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `compras.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `contas.aprovar` | ✔ | ✔ |  |  |  |  |  |  |
| `contas.operar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `contas.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `custos.gerir` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `custos.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `entregadores.editar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `entregadores.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `entregas.despachar` | ✔ | ✔ | ✔ | ✔ |  |  |  | ✔ |
| `estoque.gerir` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `estoque.mover` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `estoque.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `ficha.editar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `ficha.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `imobilizado.aprovar` | ✔ | ✔ |  |  |  |  |  |  |
| `imobilizado.operar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `imobilizado.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `parametros.editar` | ✔ | ✔ |  |  |  |  |  |  |
| `parametros.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `producao.acabamento` | ✔ | ✔ | ✔ | ✔ |  |  |  | ✔ |
| `producao.forno` | ✔ | ✔ | ✔ | ✔ |  |  |  | ✔ |
| `producao.gerir` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `producao.massa` | ✔ | ✔ | ✔ | ✔ |  | ✔ |  |  |
| `producao.montagem` | ✔ | ✔ | ✔ | ✔ |  |  | ✔ |  |
| `producao.perda` | ✔ | ✔ | ✔ | ✔ |  |  | ✔ | ✔ |
| `producao.perda_massa` | ✔ | ✔ | ✔ | ✔ |  | ✔ |  |  |
| `producao.refazer` | ✔ | ✔ | ✔ | ✔ |  |  |  | ✔ |
| `rh.aprovar` | ✔ | ✔ | ✔ |  |  |  |  |  |
| `rh.operar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `rh.proprio` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| `rh.salarios` | ✔ | ✔ |  |  |  |  |  |  |
| `rh.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `sistema.backup.rodar` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `sistema.backup.ver` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `usuarios.gerir` | ✔ | ✔ |  |  |  |  |  |  |
| `vendas.criar` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |
| `vendas.gerir` | ✔ | ✔ | ✔ | ✔ |  |  |  |  |
| `vendas.ver` | ✔ | ✔ | ✔ | ✔ | ✔ |  |  |  |

Total: 51 permissões, 8 perfis.
