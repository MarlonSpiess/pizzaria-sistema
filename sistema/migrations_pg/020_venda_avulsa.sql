-- Venda da pizza avulsa: lançada como pedido de balcão (preço do cardápio, desconto pelas regras de sempre).
-- O item do pedido aponta para a pizza avulsa vendida; essa pizza não gera nova pizza na Produção.
ALTER TABLE item_pedido ADD COLUMN IF NOT EXISTS avulsa_pizza_id BIGINT REFERENCES pizza_producao(id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_item_avulsa ON item_pedido (avulsa_pizza_id) WHERE avulsa_pizza_id IS NOT NULL;
ALTER TABLE pizza_avulsa_destino ADD COLUMN IF NOT EXISTS pedido_id BIGINT REFERENCES pedido(id);
