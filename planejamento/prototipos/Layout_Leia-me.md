# Três modelos de layout do Sistema da Pizzaria

Data: 30/10/2026. Base: moldura atual de `sistema/frontend` (padrão PCP adaptado, paleta âmbar e vermelho de forno) e o relatório `03_Padroes_de_Layout.md`. Os três usam os mesmos tokens de cor, tema noite (padrão) e dia, e as lições do relatório: alertas antes dos números, etiquetas de situação coloridas, modal próprio no lugar de `confirm()`, aviso flutuante (toast) e lista que vira cartões no celular. Produção não foi tocada.

Como ver: abra cada arquivo no navegador. Cada um tem Painel e Pedidos do dia (pelo menu), a chave 🌙/☀️ troca o tema, e dá para estreitar a janela para ver o celular. Dados fictícios ("Cliente Exemplo A", "Sabor Exemplo 1"), nada é gravado.

| Arquivo | Modelo |
|---|---|
| `Layout_A_Fiel_ao_PCP.html` | A: fiel ao PCP |
| `Layout_B_Compacto_Tablet.html` | B: compacto e operacional para tablet |
| `Layout_C_Visual_Cartoes.html` | C: visual com cartões |

## Comparação

| Ponto | A: fiel ao PCP | B: compacto para tablet | C: visual com cartões |
|---|---|---|---|
| Navegação | menu lateral com seções, recolhível; gaveta no celular | abas no topo; barra de navegação embaixo no celular | trilho de ícones com rótulo; vira barra embaixo no celular |
| Painel | faixas de alerta, 4 KPIs com faixa de estado, gráfico de barras, ranking de sabores, caixa | faixa de alerta de uma linha, placar de 5 números, fila de pedidos com tempo, resumo do caixa | cartões de alerta, destaque de vendas com meta, KPIs com minigráfico, rosca de pagamentos |
| Lista de pedidos | barra de filtros + tabela com cabeçalho fixo, etiquetas, paginação; cartões no celular | segmentos por situação com contagem, lista à esquerda e detalhe à direita com botões grandes | quadro por situação (colunas), cartão por pedido com seta para avançar |
| Confirmação | modal central com rodapé de botões | folha que sobe de baixo (alcance do polegar) | modal central com ícone grande |
| Densidade | média | alta (mais informação por tela) | baixa (mais espaço e cor) |
| Toque | botões de 36 a 40 px | 48 a 58 px em tudo | 44 px |
| Esforço para adotar | baixo: é o kit do relatório sobre a moldura atual | médio: troca a navegação e cria lista com detalhe | alto: troca navegação e cria quadro e gráficos |
| Melhor para | gerente e escritório (Estoque, Contas, Custos, RH, BI) | balcão e caixa no tablet no horário de pico | Painel do proprietário e BI |

## Pontos de atenção

- A: a tabela continua sendo a melhor forma para listas longas de escritório, mas no balcão exige mais toques e leitura.
- B: as abas no topo não comportam os 18 itens do menu; os de escritório ficam em "Mais". Bom para quem usa 3 ou 4 telas o dia todo.
- C: o quadro por situação é ótimo com até umas 30 ordens abertas; acima disso as colunas ficam longas. Os gráficos pedem dados reais de alguns dias para fazer sentido.

## Recomendação

Adotar o **A como padrão do sistema inteiro**, porque é a evolução direta do que já está construído e do kit do relatório, com o menor retrabalho, e aplicar **o padrão do B nas telas de operação no tablet** (Pedidos do dia e Caixa): segmentos por situação com contagem, lista com detalhe ao lado e botões de 48 px. Do C, aproveitar só o destaque de vendas com meta e o minigráfico nos KPIs do Painel e do BI. Produção continua fora até o layout próprio dela ser definido.

## Decisão do Marlon (30/10/2026)

Gostou do A e do C e vai fazer uma mescla dos dois. Pausado; próximo passo é definir com ele o que vem de cada um e montar o protótipo mesclado.
