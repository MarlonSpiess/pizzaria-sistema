-- Pontos de controle por pedido (melhoria M4, visão de produção): registram só o que o sistema ainda não sabia.
-- leitura_de_volta: o atendente leu o pedido de volta ao cliente. conferencia_final: itens e bebidas conferidos antes do despacho.
-- causa_atraso: a gerência anota a causa de um pedido que passou do tempo prometido. Só inserção; corrigir = novo registro.

CREATE TABLE IF NOT EXISTS pedido_controle (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    ponto TEXT NOT NULL CHECK (ponto IN ('leitura_de_volta','conferencia_final','causa_atraso')),
    ok BOOLEAN NOT NULL DEFAULT true,
    texto TEXT,
    feito_por BIGINT REFERENCES usuario(id),
    feito_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_pedido_controle_causa CHECK (ponto <> 'causa_atraso' OR (texto IS NOT NULL AND length(btrim(texto)) > 0))
);
CREATE INDEX IF NOT EXISTS idx_pedido_controle ON pedido_controle (pedido_id, ponto, id DESC);

DROP TRIGGER IF EXISTS trg_pedido_controle_so_insercao ON pedido_controle;
CREATE TRIGGER trg_pedido_controle_so_insercao BEFORE UPDATE OR DELETE ON pedido_controle
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
DROP TRIGGER IF EXISTS trg_pedido_controle_so_insercao_trunc ON pedido_controle;
CREATE TRIGGER trg_pedido_controle_so_insercao_trunc BEFORE TRUNCATE ON pedido_controle
    FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();
