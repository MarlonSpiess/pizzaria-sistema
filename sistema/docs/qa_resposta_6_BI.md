# Resposta ao QA cego de RH e BI

## Corrigido
- A1 salário vazando: `/custos/resultado` sem `rh.salarios` oculta pessoal, custos fixos, resultado e ponto de equilíbrio; `/contas/titulos` não lista o título da folha; `/auditoria` não mostra contrato, benefício, resumo e lançamento da folha; o alerta de fluxo do painel só aparece para quem vê salários.
- A2 o desligamento recusa funcionário ligado a administrador ou proprietário (409, desvincular antes).
- M1 lançar folha com resumo do contador incompleto dá 409.
- M7 mês do RH entre 2000 e 2100.
- M8 perdas do painel no fuso de Brasília.

## Pendente (segue a recomendação; Marlon avalia depois)
- M2 correção de resumo da folha e de contrato futuro errado (hoje só inserção).
- M3 limite de hora extra contornável com datas retroativas.
- M4 turno e ponto que passam da meia-noite (importante para a pizzaria; próxima rodada).
- M5 deadlock entre desligar e novo contrato; M6 compensação concorrente do banco de horas.
- Baixas: pró-rata na prévia, ponto após desligamento, sobreposição de férias e atestado, pizza meio a meio atribui a receita ao sabor 1, sinal do saldo negativo na tela Meus dados.
