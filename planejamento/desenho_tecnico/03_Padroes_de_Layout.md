# Padrões de layout: PCP Web como referência para o Sistema da Pizzaria

Data: 30/10/2026. Referência estudada: PCP Web (pcp.allexcorp.com.br), cujo código publicado é `C:\Temp\PCP\frontend\app.html`. Comparado com: `C:\Maria Gabriela\Pizzaria\sistema\frontend\` (`app.css`, `app.js`, `tema.js`).

Como foi feito: estudo do código-fonte do PCP (o mesmo arquivo servido pelo site) e depois conferência visual no site publicado, com login do Marlon, no navegador embutido do app Claude: Dashboard e Pedidos nos temas dia e noite, modal de Novo Pedido e tamanho de celular (375 px). O site confere com o código; o que a conferência acrescentou está na seção 2.7.

O módulo Produção não foi alterado e não deve ser tocado por este padrão agora: ele terá mudanças de layout e melhorias operacionais definidas depois.

---

## 1. Resumo

A pizzaria já usa a mesma moldura do PCP: menu lateral com seções, barra de topo com botão sanduíche, chave de tema noite e dia, chip do usuário e botão Sair. A paleta foi trocada (azul no PCP, âmbar e vermelho de forno na pizzaria), o que é intencional e deve ficar.

O que falta na pizzaria são os **componentes de conteúdo** do PCP: cartões de indicador (KPI), etiquetas de situação coloridas, tabela com moldura e cabeçalho fixo, barra de filtros e busca, janela modal, aviso flutuante (toast), estado vazio e paginação. Hoje cada tela da pizzaria resolve isso com `cartao`, `aviso` e `confirm()` do navegador, o que deixa as telas parecidas entre si mas pobres em leitura rápida.

---

## 2. Padrões do PCP

### 2.1 Estrutura da página

| Parte | Padrão PCP |
|---|---|
| Menu lateral | 262 px; recolhido 60 px (só ícones); fundo em gradiente vertical; borda direita de 1 px; rola sozinho |
| Marca | logo 30 px de altura + nome (14 px, negrito) + subtítulo em caixa alta (10 px, espaçado) |
| Seções do menu | rótulo 10 px, caixa alta, espaçamento 1,3 px, cor `--txt3` (Visão Geral, Operacional, Planejamento, Cadastros, Relatórios e Dados, Admin) |
| Item do menu | ícone emoji 15 px em coluna de 19 px + rótulo 13 px; raio 8 px; ativo com gradiente da cor da marca e faixa de 3 px à esquerda |
| Barra de topo | 56 px, fixa no alto (sticky), fundo `--bg2`; à esquerda sanduíche (36x36) e título da página (16 px, negrito); à direita chave de tema, chip do usuário e Sair |
| Conteúdo | preenchimento de 20 px, largura total da tela |
| Perfis | itens fora do perfil são escondidos (vendedor vê só Pedidos e Estoque; Admin só para administrador) |

### 2.2 Tema noite e dia

- Noite é o padrão. Dia é ativado por `data-theme="light"` no `<html>`.
- Todas as cores são variáveis CSS (tokens) redefinidas no tema dia: fundos (`--bg`, `--bg2`, `--panel`, `--panel2`), linhas (`--line`), três níveis de texto (`--txt`, `--txt2`, `--txt3`), marca (`--brand`, `--brand2`, `--accent`) e estados (`--crit`, `--alerta`, `--ok`, `--pot`), mais pares fundo e texto para cada etiqueta de situação.
- A escolha fica no `localStorage` **e também no servidor, por usuário** (`PATCH /auth/tema`); no login o tema salvo do usuário é aplicado. Assim o tema acompanha a pessoa em outro computador.
- Os gráficos leem as cores dos tokens na hora de desenhar e são redesenhados ao trocar o tema.
- A chave é um trilho de 38x21 px com bolinha, entre 🌙 e ☀️.

### 2.3 Tipografia

- Fonte do sistema: Segoe UI, system-ui, Arial. Corpo 14 px, entrelinha 1,45.
- Rótulos de campo, de filtro, de KPI e cabeçalho de tabela: 10 a 11 px, **caixa alta**, espaçamento 0,5 a 0,8 px, negrito, cor `--txt3`. É o traço mais marcante do visual.
- Títulos: página 16 px, painel 14 px, modal 15 px, todos negrito 700.
- Número de KPI: 26 px, peso 800, espaçamento negativo.
- Números em tabela: `font-variant-numeric: tabular-nums` (classe `mono`) para alinhar dígitos.

### 2.4 Componentes

| Componente | Como é no PCP |
|---|---|
| KPI | cartão com gradiente diagonal, raio 12 px, rótulo em caixa alta, valor grande, subtítulo pequeno, ícone gigante quase transparente no canto, faixa de cor de 3 px à esquerda conforme estado (`c-brand`, `c-ok`, `c-alerta`, `c-crit`). Grade automática, mínimo 170 px por cartão |
| Painel | fundo `--panel`, borda, raio 12 px, título 14 px com ícone, subtítulo `p-sub` em cinza |
| Duas colunas | `two-col`, vira uma coluna abaixo de 1100 px |
| Barra de filtros | painel horizontal com grupos rótulo + campo lado a lado, quebrando linha |
| Busca | campo com lupa desenhada à esquerda |
| Botões | primário na cor da marca; `ghost` (secundário com borda); `sm` (pequeno); `danger`, `ok`, `warn` (por estado) |
| Tabela | dentro de `tbl-wrap` (borda e raio, rolagem lateral); cabeçalho fixo com fundo `--bg2`; linha com destaque ao passar o mouse e clicável; texto em `--txt2` e destaque em negrito `--txt` |
| Etiqueta de situação | pílula arredondada, 11 px negrito, fundo translúcido + texto da mesma cor (Aberto azul, Em produção âmbar, Pronto verde, Expedido roxo, Cancelada e Atrasado vermelho) |
| Badge | marcador pequeno sólido (crit, alerta, ok) |
| Lista de alertas | faixa com borda esquerda de 4 px na cor do estado, no topo do painel |
| Modal | único e genérico (`openModal(título, corpo, rodapé)`): fundo escurecido com desfoque, caixa de até 540 px, cabeçalho com X, rodapé com botões à direita; fecha ao clicar fora |
| Formulário | dentro do modal; grade de duas colunas (`form-row`), `field.full` ocupa a linha toda |
| Toast | aviso flutuante no canto inferior direito, verde (ok) ou vermelho (erro), some em 3 s |
| Vazio | texto centralizado em cinza com 40 px de folga ("Carregando…", "Nenhum registro") |
| Paginação | "‹ Anterior · Pág X / Y · N registros · Próxima ›", alinhada à direita |
| Gráficos | Chart.js via CDN, cores dos tokens, rosca para distribuição e barras para séries |

### 2.5 Responsividade

- Abaixo de 1100 px: duas colunas e formulários viram uma coluna.
- Abaixo de 760 px: o menu vira gaveta que desliza da esquerda (230 px) com fundo escurecido; o sanduíche abre e fecha a gaveta em vez de recolher; KPIs em duas colunas; o chip do usuário some.
- O PCP precisou de um ajuste de camadas (z-index) para o sanduíche ficar acima da gaveta no celular, porque a barra de topo é fixa.

### 2.6 Login

Tela inteira com caixa central de 400 px (raio 16 px, sombra), logo no alto, título e subtítulo, campos com rótulo em caixa alta, botão largo, mensagem de erro em vermelho abaixo. Enter em qualquer campo entra.

### 2.7 O que a conferência visual mostrou

Pontos que funcionam bem e valem copiar:

- **Alertas antes dos números**: o Dashboard abre com as faixas de alerta ("14 matérias-primas abaixo do mínimo", "3 pedidos com prazo vencido") e logo abaixo os quatro KPIs. A pessoa vê primeiro o que pede ação.
- **KPIs leem bem nos dois temas**: faixa colorida à esquerda e ícone apagado no canto dão o estado sem poluir. No tema dia o cartão fica claro com sombra leve; no noite, gradiente escuro.
- **Barra de ações da lista**: busca com lupa, filtro de status com rótulo em caixa alta, botão Filtrar e "+ Novo Pedido" (secundário) na mesma linha, quebrando no celular.
- **Modal no tema noite**: fundo escurecido com desfoque, campos com rótulo em caixa alta e obrigatórios marcados com `*`, ação principal azul e Cancelar ao lado.
- **Logo da marca no menu** com o nome do sistema ao lado; no tema dia o logo vai sobre fundo escuro próprio, o que mantém o contraste.

Pontos fracos que a pizzaria deve evitar:

- **Tabela larga no celular e em telas médias**: em Pedidos as colunas quebram em várias linhas (cidade, vendedor) e as últimas colunas saem da tela, só acessíveis com rolagem lateral. Para a pizzaria, abaixo de 760 px a lista deve virar cartões (um por pedido, com número, cliente, situação e valor) em vez de tabela.
- **Gráficos gigantes em uma coluna**: abaixo de 1100 px as roscas ocupam a largura toda e ficam enormes, com a legenda pequena ao lado. Limitar a altura do gráfico (a classe `chart-wrap sm` usada no HTML não existe no CSS do PCP) e manter duas colunas até telas menores.
- **Subtítulo da marca cortado**: "PLANEJ. & CONTRO..." aparece cortado com o menu aberto em telas de até 830 px. Subtítulo curto ("Gestão integrada" já cabe).
- **Rótulo de KPI quebrando no celular**: "MP ABAIXO DO MÍNIMO" quebra em duas linhas. Rótulos de KPI com até cerca de 16 caracteres.
- **Gaveta do celular sem animação**: o menu aparece de uma vez (a transição só cobre a largura). Pequeno, mas um `transition: transform` resolve.
- **Chip do usuário some no celular** e não há outro lugar mostrando quem está logado. Na pizzaria, que divide tablet no balcão e na cozinha, o nome deve continuar visível (só o perfil pode sumir, como já é hoje).

---

## 3. O que a pizzaria já segue

- Mesma moldura: menu 250 px recolhível para 60 px, seções em caixa alta, item ativo com faixa de 3 px, topo de 56 px com sanduíche, título, chave de tema, chip e Sair.
- Mesmo esquema de tokens e de tema noite (padrão) e dia via `data-theme="light"`, com a chave igual.
- Mesma gaveta no celular abaixo de 760 px.
- Mesmos rótulos de campo em caixa alta.

Pontos em que a pizzaria já está **melhor** e deve manter:

- Itens do menu são `<button>` (acessíveis por teclado); no PCP são `<div>`.
- `tema.js` aplica o tema antes de desenhar, sem clarão branco.
- Fonte 15 px, campos maiores e botões de 44 px na produção: melhor para tablet e balcão.
- Barra de subabas (`subnav`) para dividir um módulo grande; o PCP não tem e usa mais itens no menu.
- Conteúdo com largura máxima de 1100 px e só a área de conteúdo rola (o topo nunca some).
- Chip mostra o perfil junto do nome.

---

## 4. Diferenças encontradas

| # | Assunto | PCP | Pizzaria hoje | Ação sugerida |
|---|---|---|---|---|
| 1 | Paleta | azul e verde-água | âmbar (noite) e vermelho forno (dia) | manter, é a identidade da pizzaria |
| 2 | Item ativo do menu | gradiente da cor da marca, texto branco | gradiente `--panel2`, texto normal | manter o da pizzaria (mais legível nos dois temas) |
| 3 | Tema por usuário | salvo no servidor e aplicado no login | só no navegador (`pz-tema`) | adotar: campo de tema no usuário e `PATCH /auth/tema` |
| 4 | KPIs | cartões com faixa de estado | não existem; Painel e BI usam texto e tabelas | adotar no Painel, Caixa, BI e Estoque |
| 5 | Etiquetas de situação | pílulas coloridas por estado | texto puro; `tr.destaque`, `tr.atrasado` | adotar `tag` com tokens para situação de pedido, conta, lista de compras |
| 6 | Tabela | moldura, cabeçalho fixo, linha com destaque | tabela simples em `.tabela` | adotar `tbl-wrap` e destaque de linha |
| 7 | Filtros e busca | `filterbar` e busca com lupa | `linha` e `acoes-linha` montados em cada tela | adotar `filterbar` e `busca` como padrão único |
| 8 | Confirmações | modal próprio | `confirm()`, `prompt()` e `alert()` do navegador | trocar por modal próprio, principalmente nas ações que não voltam (contagem de caixa, fechar CMV, desligar funcionário, lançar folha) |
| 9 | Retorno de ação | toast flutuante | `aviso` dentro da tela | usar toast para sucesso e manter `aviso` para erro e alerta que precisam ficar visíveis |
| 10 | Estado vazio e carregando | `empty` centralizado | parágrafo "Carregando..." solto | adotar `vazio` |
| 11 | Paginação | componente padrão | listas cortadas em 200 ("refine a busca") | adotar quando uma lista passar de 200 |
| 12 | Botões | primário, ghost, sm, danger, ok, warn | `principal` e `sec` | acrescentar `perigo` e `pequeno`; usar `perigo` em cancelar e excluir |
| 13 | Gráficos | Chart.js com cores dos tokens | nenhum | adotar no BI e no Painel, com a mesma regra de redesenhar ao trocar o tema |
| 14 | Cores fora dos tokens | todas em tokens | `td.negativo` e `tr.atrasado` usam `#e5484d` fixo; `.cartao.destaque` usa `--acento`, que não existe (cai no reserva `#e0a030`) | corrigir para `--crit` e `--accent` |
| 15 | Menu | seções contíguas | "Meus dados" está no grupo Visão geral mas listado depois de RH, o que cria uma segunda seção "Visão geral" | mover "Meus dados" para logo após Painel |
| 16 | Ícones do menu | um por item | repetidos: 📊 Painel e BI, 👥 Clientes e RH, 🧾 Vendas e Auditoria | trocar por ícones únicos (sugestão: BI 📉, RH 🧑‍🍳 ou 🪪, Auditoria 🔍) |
| 17 | Login | caixa com sombra, título e subtítulo | cartão simples com logo de 64 px | manter o da pizzaria; opcional acrescentar subtítulo "Gestão integrada" |
| 18 | Logo | `logo.png` da Allex | `logo.svg` provisório | continua provisório até a logo definitiva |

