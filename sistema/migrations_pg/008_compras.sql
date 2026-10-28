-- Fatia 2B: Compras. Lista de necessidades, cotação por fornecedor, lista definitiva, pedido, recebimento com entrada da nota.

CREATE TABLE IF NOT EXISTS fornecedor (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    contato TEXT,
    telefone TEXT,
    prazo_dias INTEGER CHECK (prazo_dias IS NULL OR (prazo_dias >= 0 AND prazo_dias <= 365)),
    forma_pagamento TEXT CHECK (forma_pagamento IS NULL OR forma_pagamento IN ('dinheiro','pix','boleto','cartao','prazo','outro')),
    observacao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_fornecedor_nome ON fornecedor (loja_id, lower(nome));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_item_estoque_fornecedor') THEN
        ALTER TABLE item_estoque ADD CONSTRAINT fk_item_estoque_fornecedor FOREIGN KEY (fornecedor_habitual_id) REFERENCES fornecedor(id);
    END IF;
END $$;

-- Preço efetivamente pago, por unidade do item. Alimenta o mapa de cotação (últimos 3 preços) e Custos.
CREATE TABLE IF NOT EXISTS preco_compra (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    fornecedor_id BIGINT REFERENCES fornecedor(id),
    preco_unit NUMERIC(14,6) NOT NULL CHECK (preco_unit >= 0),
    quantidade NUMERIC(14,4) NOT NULL,
    data DATE NOT NULL,
    recebimento_id BIGINT,
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_preco_compra ON preco_compra (item_id, id DESC);

CREATE TABLE IF NOT EXISTS lista_compra (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    situacao TEXT NOT NULL DEFAULT 'rascunho' CHECK (situacao IN ('rascunho','cotando','definida','aprovada','cancelada')),
    observacao TEXT,
    total NUMERIC(12,2),
    criado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    definida_por BIGINT REFERENCES usuario(id),
    definida_em TIMESTAMPTZ,
    aprovada_por BIGINT REFERENCES usuario(id),
    aprovada_em TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS lista_compra_item (
    id BIGSERIAL PRIMARY KEY,
    lista_id BIGINT NOT NULL REFERENCES lista_compra(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    sugerida NUMERIC(14,4),
    origem TEXT NOT NULL CHECK (origem IN ('minimo','validade','producao','manual')),
    removido BOOLEAN NOT NULL DEFAULT false,
    motivo TEXT,
    UNIQUE (lista_id, item_id)
);

CREATE TABLE IF NOT EXISTS cotacao_resposta (
    id BIGSERIAL PRIMARY KEY,
    lista_item_id BIGINT NOT NULL REFERENCES lista_compra_item(id),
    fornecedor_id BIGINT NOT NULL REFERENCES fornecedor(id),
    preco_embalagem NUMERIC(14,4) NOT NULL CHECK (preco_embalagem > 0),
    fator NUMERIC(14,4) NOT NULL CHECK (fator > 0),
    preco_unit NUMERIC(14,6) NOT NULL CHECK (preco_unit > 0),
    prazo_dias INTEGER CHECK (prazo_dias IS NULL OR prazo_dias BETWEEN 0 AND 365),
    condicao TEXT,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cotacao ON cotacao_resposta (lista_item_id, fornecedor_id, id DESC);

CREATE TABLE IF NOT EXISTS lista_compra_escolha (
    id BIGSERIAL PRIMARY KEY,
    lista_id BIGINT NOT NULL REFERENCES lista_compra(id),
    lista_item_id BIGINT NOT NULL REFERENCES lista_compra_item(id),
    fornecedor_id BIGINT NOT NULL REFERENCES fornecedor(id),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    preco_unit NUMERIC(14,6) NOT NULL CHECK (preco_unit > 0),
    origem_preco TEXT NOT NULL CHECK (origem_preco IN ('cotacao','habitual','manual')),
    valor NUMERIC(12,2) NOT NULL CHECK (valor >= 0)
);

CREATE TABLE IF NOT EXISTS pedido_compra (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    lista_id BIGINT REFERENCES lista_compra(id),
    fornecedor_id BIGINT NOT NULL REFERENCES fornecedor(id),
    situacao TEXT NOT NULL DEFAULT 'emitido' CHECK (situacao IN ('emitido','parcial','recebido','cancelado')),
    prazo_dias INTEGER,
    forma_pagamento TEXT,
    previsao_entrega DATE,
    total NUMERIC(12,2) NOT NULL CHECK (total >= 0),
    observacao TEXT,
    criado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS pedido_compra_item (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedido_compra(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    preco_unit NUMERIC(14,6) NOT NULL CHECK (preco_unit > 0),
    UNIQUE (pedido_id, item_id)
);

CREATE TABLE IF NOT EXISTS recebimento (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    pedido_id BIGINT REFERENCES pedido_compra(id),
    fornecedor_id BIGINT NOT NULL REFERENCES fornecedor(id),
    numero_nota TEXT,
    data_nota DATE NOT NULL,
    conferente_id BIGINT REFERENCES usuario(id),
    frete NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (frete >= 0),
    desconto NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    total_nota NUMERIC(12,2) NOT NULL CHECK (total_nota >= 0),
    forma_pagamento TEXT,
    vencimento DATE,
    movimento_caixa_id BIGINT UNIQUE REFERENCES movimento_caixa(id),  -- compra urgente paga com dinheiro do caixa
    observacao TEXT,
    criado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_recebimento_nota ON recebimento (loja_id, fornecedor_id, numero_nota) WHERE numero_nota IS NOT NULL;
CREATE TABLE IF NOT EXISTS recebimento_item (
    id BIGSERIAL PRIMARY KEY,
    recebimento_id BIGINT NOT NULL REFERENCES recebimento(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    quantidade_pedida NUMERIC(14,4),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    preco_unit NUMERIC(14,6) NOT NULL CHECK (preco_unit >= 0),
    valor NUMERIC(12,2) NOT NULL CHECK (valor >= 0),
    lote_codigo TEXT,
    validade DATE,
    diferenca_motivo TEXT,
    movimento_estoque_id BIGINT REFERENCES movimento_estoque(id)
);
CREATE INDEX IF NOT EXISTS idx_recebimento_item ON recebimento_item (recebimento_id);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['preco_compra','cotacao_resposta','pedido_compra_item','recebimento','recebimento_item'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- A lista só avança (rascunho, cotando, definida, aprovada); cancela de qualquer ponto antes de aprovada. Aprovada e cancelada não mudam.
CREATE OR REPLACE FUNCTION lista_compra_regra() RETURNS trigger AS $$
DECLARE ordem TEXT[] := ARRAY['rascunho','cotando','definida','aprovada'];
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Lista de compras não pode ser apagada.'; END IF;
    IF OLD.situacao IN ('aprovada','cancelada') THEN RAISE EXCEPTION 'Lista % não muda.', OLD.situacao; END IF;
    IF (NEW.loja_id, NEW.criado_por, NEW.criado_em) IS DISTINCT FROM (OLD.loja_id, OLD.criado_por, OLD.criado_em) THEN
        RAISE EXCEPTION 'Lista de compras aceita alterar apenas situação, total, observação e aprovação.';
    END IF;
    IF NEW.situacao <> 'cancelada' AND array_position(ordem, NEW.situacao) < array_position(ordem, OLD.situacao) THEN
        RAISE EXCEPTION 'Lista de compras só avança.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_lista_compra_regra ON lista_compra;
CREATE TRIGGER trg_lista_compra_regra BEFORE UPDATE OR DELETE ON lista_compra FOR EACH ROW EXECUTE FUNCTION lista_compra_regra();

-- Itens e escolhas só mudam enquanto a lista está aberta (antes de definida para os itens; antes de aprovada para as escolhas).
CREATE OR REPLACE FUNCTION lista_compra_filhos() RETURNS trigger AS $$
DECLARE sit TEXT; lid BIGINT;
BEGIN
    IF TG_TABLE_NAME = 'lista_compra_item' THEN lid := COALESCE(OLD.lista_id, NEW.lista_id); ELSE lid := COALESCE(OLD.lista_id, NEW.lista_id); END IF;
    SELECT situacao INTO sit FROM lista_compra WHERE id = lid;
    IF TG_TABLE_NAME = 'lista_compra_item' AND sit NOT IN ('rascunho','cotando') THEN
        RAISE EXCEPTION 'Itens da lista só mudam em rascunho ou cotação.';
    END IF;
    IF TG_TABLE_NAME = 'lista_compra_escolha' AND sit IN ('aprovada','cancelada') THEN
        RAISE EXCEPTION 'Escolhas de lista % não mudam.', sit;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_lista_compra_item_regra ON lista_compra_item;
CREATE TRIGGER trg_lista_compra_item_regra BEFORE UPDATE OR DELETE ON lista_compra_item FOR EACH ROW EXECUTE FUNCTION lista_compra_filhos();
DROP TRIGGER IF EXISTS trg_lista_compra_escolha_regra ON lista_compra_escolha;
CREATE TRIGGER trg_lista_compra_escolha_regra BEFORE UPDATE OR DELETE ON lista_compra_escolha FOR EACH ROW EXECUTE FUNCTION lista_compra_filhos();

-- Pedido de compra: só a situação muda, e nunca depois de recebido ou cancelado.
CREATE OR REPLACE FUNCTION pedido_compra_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Pedido de compra não pode ser apagado.'; END IF;
    IF OLD.situacao IN ('recebido','cancelado') THEN RAISE EXCEPTION 'Pedido de compra % não muda.', OLD.situacao; END IF;
    IF (NEW.loja_id, NEW.lista_id, NEW.fornecedor_id, NEW.total, NEW.criado_em) IS DISTINCT FROM (OLD.loja_id, OLD.lista_id, OLD.fornecedor_id, OLD.total, OLD.criado_em) THEN
        RAISE EXCEPTION 'Pedido de compra aceita alterar apenas a situação.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_pedido_compra_regra ON pedido_compra;
CREATE TRIGGER trg_pedido_compra_regra BEFORE UPDATE OR DELETE ON pedido_compra FOR EACH ROW EXECUTE FUNCTION pedido_compra_regra();
