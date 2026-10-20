# Detalhamento 07: Imobilizado

Versão 0.1, 20/10/2026 (atualizada com M1, M2, M3 e M6). Rascunho para discussão, montado com o que Marlon já decidiu, com o plano macro (seção 4.2) e com boas práticas marcadas. Depende dos módulos já aprovados, em especial [Estoques e Compras](04_Estoques_e_Compras.md), [Contas e Fluxo de Caixa](05_Contas_e_Fluxo_de_Caixa.md) e [Custos](06_Custos.md).

**Critério de sucesso:** Marlon responde as perguntas da seção 6, corrige o desenho e diz "é assim". Só então o módulo vira v0.2 para aprovação.

Marcações: **[Decisão]** é de Marlon; **[Prática]** é boa prática sem fonte específica; **[Suposição]** é minha e precisa de confirmação.

---

## 1. O que já está decidido

- Objetivo: controlar os bens de uso da pizzaria (forno, masseira, freezer, motos, móveis, computadores) e o custo que geram ao longo do tempo **[Plano Macro]**.
- A **depreciação** do forno e dos equipamentos entra no custo fixo, **vinda do Imobilizado** **[Decisão L12]**.
- Empréstimos e financiamentos são **títulos parcelados**, **ligados ao Imobilizado quando for bem** **[Decisão K11]**.
- A compra de um bem vem de Estoques e Compras (nota fiscal digitada no começo) e gera o título em Contas a Pagar **[Decisão J9 e J10]**.
- Material de uso e consumo é item de Estoques, não bem do imobilizado **[Decisão E1]**.
- Equipamentos já planejados para a loja: 2 PCs na recepção, 1 tablet de massa, 2 de pizzaiolo, 1 de acabamento com impressora térmica portátil, forno esteira, com variações de modelo **[Decisão P9, A6 e H7]**.
- Uma loja, um banco por loja, identificador da loja em todo registro; cada loja é uma empresa à parte **[Decisão P2 e K1]**.
- Taxas fiscais de referência: IN RFB 1.700/2017, Anexo III (máquinas e equipamentos 10% ao ano, móveis e utensílios 20%, veículos 25%) (Plano Macro, fonte 3).

---

## 2. Objetivo

Registrar cada bem com valor, data, local e responsável, calcular a depreciação mensal, agendar e guardar a manutenção, e dar baixa quando o bem sai, entregando o custo a Custos, Contas e BI.

---

## 3. Submódulos propostos **[Prática, a confirmar]**

| Submódulo | O que faz |
|---|---|
| Cadastro de bens | Nome, categoria, valor, data de aquisição, nota, fornecedor, local, responsável, plaqueta, número de série |
| Depreciação | Mensal, a partir da data de início de uso, por taxa fiscal (padrão) ou por vida útil real; valor residual opcional |
| Manutenção | Agenda preventiva e histórico corretivo, com custo, data, fornecedor e próxima data |
| Baixa | Venda, perda, descarte ou doação, com motivo, data e valor |
| Seguros e garantias | Vencimento da garantia e da apólice, com alerta |
| Inventário de bens | Conferência periódica do que existe e onde está |

### 3.1 Manutenção ampliada **[Decisão M6, desenho Prática]**

Marlon pediu a **rotina completa de manutenção**, com controle de custos, materiais de manutenção e equipamentos. Proposta:

| Parte | O que faz |
|---|---|
| Plano preventivo | Tarefas periódicas por bem (limpeza do forno, revisão, troca de peça), por tempo ou por uso, com alerta antes do vencimento |
| Manutenção preditiva | Acompanha leituras do bem (horas de uso, temperatura, consumo, ruído registrado em inspeção) e avisa quando uma leitura sai do normal, antes da quebra |
| Manutenção corretiva | Registro da quebra, com data e hora da parada e da volta, causa e o que foi feito |
| Ordem de serviço | Um número por manutenção, com bem, tipo, responsável (funcionário ou terceiro), peças, horas e custo; abre, executa e fecha |
| Materiais de manutenção | Peças e insumos de manutenção como classe de item em Estoques e Compras, com saldo e baixa pela ordem de serviço |
| Ferramentas e equipamentos de manutenção | Cadastro como bem ou como item de uso e consumo, conforme o valor |
| Custos | Custo da manutenção por bem e por tipo, vindo da ordem de serviço, para Custos e Contas a Pagar |
| Paradas | Tempo parado por bem, para medir o impacto na produção |

**Referência de taxas.** Para a DRE gerencial pode fazer mais sentido a vida útil real do bem; proponho permitir as duas, com a fiscal como padrão (Plano Macro).

---

## 4. Integrações

