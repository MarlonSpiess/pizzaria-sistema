-- O manual do Anota Ai mostra só 3 fases para o cliente (em análise, em produção, pronto) mais "finalizar".
-- "Pronto" já informa "a caminho" (entrega) ou "disponível para retirada". Eventos do sistema: pronto e finalizado.
-- Avisos antigos ainda não enviados são descartados (a regra mudou e o cliente seria avisado cedo demais).
ALTER TABLE aviso_canal DROP CONSTRAINT IF EXISTS aviso_canal_evento_check;
DELETE FROM aviso_canal WHERE enviado_em IS NULL AND evento IN ('saiu_entrega','disponivel_retirada');
DELETE FROM aviso_canal a USING aviso_canal b
 WHERE a.pedido_id = b.pedido_id AND a.id > b.id AND a.evento IN ('saiu_entrega','disponivel_retirada') AND b.evento IN ('pronto','saiu_entrega','disponivel_retirada');
UPDATE aviso_canal SET evento = 'pronto' WHERE evento IN ('saiu_entrega','disponivel_retirada');
ALTER TABLE aviso_canal ADD CONSTRAINT aviso_canal_evento_check CHECK (evento IN ('pronto','finalizado'));
