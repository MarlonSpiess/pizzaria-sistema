-- Importar = ler o pedido na fila do canal, aceitar no canal e criar o pedido no sistema (definição de Marlon, 04/11/2026).
-- Estados da entrada: pendente (chegou), importando (no meio do processo), importada (aceita e criada),
-- bloqueada (a loja não pode produzir: espera decisão da gerência) e recusada.
ALTER TABLE entrada_canal DROP CONSTRAINT IF EXISTS entrada_canal_situacao_check;
ALTER TABLE entrada_canal ADD CONSTRAINT entrada_canal_situacao_check
    CHECK (situacao IN ('pendente','importando','importada','bloqueada','recusada'));
ALTER TABLE entrada_canal ADD COLUMN IF NOT EXISTS pedido_id BIGINT REFERENCES pedido(id);
ALTER TABLE entrada_canal ADD COLUMN IF NOT EXISTS importando_desde TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS uq_entrada_pedido ON entrada_canal (pedido_id) WHERE pedido_id IS NOT NULL;
ALTER TABLE entrada_canal ADD COLUMN IF NOT EXISTS importacao_tentativas INTEGER NOT NULL DEFAULT 0;
-- Flag do canal: aceitar sozinho (decisão de Marlon, 04/11/2026). Desligada por padrão: o pedido é aceito explicitamente pela gerência.
ALTER TABLE canal_venda ADD COLUMN IF NOT EXISTS aceitar_sozinho BOOLEAN NOT NULL DEFAULT false;
