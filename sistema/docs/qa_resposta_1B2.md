# Resposta ao QA cego da extensão 1B2

QA cego em docs/qa_cego_1B2.md. Situação após as correções, com 89 testes passando.

## Corrigidos
- **Alta:** a leitura da ficha arredondava a quantidade a 2 casas (0,0125 voltava 0,01) e o front reenviava o valor errado. A leitura agora devolve as 4 casas guardadas; há teste de ida e volta.
- **Média:** ciclo de preparos sob concorrência: a checagem agora roda sob trava (advisory lock) até o fim da transação.
- **Média:** item ou etapa inativado depois de usado travava o salvamento. Agora pode continuar na lista em que já está; um item inativo novo continua recusado. No front o seletor mantém o item usado.
- **Média:** a tela "O que falta" agora lista bordas e adicionais sem ficha, por tamanho.
- **Média:** resposta fora de ordem no editor de ficha podia gravar linhas na ficha errada; o dono da ficha agora é fixado ao abrir e respostas antigas são descartadas.
- **Baixa:** TRUNCATE recusado nas tabelas de ficha; erro de banco no iniciar-padrão agora é traduzido.

## Aceitos como estão
- Sem controle de versão na edição (o último a salvar vale): uma loja e poucos editores; cada salvamento cria versão e fica na auditoria.
- INSERT de linha em versão antiga pelo banco: só quem tem acesso direto ao banco; a API não faz isso.
- Ficha de produto inativo aceita: permite preparar a ficha antes de ativar.
- Perda padrão congelada ao salvar: é o desejado, a ficha guarda o valor da época.
- Linhas em ordem alfabética, não na ordem digitada; sem botão "Descer"; classe e unidade do item não editáveis (cadastrar outro item): ajustes de conforto para depois.
