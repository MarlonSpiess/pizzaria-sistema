-- Fechar vendas por ingrediente (decisão de Marlon, 04/11/2026): marcar um ingrediente "em falta" fecha a venda de todos os sabores
-- que o usam e o sistema pede ao canal para pausar esses produtos. Reabrir faz o inverso. O fechamento do produto é CALCULADO
-- a partir dos ingredientes em falta, nunca guardado, para não ficar fora de sincronia.
CREATE TABLE IF NOT EXISTS ingrediente_em_falta (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    desde TIMESTAMPTZ NOT NULL,
    marcado_por BIGINT REFERENCES usuario(id),
    reaberto_em TIMESTAMPTZ,
    reaberto_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ingrediente_em_falta_ativo ON ingrediente_em_falta (loja_id, item_id) WHERE reaberto_em IS NULL;

-- O que já foi pedido ao canal: o sistema compara com o que deveria ser e corrige a diferença (repetir é seguro).
ALTER TABLE mapa_produto_canal ADD COLUMN IF NOT EXISTS pausado_no_canal BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE mapa_produto_canal ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;
ALTER TABLE mapa_produto_canal ADD COLUMN IF NOT EXISTS erro_sincronia TEXT;
