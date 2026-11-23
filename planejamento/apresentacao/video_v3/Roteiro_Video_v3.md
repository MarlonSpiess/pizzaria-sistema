# Vídeo de apresentação do sistema (v3)

Vídeo para apresentar o Sistema Integrado da Pizzaria à diretoria. Mostra as telas reais do sistema em operação, com narração em português, legendas e trilha própria.

- **Versão completa:** `Sistema_Pizzaria_Apresentacao_Completa.mp4` (16 cenas).
- **Versão curta:** `Sistema_Pizzaria_Apresentacao_Curta.mp4` (cenas 01, 03, 04, 05, 10, 13, 14, 16).
- **Legendas separadas:** `.srt` com o mesmo nome de cada vídeo.

## Dados mostrados

Tudo o que aparece é **fictício**: loja "Pizzaria Demonstração", equipe (Ana, Carla, Bruno, Diego, Elisa, Fábio), clientes, telefones, endereços, insumos e custos. Nenhum dado real da loja nem senha de produção foi usado. Os preços de venda seguem só a regra do cardápio (Grande Tradicional R$ 35, Especial R$ 50, Broto R$ 25, Calzone R$ 50, Borda R$ 10).

O sistema gravado é o código do PR #6 (Checklists, migrações até 024), rodando num banco de demonstração recriado a cada gravação.

## Números citados (contados do código)

| Item | Valor | Origem |
|---|---|---|
| Versões do banco (migrações) | 24 | `fonte_v3/contagem.py` |
| Tabelas | 110 | `fonte_v3/contagem.py` |
| Rotas de API | 270 | `fonte_v3/contagem.py` |
| Testes automatizados | 374, todos passando em 23/11/2026 | `pytest` na suíte completa |
| Perfis e permissões | 8 e 55 | `sistema/api/security.py` |

## Roteiro cena a cena

