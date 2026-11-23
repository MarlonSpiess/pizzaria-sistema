-- Flag manual "loja aberta" (decisão de Marlon, 04/11/2026): a gerência liga quando já pode receber pedidos dos canais e desliga ao fechar.
-- Não muda sozinha. Desligada por padrão.
ALTER TABLE loja ADD COLUMN IF NOT EXISTS loja_aberta BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE loja ADD COLUMN IF NOT EXISTS loja_aberta_desde TIMESTAMPTZ;
