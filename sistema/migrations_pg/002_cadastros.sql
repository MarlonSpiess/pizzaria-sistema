-- Fatia 1B: cadastros. Categorias, produtos, preços com histórico, bordas e adicionais, clientes e entregadores.

CREATE TABLE IF NOT EXISTS categoria_pizza (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    preco_padrao_grande NUMERIC(10,2) CHECK (preco_padrao_grande >= 0),
    preco_padrao_broto NUMERIC(10,2) CHECK (preco_padrao_broto >= 0),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_nome ON categoria_pizza (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS produto (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('pizza','calzone','bebida','acompanhamento')),
    nome TEXT NOT NULL,
    categoria_id BIGINT REFERENCES categoria_pizza(id),
    ingredientes TEXT,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    -- Pizza tem categoria; os demais tipos não.
    CONSTRAINT ck_produto_categoria CHECK ((tipo = 'pizza') = (categoria_id IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_produto_nome ON produto (loja_id, tipo, lower(nome));

-- Histórico de preços: cada mudança é uma linha nova; vale a mais recente por (produto, tamanho).
CREATE TABLE IF NOT EXISTS preco_produto (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT NOT NULL REFERENCES produto(id),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto','unico')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    vigente_desde TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_preco_produto ON preco_produto (produto_id, tamanho, id DESC);

CREATE TABLE IF NOT EXISTS adicional (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('borda','adicional')),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_adicional_nome ON adicional (loja_id, tipo, lower(nome));

CREATE TABLE IF NOT EXISTS preco_adicional (
    id BIGSERIAL PRIMARY KEY,
    adicional_id BIGINT NOT NULL REFERENCES adicional(id),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    vigente_desde TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_preco_adicional ON preco_adicional (adicional_id, tamanho, id DESC);

CREATE TABLE IF NOT EXISTS cliente (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL CHECK (telefone ~ '^[0-9]{8,15}$'),
    endereco TEXT,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cliente_telefone ON cliente (loja_id, telefone);
CREATE INDEX IF NOT EXISTS idx_cliente_nome ON cliente (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS entregador (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    telefone TEXT CHECK (telefone IS NULL OR telefone ~ '^[0-9]{8,15}$'),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_entregador_nome ON entregador (loja_id, lower(nome));