| # | Cena | Na tela | Narração |
|---|---|---|---|
| 1 | Abertura | Abertura animada: relógio chega às 20:00 de sexta; o balcão enche, o telefone toca, o aplicativo apita. | Sexta-feira, oito da noite. O balcão enche, o telefone toca, o aplicativo não para de apitar. Numa pizzaria, cada minuto vale dinheiro. E cada erro também. |
| 2 | Problema | Memória, papel e planilha; três perguntas sem resposta: custo da pizza, sobra de estoque, diferença de caixa. | Em muitas pizzarias, a operação ainda depende de memória, papel e planilha. Ninguém sabe, na hora, quanto custou cada pizza, quanto sobrou no estoque, ou por que o caixa não bateu. |
| 3 | Solucao | Marca do sistema; 1 servidor na loja, 1 login por pessoa; cartões das 3 áreas. | Por isso nasceu o Sistema Integrado da Pizzaria. Um servidor dentro da loja. Um login por pessoa. Três áreas: Produção, Vendas e Administrativo. E cada pessoa vê exatamente o que precisa para o seu trabalho. Nem mais, nem menos. |
| 4 | Pedido | Navegador do balcão (Bruno, atendente): Grande meio Margherita, meio Quatro Queijos, borda de Catupiry; total R$ 52,50 com nota da regra meio a meio; Pix; urgente; confirmação com o número do dia. | Tudo começa no balcão. O atendente monta o pedido: uma grande, meio Margherita, meio Quatro Queijos, com borda de Catupiry. O sistema aplica a regra da casa sozinho: na pizza de dois sabores, metade do preço de cada um. Pagamento no Pix, pedido marcado como urgente, confirmado, e ele já recebe o número do dia. |
| 5 | Pizzaiolo | Tablet da montagem (Diego): Pegar a próxima pizza traz o pedido urgente; aproximação na pizza atual; Finalizada a montagem. | No mesmo instante, o pedido chega ao tablet do pizzaiolo. Ele não procura nada. Toca em pegar a próxima pizza, e o sistema entrega a próxima da fila, com o urgente na frente, com sabores e borda. Montou? Um toque, e a pizza segue para o forno. |
| 6 | Acabamento | Tablet do acabamento (Fábio): ocupação do forno; Saiu do forno; Acabada e etiqueta; nota: nenhum valor em reais nesta tela. | No acabamento, a tela mostra a ocupação do forno e avisa se passar da capacidade. A pizza sai do forno, é acabada, e o sistema gera a etiqueta com o número do pedido. Repare: a tela do acabamento não mostra o valor do pedido. Quem não precisa ver dinheiro, não vê. |
| 7 | Massa | Tablet da massa (Elisa): pizzas esperando e saldo de massa aberta; lança lote de 20. | A massa trabalha um passo à frente. A tela mostra quantas pizzas estão esperando e o saldo de massa aberta, por tamanho. Precisa de mais? Lança o lote, e pronto. |
| 8 | Acesso | Dois tablets lado a lado: menu do pizzaiolo e menu da gerente; nota: 8 perfis, 55 permissões, conferidas no servidor. | E esse controle não é só visual. Cada permissão é conferida no servidor, em cada chamada. São oito perfis e cinquenta e cinco permissões. O pizzaiolo enxerga a montagem. A gerente enxerga a operação inteira. |
| 9 | Caixa | Despacho escolhe o entregador; depois o caixa (Bruno) faz a contagem cega; o esperado aparece só depois, com R$ 5,00 de diferença no dinheiro. | Pedido pronto, o despacho escolhe o entregador, e só despacha com o caixa do dia aberto. No fim da noite, a contagem é cega: o caixa informa o que tem na gaveta, no Pix e nas maquininhas, e só depois o sistema revela o esperado. Diferença acima da tolerância exige justificativa e a aprovação de um gerente que não fez a contagem. |
| 10 | Estoque | Estoque (Carla, gerente): calabresa abaixo do mínimo; Fechar vendas dos sabores; no balcão, Calabresa aparece como VENDA FECHADA. | Cada pizza produzida baixa o estoque pela ficha técnica, ingrediente por ingrediente. A calabresa ficou abaixo do mínimo? O alerta aparece. Com um toque, a gerente fecha a venda de todos os sabores que levam calabresa, e no balcão eles ficam bloqueados na hora. Ninguém vende o que a cozinha não consegue entregar. |
| 11 | Custos | Custo e margem por produto e tamanho; realce em Frango com Catupiry. | Com a ficha técnica e o custo médio de compra, o sistema calcula o custo e a margem de cada produto, em cada tamanho. É aqui que se descobre quais sabores dão lucro de verdade. |
| 12 | Checklists | Checklist de início do dia: câmara fria 3 °C; freezer -12 °C fora do limite pede ação corretiva; aba Aderência. | A rotina também está no sistema. Os checklists de início do dia, acompanhamento e fechamento guiam a equipe item por item, com limite de temperatura da câmara fria e do freezer. Item fora do padrão pede ação corretiva, e a gerência acompanha a aderência. |
| 13 | Bi | BI: vendas, tempo médio, CMV do mês e alerta de CMV acima da meta; abas DRE e Lucratividade. | E tudo isso vira informação. O painel do dia mostra vendas, ticket médio, tempo médio, perdas, diferença de caixa e o custo da mercadoria vendida no mês. Passou da meta? O alerta aparece sozinho. E ainda tem DRE, lucratividade e produção. |
| 14 | Numeros | Números contados do código: 24, 110, 270, 374; selo: todos passando, revisão dupla. | Os números do projeto, contados direto do código: vinte e quatro versões do banco de dados, cento e dez tabelas, duzentas e setenta rotas de API e trezentos e setenta e quatro testes automatizados, todos passando. E cada entrega de código passa por dois revisores independentes. |
| 15 | Roadmap | Próximos passos: Anota Ai por API (aguardando acesso oficial), iFood, computador na loja para o piloto, nuvem. | Os próximos passos: a integração com o Anota Ai por API, já desenhada no sistema e aguardando o acesso oficial, com aceite automático dos pedidos. Depois, o iFood. Um computador na loja para o piloto. E a nuvem, quando fizer sentido. |
| 16 | Fechamento | Chamada à decisão: aprovar o piloto na pizzaria; marca e assinatura: Cada pizza, cada real, sob controle. | O sistema já funciona e já foi testado em tablet. O que falta é uma decisão: aprovar o piloto na pizzaria. Sistema Integrado da Pizzaria. Cada pizza, cada real, sob controle. |

## O que o vídeo não afirma

- O aceite de pedidos do Anota Ai (automático ou um a um) **ainda não existe**: aparece só em Próximos passos.
- O forno não é bloqueado pela capacidade: a tela mostra a ocupação e avisa.
- A baixa de estoque acontece quando a pizza é produzida (acabada), não no momento da venda.

## Como gerar de novo

Pasta `fonte/` (Linux com PostgreSQL local, Node com Playwright, ffmpeg com libass e a fonte Inter):

1. `SISTEMA=.../sistema DB_PASS=... DEMO_SENHA=... ./preparar_demo.sh` recria o banco `pizzaria_demo` e semeia os dados fictícios (recusa qualquer banco que não termine em `_demo` e servidor que não seja local).
2. `python gerar_narracao.py audio` gera a voz (edge-tts, voz pt-BR-AntonioNeural; precisa de internet, roda em qualquer PC).
3. `DEMO_SENHA=... DB_NAME=pizzaria_demo DB_PASS=... SISTEMA=... node gravar.js ../saida/cenas` grava as 16 cenas no tempo exato da narração (`TESTE=1` faz um ensaio só com capturas de tela).
4. `python montar.py ../saida/cenas ..` monta as duas versões, com trilha (`musica.py`, sintetizada, livre de direitos) e legendas.

Mudou o texto de uma cena em `narracao.json`? Gere a voz de novo e regrave a cena: o `montar.py` recusa cena gravada com narração antiga, com erro ou com atraso.

Os scripts passaram por revisão dupla (um revisor cego e um não cego), com os achados corrigidos antes da gravação final.
