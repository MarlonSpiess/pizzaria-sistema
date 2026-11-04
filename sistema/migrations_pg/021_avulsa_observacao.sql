-- Observações lançadas por quem apontou o erro (acabamento ou pizzaiolo): a venda avulsa leva junto com as do pedido.
ALTER TABLE aviso_producao ADD COLUMN IF NOT EXISTS observacao TEXT;