---

## 5. Como aplicar em `sistema/frontend`

1. **Kit de componentes em `app.css`**, numa seção própria "componentes PCP", usando só tokens: `kpis` e `kpi` (com `c-ok`, `c-alerta`, `c-crit`, `c-marca`), `tag` (com classes por situação e pares de tokens noite e dia), `tbl-wrap` (cabeçalho fixo, destaque de linha), `filterbar`, `busca`, `vazio`, `paginacao`, `toast`, `modal`, botões `perigo` e `pequeno`, `mono` para números. Nomes em português, como o restante do CSS da pizzaria.
2. **Ajudantes em `app.js`**, no mesmo estilo de `aviso()` e `h()`: `kpi(rotulo, valor, estado, sub)`, `etiqueta(situacao)`, `tabela(colunas, linhas)`, `modal(titulo, corpo, botoes)` que devolve uma Promise (substitui `confirm` e `prompt`), `toast(texto, erro)`, `vazio(texto)`.
3. **Correções pequenas** dos itens 14, 15 e 16 da tabela.
4. **Tema por usuário** (item 3): migration nova com coluna de tema no usuário (com CHECK `noite`/`dia`), rota `PATCH /auth/tema`, aplicar no login. `tema.js` continua evitando o clarão.
5. **Ordem de adoção nas telas**: Painel (KPIs), Caixa (KPIs e modal na contagem), Vendas (etiquetas de situação e toast), Estoque e Compras (filterbar, tabela, etiquetas), Contas, Custos, Imobilizado e RH (modal nas ações que não voltam), BI (KPIs e gráficos). Cadastros por último.
6. **Produção fica de fora** até o novo layout dela ser definido. Quando for desenhado, deve nascer já com este kit.

Regras para toda tela nova: cores só por token; nada de `confirm`/`prompt`/`alert`; situação sempre como etiqueta; listas em `tbl-wrap` no computador e em cartões abaixo de 760 px; alertas que pedem ação no topo da tela, antes dos KPIs; gráficos com altura limitada; títulos de cartão como `h2` de 16 px; número com `mono`; testar nos dois temas e em 760 px.

---

## 6. Recomendação

Manter a moldura e a paleta atuais da pizzaria, que já são o padrão PCP adaptado e em alguns pontos melhores (acessibilidade, tablet, subabas, rolagem só do conteúdo). O ganho real está em trazer o **kit de componentes de conteúdo** do PCP (KPIs, etiquetas de situação, tabela com moldura, filtros, modal e toast) e o **tema salvo por usuário**, aplicados como uma fatia própria de "padronização visual" antes de qualquer tela nova, começando pelo Painel e pelo Caixa. Junto dela, corrigir as três inconsistências pequenas (cores fixas, seção duplicada no menu, ícones repetidos). A conferência no site confirmou o padrão e acrescentou duas lições: alertas antes dos números, e listas em cartões no celular em vez de tabela larga. A Produção só recebe o kit quando o novo layout dela for definido.
