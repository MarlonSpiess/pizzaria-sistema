# Manual do Usuário: Administrador e proprietário

Versão 2.0, 04/11/2026. Administrador e proprietário têm **todas** as permissões. Leia antes o [manual da gerência](06_Gerencia.md); aqui está só o que é exclusivo de vocês.

## 1. Usuários (Administrativo > Usuários)

- Crie **um login por pessoa**, com o perfil certo: massa, pizzaiolo, acabamento, atendente, subgerente, gerente, proprietário ou administrador. Nunca compartilhe login.
- A senha inicial é trocada pela pessoa no primeiro acesso. **Redefinir senha** obriga uma nova troca.
- Desativar o usuário encerra as sessões dele na hora.
- Mudou a função? Troque o perfil. A permissão vale a partir da próxima ação da pessoa.

Regra de ouro: cada função só vê a sua tela, e isso é conferido no servidor. Dar um perfil maior "para facilitar" abre valores e dados que a função não deve ver.

## 2. Parâmetros (Administrativo > Parâmetros)

Só vocês editam. Cada alteração guarda o histórico (quem, quando, valor anterior). Preencha antes do primeiro dia:

| Grupo | O que definir |
|---|---|
| Vendas | Formas de pagamento aceitas, limite de desconto do atendente, do subgerente e do gerente (vazio = 0, todo desconto pede autorização), taxa de entrega, vender só com caixa aberto |
| Entregas | Valor por entrega e diária do entregador |
| Caixa | Fundo de troco padrão, tolerância de diferença, limite de sangria sem gerente |
| Produção | Tempo de forno, pizzas por vez, minutos de montagem e de acabamento, pizzaiolos ativos, deslocamento, tamanho de massa do calzone |
| Estoque e compras | Dias de alerta de validade, perda padrão das fichas, valor de compra que exige aprovação |
| Contas, imobilizado e RH | Valor de título que exige aprovação, valor mínimo de bem (confirmar com o contador), valor de OS que exige aprovação, encargos estimados, limite de hora extra |
| BI | Meta de CMV e alertas ligados |

## 3. Canais (Vendas > Canais)

Exclusivo de administrador e proprietário:

- **Ativar ou desativar** o canal. O sistema só consulta o Anota Ai com o canal ativo **e** com o endereço e o token configurados no servidor (variáveis de ambiente, nunca na tela).
- **Mapa de produtos:** informe o **ID externo** de cada produto, o mesmo do campo "ID Externo" do gerenciador de cardápio do Anota Ai.
- **Aceitar sozinho:** vem desligado. Ligado, o sistema aceita o pedido sem a gerência quando o canal está ativo, a **loja está aberta** (chave da gerência), o **caixa de hoje** está aberto, **todos os itens** estão no mapa e nenhum sabor está com a venda fechada. Desligado, ou se algum critério falhar, a gerência aceita cada pedido.

Hoje a integração **não está conectada**: falta o token e a documentação da API do Anota Ai, que se pede por chamado. Até lá, nada é aceito automaticamente.

## 4. Aprovações exclusivas

- Títulos a pagar lançados à mão acima do valor do parâmetro (Contas).
- Ordens de serviço acima do valor do parâmetro e baixa de bem (Imobilizado).
- Folha gerencial e salários (RH > Folha gerencial): prévia, resumo e lançamento em Contas.
- Diferença de caixa (também o gerente), sempre por quem não fez a contagem.

## 5. Sistema

- **Backup:** botão "Fazer backup agora" no Painel e comando `python scripts\backup.py` no PC da loja. A rotina diária fora da máquina está adiada; até lá, faça ao fechar o dia e copie para um pen drive.
- **Auditoria:** consulte quem fez cada ação. Ninguém, nem o sistema, consegue apagar a auditoria.
- Instalação, variáveis e solução de problemas: [Manual Técnico](../tecnico/Manual_Tecnico.md).