| Com | O que passa | Direção |
|---|---|---|
| Estoques e Compras | Aquisição de bem, com nota, valor e fornecedor | Estoques para Imobilizado |
| Contas a Pagar | Parcelas e financiamento do bem; manutenções | Contas para Imobilizado e Imobilizado para Contas |
| Custos | Depreciação mensal como custo fixo | Imobilizado para Custos |
| BI | Depreciação na DRE gerencial | Imobilizado para BI |
| Produção | Equipamentos em uso (forno, tablets, impressora) e falhas | Produção para Imobilizado, a confirmar |

Cada ligação tem forma manual, para o módulo funcionar sozinho **[Prática]**.

---

## 5. O que os módulos aprovados deixaram para cá

1. **Quem decide o que é bem:** compra de equipamento caro entra aqui, e compra de insumo entra em Estoques. Falta o limite de valor que separa bem de despesa.
2. **Depreciação por loja:** como cada loja é uma empresa à parte, o bem pertence a uma loja.
3. **Equipamentos de produção:** o forno esteira e os tablets são bens críticos; uma falha trava a produção, então a manutenção importa.
4. **Parcela de financiamento:** vem de Contas; o bem fica ligado ao título parcelado.

---

## 6. Perguntas

### 6.1 Respondidas por Marlon em 20/10/2026

- **M1:** os bens são **cadastrados um a um** **[Decisão]**.
- **M2:** **valor mínimo** para ser bem nos parâmetros, **confirmado com o contador** **[Decisão]**.
- **M3:** depreciação pelos **dois métodos**, com a **taxa fiscal como padrão** **[Decisão]**.
- **M6:** **agenda por bem, com alerta antes do vencimento**, e Marlon pediu montar **toda a rotina de manutenção, preventiva, preditiva e corretiva**, com controle de custos, materiais de manutenção, equipamentos e outros (seção 3.1) **[Decisão]**.

### 6.2 Em aberto


| # | Pergunta | Minha recomendação |
|---|---|---|
| M1 | Quais bens a loja tem hoje? Existe lista, planilha ou nota fiscal? | Carregar por planilha na primeira vez |
| M2 | A partir de qual valor uma compra é bem do imobilizado (por exemplo, acima de R$ 1.200) e não despesa? | Valor mínimo nos parâmetros; confirmar com o contador |
| M3 | Quer depreciar pela taxa fiscal, pela vida útil real, ou os dois? | Os dois, com a fiscal como padrão |
| M4 | Os bens têm valor residual esperado (o que vale no fim da vida)? | Zero por padrão, alterável por bem |
| M5 | A depreciação começa na compra ou quando o bem entra em uso? | Quando entra em uso |
| M6 | Há manutenção preventiva programada (limpeza do forno, revisão da moto, outros)? De quanto em quanto tempo? | Agenda por bem, com alerta antes do vencimento |
| M7 | A manutenção é feita por terceiro, funcionário ou ambos? | Registrar fornecedor ou responsável em cada manutenção |
| M8 | Existe seguro ou garantia que valha controlar? | Sim, com data de vencimento e alerta |
| M9 | A loja tem motos ou veículos próprios, ou só entregadores terceiros? | Só terceiros, como já definido; sem veículos no cadastro |
| M10 | Há bens de uso do proprietário misturados com os da loja? | Separar; só o que é da loja entra |
| M11 | Quem cadastra, quem dá baixa e quem aprova a baixa? | Cadastra o gerente ou subgerente; baixa aprovada pelo administrador |
| M12 | Quer plaqueta ou etiqueta com código em cada bem e inventário periódico? | Sim, com inventário anual |

---

### 6.3 Novas, vindas do pedido de manutenção completa

| # | Pergunta | Minha recomendação |
|---|---|---|
| M13 | Quais bens precisam de plano preventivo hoje (forno esteira, masseira, freezer, câmara, tablets, impressora, outros) e com que periodicidade? | Começar pelo forno, a câmara e o freezer, e crescer |
| M14 | A manutenção preditiva usa que leitura em cada bem (horas de uso, temperatura, consumo, outra)? Quem faz a leitura e com que frequência? | Começar com leitura digitada na inspeção; sensores automáticos só no futuro |
| M15 | Peças e materiais de manutenção ficam em estoque ou são comprados na hora? | Estoque mínimo só das peças críticas, o resto comprado por ordem de serviço |
| M16 | Quem abre, quem executa e quem aprova a ordem de serviço? Há valor acima do qual o administrador aprova? | Abre qualquer perfil de gestão; executa funcionário ou terceiro; aprova o administrador acima de um valor nos parâmetros |
| M17 | A parada de um bem crítico (forno) deve avisar a produção e registrar o tempo perdido? | Sim, com o tempo parado ligado ao pedido atrasado, quando houver |
| M18 | O custo da manutenção é custo fixo (contrato mensal) ou variável (por chamado), ou os dois? | Os dois, marcados por tipo de despesa, como em Custos |

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Fórmulas finais de depreciação (linha reta), valor residual e baixa parcial.
- Reavaliação e impairment, que ficam com o contador.
- Carga inicial dos bens: depende da lista que Marlon vai enviar.
