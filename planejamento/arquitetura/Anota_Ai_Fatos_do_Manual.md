# Anota Ai: o que o manual de atendimento confirma

Fonte: "Manual do Usuário, Atendendo Pedidos pelo Celular na Anota Ai" (Setembro de 2026, enviado por Marlon). É manual de USO do aplicativo, não a documentação da API. Segundo o próprio manual, baseia-se na Central de Ajuda (anota.ai/ajuda).

## Confirmado pelo manual

- **Três fases do pedido**: Em análise (vermelho), Em produção (laranja), Pronto (verde). Depois, "Finalizar Pedido".
- **Em análise**: o pedido chega aqui. É preciso **Aceitar Pedido** em até **15 minutos**; sem resposta, o Anota Ai **cancela sozinho**, sem segunda chance.
- **Em produção**: avança sozinho depois de aceitar; o cliente é avisado de que o preparo começou. Sem prazo.
- **Pronto** ("Avançar para Pronto"): o cliente é informado de que o pedido está **a caminho** (delivery) ou **disponível para retirada**. Se a entrega for pelo Entrega Aí do Anota Ai, o motoboy é atribuído aí.
- **Finalizar Pedido**: encerra o atendimento; o pedido passa a contar nos relatórios do dia. Existe também "Enviar para finalizado" (pula as fases).
- **Cancelar pedido**: possível a qualquer momento, mesmo depois de aceito.
- Outras ações: Resumo, Re-imprimir, Editar (itens), Emitir nota fiscal (só plano Gestão Avançada).
- Tipos de pedido: delivery, retirada, mesa. Pedido de balcão ou telefone entra pelo botão "+" na loja.
- Fechar loja temporariamente (30 min, 1 h, resto do dia) pausa só pedidos novos.
- Aplicativo só para Android; no iPhone, pelo navegador (admin.anota.ai/login).

## O que isso muda na integração

1. **"Saiu para entrega" e "disponível para retirada" são a MESMA fase no Anota Ai: Pronto.** Os eventos do sistema passaram a ser `pronto` e `finalizado`.
2. Retirada: `acabado` envia Pronto; `despachado ou retirado` envia Finalizado.
3. Entrega: Pronto só quando o entregador sai (despachado), para o cliente não ser avisado cedo. Finalizar a entrega fica **pendente**: o sistema não tem confirmação de que o cliente recebeu. Decisão de Marlon (recomendação: finalizar junto com o despacho, ou ao acertar o entregador).
4. **Aceitar o pedido em até 15 minutos é obrigatório**, e é uma chamada à API que ainda não existe no sistema. Até existir, a tela Canais mostra há quantos minutos o pedido espera. Por isso a varredura rápida faz sentido.
5. Cancelamento: o manual confirma que existe no Anota Ai. O sistema ainda não avisa o cancelamento (pendente).

## O que ainda falta (só a documentação da API responde)

- Endereços, autenticação e formato dos pedidos e das chamadas (listar novos, aceitar, avançar para pronto, finalizar, cancelar).
- Limite de chamadas (a cada 1 segundo pode passar do limite).
- Identificador do pedido no Anota Ai e como ele chega para o sistema.
- Como o código externo de produto e de forma de pagamento aparece no pedido.
