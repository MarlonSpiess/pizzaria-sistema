-- Fatia 1C: vendas de balcão. Pedido, itens, adicionais, pagamentos, ajustes, cancelamento e eventos.
-- Itens, pagamentos, ajustes, cancelamentos e eventos são só de inserção; o pedido muda apenas de situação.

CREATE TABLE IF NOT EXISTS contador_dia (
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    ultimo INTEGER NOT NULL DEFAULT 0 CHECK (ultimo >= 0),
    PRIMARY KEY (loja_id, data)
);

CREATE TABLE IF NOT EXISTS pedido (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    id_dia INTEGER NOT NULL CHECK (id_dia > 0),
    canal TEXT NOT NULL DEFAULT 'balcao' CHECK (canal IN ('balcao','anotaai')),
    id_canal TEXT,
    cliente_id BIGINT REFERENCES cliente(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('retirada','entrega')),
    situacao TEXT NOT NULL DEFAULT 'recebido'
        CHECK (situacao IN ('recebido','em producao','acabado','despachado ou retirado','cancelado')),
    urgente BOOLEAN NOT NULL DEFAULT false,
    subtotal NUMERIC(10,2) NOT NULL CHECK (subtotal >= 0),
    desconto NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    acrescimo NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (acrescimo >= 0),
    taxa_entrega NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (taxa_entrega >= 0),
    taxa_motivo TEXT,
    total NUMERIC(10,2) NOT NULL CHECK (total >= 0),
    observacoes TEXT,
    entrega_calculada TIMESTAMPTZ,
    entrega_real TIMESTAMPTZ,
    numero_cf TEXT,
    chave TEXT,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_pedido_entrega_cliente CHECK (tipo = 'retirada' OR cliente_id IS NOT NULL),
    CONSTRAINT ck_pedido_total CHECK (total = subtotal - desconto + acrescimo + taxa_entrega),
    CONSTRAINT ck_pedido_desc_acres CHECK (desconto = 0 OR acrescimo = 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_id_dia ON pedido (loja_id, data, id_dia);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_canal ON pedido (loja_id, canal, id_canal) WHERE id_canal IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_pedido_chave ON pedido (loja_id, chave) WHERE chave IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pedido_data ON pedido (loja_id, data, situacao);

CREATE TABLE IF NOT EXISTS item_pedido (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    seq INTEGER NOT NULL CHECK (seq > 0),
    tipo TEXT NOT NULL CHECK (tipo IN ('pizza','calzone','bebida','acompanhamento')),
    produto_id BIGINT NOT NULL REFERENCES produto(id),
    sabor2_id BIGINT REFERENCES produto(id),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto','unico')),
    descricao TEXT NOT NULL,
    preco_unit NUMERIC(10,2) NOT NULL CHECK (preco_unit >= 0),
    quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 99),
    observacoes TEXT,
    UNIQUE (pedido_id, seq),
    CONSTRAINT ck_item_sabor2 CHECK (sabor2_id IS NULL OR (tipo = 'pizza' AND tamanho = 'grande'))
);

CREATE TABLE IF NOT EXISTS item_adicional (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES item_pedido(id),
    adicional_id BIGINT NOT NULL REFERENCES adicional(id),
    nome TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL CHECK (valor >= 0)
);

CREATE TABLE IF NOT EXISTS pagamento (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    forma TEXT NOT NULL CHECK (forma IN ('dinheiro','pix','credito','debito')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    troco NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (troco >= 0),
    maquininha TEXT,
    criado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_pagamento_troco CHECK (troco = 0 OR forma = 'dinheiro')
);
CREATE INDEX IF NOT EXISTS idx_pagamento_pedido ON pagamento (pedido_id);

CREATE TABLE IF NOT EXISTS ajuste_pedido (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('desconto','acrescimo')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    motivo TEXT NOT NULL CHECK (length(btrim(motivo)) > 0),
    usuario_id BIGINT REFERENCES usuario(id),
    autorizado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS cancelamento (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL UNIQUE REFERENCES pedido(id),
    motivo TEXT NOT NULL CHECK (length(btrim(motivo)) > 0),
    usuario_id BIGINT REFERENCES usuario(id),
    autorizado_por BIGINT REFERENCES usuario(id),
    situacao_anterior TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS evento_pedido (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    situacao TEXT NOT NULL,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evento_pedido ON evento_pedido (pedido_id, id);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['item_pedido','item_adicional','pagamento','ajuste_pedido','cancelamento','evento_pedido'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- Do pedido, só situação, urgência, entrega real e número do CF mudam; o resto é fixo. Cancelado é final e a situação anda um passo.
CREATE OR REPLACE FUNCTION pedido_so_situacao() RETURNS trigger AS $$
DECLARE ordem TEXT[] := ARRAY['recebido','em producao','acabado','despachado ou retirado'];
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Pedido não pode ser apagado.';
    END IF;
    IF (NEW.loja_id, NEW.data, NEW.id_dia, NEW.canal, NEW.id_canal, NEW.cliente_id, NEW.tipo, NEW.subtotal, NEW.desconto, NEW.acrescimo,
        NEW.taxa_entrega, NEW.taxa_motivo, NEW.total, NEW.observacoes, NEW.chave, NEW.criado_em, NEW.criado_por) IS DISTINCT FROM
       (OLD.loja_id, OLD.data, OLD.id_dia, OLD.canal, OLD.id_canal, OLD.cliente_id, OLD.tipo, OLD.subtotal, OLD.desconto, OLD.acrescimo,
        OLD.taxa_entrega, OLD.taxa_motivo, OLD.total, OLD.observacoes, OLD.chave, OLD.criado_em, OLD.criado_por) THEN
        RAISE EXCEPTION 'Pedido aceita alterar apenas situação, urgência, entrega e número do CF.';
    END IF;
    IF NEW.situacao IS DISTINCT FROM OLD.situacao THEN
        IF OLD.situacao = 'cancelado' OR OLD.situacao = 'despachado ou retirado' THEN
            RAISE EXCEPTION 'Pedido % é final.', OLD.situacao;
        ELSIF NEW.situacao = 'cancelado' THEN
            NULL;
        ELSIF array_position(ordem, NEW.situacao) IS DISTINCT FROM array_position(ordem, OLD.situacao) + 1 THEN
            RAISE EXCEPTION 'Situação só avança um passo por vez.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_pedido_so_situacao ON pedido;
CREATE TRIGGER trg_pedido_so_situacao BEFORE UPDATE OR DELETE ON pedido
    FOR EACH ROW EXECUTE FUNCTION pedido_so_situacao();
