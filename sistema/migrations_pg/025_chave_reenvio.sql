-- Chave contra reenvio (duplo clique, rede lenta) nas gravações que somam valor ou quantidade,
-- no mesmo padrão do pedido de venda (004): a tela manda uma chave por formulário e o reenvio
-- devolve o que já foi gravado. Decisão de Marlon em 23/11/2026 (item C11 da revisão ub-mode 2).
-- Coluna opcional: o que já existe e quem não manda chave seguem como antes.
ALTER TABLE movimento_caixa ADD COLUMN IF NOT EXISTS chave TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_movimento_caixa_chave ON movimento_caixa (loja_id, chave) WHERE chave IS NOT NULL;

-- No título parcelado, a chave fica só na primeira parcela (as outras chegam pelo grupo_id).
ALTER TABLE titulo ADD COLUMN IF NOT EXISTS chave TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_titulo_chave ON titulo (loja_id, chave) WHERE chave IS NOT NULL;

ALTER TABLE lote_massa ADD COLUMN IF NOT EXISTS chave TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_lote_massa_chave ON lote_massa (loja_id, chave) WHERE chave IS NOT NULL;

-- Em perda, só a perda de massa usa a chave; perda de pizza segue sem ela.
ALTER TABLE perda ADD COLUMN IF NOT EXISTS chave TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_perda_chave ON perda (loja_id, chave) WHERE chave IS NOT NULL;
