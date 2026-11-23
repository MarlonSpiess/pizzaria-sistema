-- Canais de venda (Anota Ai agora, iFood e outros depois). Só estrutura: sem integração real e sem guardar token no banco.
CREATE TABLE IF NOT EXISTS canal_venda (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    codigo TEXT NOT NULL CHECK (codigo ~ '^[a-z0-9_]{2,30}$'),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_canal_venda ON canal_venda (loja_id, codigo);

-- Fila de entrada: pedido que chegou do canal e ainda não virou pedido do sistema.
CREATE TABLE IF NOT EXISTS entrada_canal (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    canal_id BIGINT NOT NULL REFERENCES canal_venda(id),
    id_externo TEXT NOT NULL,
    conteudo JSONB NOT NULL DEFAULT '{}'::jsonb,
    situacao TEXT NOT NULL DEFAULT 'pendente' CHECK (situacao IN ('pendente','recusada')),
    motivo TEXT,
    recebido_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_entrada_canal ON entrada_canal (canal_id, id_externo);

-- ID Externo do produto em cada canal (o cardápio é único e exportado).
CREATE TABLE IF NOT EXISTS mapa_produto_canal (
    id BIGSERIAL PRIMARY KEY,
    canal_id BIGINT NOT NULL REFERENCES canal_venda(id),
    produto_id BIGINT NOT NULL REFERENCES produto(id),
    id_externo TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_mapa_produto ON mapa_produto_canal (canal_id, produto_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_mapa_externo ON mapa_produto_canal (canal_id, id_externo);
