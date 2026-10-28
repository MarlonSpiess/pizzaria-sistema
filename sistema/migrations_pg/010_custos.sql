-- Fatia 4: Custos. Fator de correção por insumo e o fechamento mensal do CMV (insert-only).
CREATE TABLE IF NOT EXISTS item_custo (
    item_id BIGINT PRIMARY KEY REFERENCES item(id),
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    fator_correcao NUMERIC(6,3) NOT NULL DEFAULT 1 CHECK (fator_correcao >= 1 AND fator_correcao <= 10),
    atualizado_em TIMESTAMPTZ NOT NULL,
    atualizado_por BIGINT REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS fechamento_cmv (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    mes DATE NOT NULL CHECK (EXTRACT(DAY FROM mes) = 1),
    estoque_inicial NUMERIC(14,2) NOT NULL,
    compras NUMERIC(14,2) NOT NULL,
    estoque_final NUMERIC(14,2) NOT NULL,
    cmv_real NUMERIC(14,2) NOT NULL,
    cmv_teorico NUMERIC(14,2) NOT NULL,
    perdas NUMERIC(14,2) NOT NULL DEFAULT 0,
    consumo_interno NUMERIC(14,2) NOT NULL DEFAULT 0,
    vendas NUMERIC(14,2) NOT NULL DEFAULT 0,
    fechado_por BIGINT REFERENCES usuario(id),
    fechado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_cmv_real CHECK (cmv_real = estoque_inicial + compras - estoque_final),
    UNIQUE (loja_id, mes)
);
DO $$
BEGIN
    DROP TRIGGER IF EXISTS trg_fechamento_cmv_so_insercao ON fechamento_cmv;
    CREATE TRIGGER trg_fechamento_cmv_so_insercao BEFORE UPDATE OR DELETE ON fechamento_cmv FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
    DROP TRIGGER IF EXISTS trg_fechamento_cmv_so_insercao_trunc ON fechamento_cmv;
    CREATE TRIGGER trg_fechamento_cmv_so_insercao_trunc BEFORE TRUNCATE ON fechamento_cmv FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();
END $$;
