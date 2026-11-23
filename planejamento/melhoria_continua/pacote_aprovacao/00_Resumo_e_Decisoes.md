# Pacote de aprovação: melhoria contínua e checklists

**Para:** Marlon. **Data:** 16/11/2026. **Situação:** proposta já implementada no código a pedido do usuário, ainda sem a sua aprovação e sem o piloto em papel. Os documentos aprovados (Plano Macro v2.0 e módulos) não foram alterados. **As respostas abaixo agora decidem o que manter, ajustar ou desligar no sistema**, em vez de autorizar a construção. Os testes novos foram escritos mas não executados; falta rodar a suíte antes do uso na loja. Detalhes em 03_Praticas_e_Melhorias.

## 1. O que se pede

Responder as decisões abaixo com "Aprovo", "Ajusto" (escrevendo o que muda) ou "Não". Em ordem de urgência:

1. **Esta semana, sem código:** aprovar o piloto em papel dos checklists (bloco A).
2. **Mudanças pequenas no sistema:** M1 e M2 (bloco B).
3. **Direção do módulo de Checklists dentro do sistema (M4):** dez decisões (bloco C).
4. **Depois, junto do novo layout da Produção:** M3 e as demais (bloco D).

## 2. Em uma página: o que foi levantado

- Hoje o sistema registra o **pedido** do começo ao fim, mas não o **dia de trabalho**: não há checklist de abertura, de acompanhamento nem de fechamento, nem registro de temperatura, limpeza e higiene.
- Foram montados **três checklists do dia** (31, 17 e 27 itens, setor a setor, com limpeza e higiene no fechamento) e **três pontos de controle por pedido** (18 itens), cada item com critério, responsável por função e origem.
- A pesquisa foi feita em revistas do setor, fornecedores e guias de vigilância sanitária e do Sebrae. Boa parte é de fornecedores e dos EUA; trate como prática de mercado.
- No código, já estão feitas as mudanças M1 e M2 (resumo do pedido com leitura de volta; tempos até atribuir e até a saída no BI) e o módulo de Checklists (M4, fatias 4A e 4B, com a ligação à loja aberta). Ficaram de fora a conferência de bebida no despacho (M3, aguarda o novo layout da Produção) e a edição de modelos por tela.
- O módulo de Checklists (M4) é grande e só deve ser construído depois de 2 a 3 semanas de piloto em papel.

## 3. O que há no pacote

| Arquivo | Para quê |
|---|---|
| 01_Checklists_da_Pizzaria.docx | Os checklists para imprimir: início, acompanhamento e fim do dia, e início, acompanhamento e fim do pedido. É o que roda no piloto em papel. |
| 02_Modulo_Checklists_M4.docx | Como seria o módulo de Checklists dentro do sistema: dados, regras, permissões, telas, fatias e riscos. |
| 03_Praticas_e_Melhorias.docx | As melhorias propostas para o sistema (M1 a M8), as fases, os valores a definir e os limites da pesquisa. |
| 04_Lista_compacta_pizzaria.docx | As 14 boas práticas por etapa (atendimento, produção, acabamento, entrega), com a situação de cada uma no sistema. |

## 4. Decisões

### Bloco A. Esta semana, sem código

| # | Decisão | Sugestão | Resposta |
|---|---|---|---|
| A1 | Rodar os checklists em papel por 2 a 3 semanas, sem mudar o sistema? | Sim. Começar pelo Checklist 1 (início), o 3 (fim do dia) e os pontos do pedido. Os demais entram depois. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| A2 | Quem preenche e quem confere? | Cada função preenche os itens dela; o gerente ou subgerente do turno confere e assina o conjunto. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| A3 | Os valores da tabela "Valores a definir" (final deste documento) podem ser preenchidos agora? | Preencher o que for possível; o que ficar em branco continua "a definir" nos checklists. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |

### Bloco B. Mudanças pequenas no sistema

| # | Decisão | Sugestão | Resposta |
|---|---|---|---|
| B1 | M1: mostrar telefone, endereço e entrega sugerida no resumo do pedido de balcão, só leitura. | Aprovar. Mudança pequena, só de tela, para o atendente ler o pedido de volta. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| B2 | M2: mostrar no BI o tempo do pedido até atribuir o entregador e até a saída (despacho). O tempo na rua não é medido, porque o sistema não registra a chegada ao cliente. | Aprovar, com a regra de atribuir o entregador na hora em que ele sai. Decidir se vale registrar a chegada ao cliente para medir a rua. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |

