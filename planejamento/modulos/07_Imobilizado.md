# Detalhamento 07: Imobilizado

Versão 0.2, 20/10/2026. Consolidada com as respostas M1 a M18 de Marlon. **APROVADA por Marlon em 20/10/2026.** Montada com o que Marlon já decidiu, com o plano macro (seção 4.2) e com boas práticas marcadas. Depende dos módulos já aprovados, em especial [Estoques e Compras](04_Estoques_e_Compras.md), [Contas e Fluxo de Caixa](05_Contas_e_Fluxo_de_Caixa.md) e [Custos](06_Custos.md).

**Critério de sucesso:** Marlon lê o desenho e as respostas da seção 6 e diz "aprovado" ou aponta o que corrigir.

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

### 6.2 Respondidas em 20/10/2026 (recomendações aceitas)

- **M4:** valor residual zero por padrão, alterável por bem **[Decisão]**.
- **M5:** a depreciação começa quando o bem entra em uso **[Decisão]**.
- **M7:** a manutenção é feita por terceiro, funcionário ou ambos; fornecedor ou responsável registrado em cada ordem de serviço **[Decisão]**.
- **M8:** seguro e garantia são controlados, com vencimento e alerta **[Decisão]**.
- **M9:** **inicialmente só entregadores terceiros**, sem veículos no cadastro; **no futuro pode haver veículos próprios**, então o cadastro de bens deve aceitar a categoria veículo (placa, quilometragem, documentos) sem mudar a estrutura **[Decisão]**.
- **M10:** só o que é da loja entra; bens do proprietário ficam fora **[Decisão]**.
- **M11:** cadastra o gerente ou o subgerente; a baixa é aprovada pelo administrador **[Decisão]**.
- **M12:** plaqueta ou etiqueta com código em cada bem, com inventário anual **[Decisão]**.
- **M13:** plano preventivo começa pelo forno, a câmara e o freezer, e cresce **[Decisão]**.
- **M14:** a preditiva começa com leitura digitada na inspeção; sensores automáticos só no futuro **[Decisão]**.
- **M15:** estoque mínimo só das peças críticas; o resto é comprado por ordem de serviço **[Decisão]**.
- **M16:** abre qualquer perfil de gestão, executa funcionário ou terceiro, e o administrador aprova acima de um valor nos parâmetros **[Decisão]**.
- **M17:** a parada de um bem crítico avisa a produção e registra o tempo parado, ligado ao pedido atrasado quando houver **[Decisão]**.
- **M18:** o custo de manutenção pode ser fixo (contrato) ou variável (chamado), marcado por tipo de despesa **[Decisão]**.

Todas as perguntas do módulo estão respondidas.

---

## 7. O que este documento ainda não cobre

- Telas e fluxo de cliques.
- Fórmulas finais de depreciação (linha reta), valor residual e baixa parcial.
- Reavaliação e impairment, que ficam com o contador.
- Carga inicial dos bens: depende da lista que Marlon vai enviar.
