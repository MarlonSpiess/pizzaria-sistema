-- Avisos de status ao canal (pronto, saiu para entrega, disponível para retirada). Fila com tentativas: se a internet cair, o aviso espera e é reenviado.
CREATE TABLE IF NOT EXISTS aviso_canal (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    canal_id BIGINT NOT NULL REFERENCES canal_venda(id),
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    evento TEXT NOT NULL CHECK (evento IN ('pronto','saiu_entrega','disponivel_retirada')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    tentativas INTEGER NOT NULL DEFAULT 0,
    proxima_tentativa TIMESTAMPTZ NOT NULL DEFAULT now(),
    enviado_em TIMESTAMPTZ,
    erro TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_aviso_canal ON aviso_canal (pedido_id, evento);
CREATE INDEX IF NOT EXISTS idx_aviso_pendente ON aviso_canal (proxima_tentativa) WHERE enviado_em IS NULL;