### Bloco C. Módulo de Checklists (M4)

| # | Decisão | Sugestão | Resposta |
|---|---|---|---|
| M4-1 | "Loja aberta" fica bloqueada até concluir o checklist de início? | Só aviso na primeira versão; bloquear depois, se a equipe aderir. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-2 | Quem pode marcar "não se aplica", e com que motivo? | Qualquer perfil, com motivo curto e relatório para a gerência. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-3 | Qual a cadência do checklist de acompanhamento? | Começar a cada hora no pico e menos fora dele; ajustar pelo piloto. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-4 | Limites e frequência de temperatura das câmaras. | Começar em 5 °C (refrigerado) e -18 °C (congelado), conferindo com a vigilância local. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-5 | Itens que o sistema já sabe ficam automáticos ou o gerente marca? | Automáticos e só leitura. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-6 | Pendência aberta impede fechar o dia ou o caixa? | Não. Só aparece como alerta. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-7 | Fotos de evidência entram no futuro? | Deixar fora da primeira versão. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-8 | Quem edita os modelos de checklist? | Administrador e proprietário; a gerência propõe. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-9 | Por quanto tempo guardar os registros? | Definir com orientação jurídica e a vigilância (pendência de LGPD do plano). | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| M4-10 | Construir o módulo só depois do piloto em papel? | Sim. Assim o conteúdo final vem do que a equipe realmente usou. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |

### Bloco D. Depois, com o novo layout da Produção

| # | Decisão | Sugestão | Resposta |
|---|---|---|---|
| D1 | M3: conferir bebida e acompanhamento no despacho, sem valores, com marca de "conferido". | Decidir se é obrigatório ou só aviso. Mexe numa decisão aprovada e na tela de despacho, que depende do novo layout da Produção. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |
| D2 | M5 a M8 (valores numéricos, recorrência, pauta da revisão semanal, horário de temperagem da massa). | Deixar para depois do piloto. M5 e M6 fazem parte do M4. | [ ] Aprovo  [ ] Ajusto  [ ] Não. Obs.: |

## 5. Valores a definir (para os checklists)

| O que definir | Quem define ou onde está | Valor da loja |
|---|---|---|
| Temperatura e pré-aquecimento do forno | Manual do forno e receita |  |
| Tempos da massa (descanso, temperagem, janela de uso) | Receita da loja |  |
| Tempos-alvo por etapa (massa, montagem, forno, acabamento, despacho) | Marlon, com base no histórico do BI |  |
| Frequência da leitura de temperatura das câmaras durante o turno | Marlon e vigilância sanitária local |  |
| Limites de temperatura de recebimento por produto | Manual de Boas Práticas da loja |  |
| Cronograma de limpeza periódica (coifa, câmara, reservatório, pragas) | Manual de Boas Práticas e normas locais |  |
| Se "loja aberta" fica bloqueada até o checklist de início ser concluído | Marlon |  |
| Cadência do acompanhamento (a cada hora ou outra) | Marlon |  |
| Meta de CMV e de custo de pessoal da loja | Marlon e contador |  |

## 6. Limites e cuidados

- Os limites de temperatura vêm de materiais secundários que citam a RDC 216/2004. O texto oficial não foi lido; confirmar com a vigilância sanitária do município.
- Os checklists são registros de apoio. Não substituem o Manual de Boas Práticas e os POPs que a loja precisa ter.
- A referência de CMV de 30 a 40% vem de páginas de fornecedores que atribuem o dado ao Sebrae; a página original não foi encontrada.
- O código foi lido só em parte; o BI e o restante não foram lidos. Nomes de tabelas e rotas do M4 são suposições.
- O layout dos arquivos Word não foi verificado visualmente.

## 7. Depois da resposta

1. Com o bloco A aprovado, imprimir os checklists e rodar o piloto.
2. Com o bloco B aprovado, abrir as duas mudanças pequenas, com testes.
3. Ao fim do piloto, revisar os itens, fechar o bloco C e só então desenhar a fatia 4A do M4.

**Resposta de:** ______________________   **Data:** ____/____/______
