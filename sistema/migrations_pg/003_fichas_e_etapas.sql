-- Fatia 1B2: itens, fichas técnicas (versões só de inserção) e etapas de produção. Sem baixa de estoque nem custo.

CREATE TABLE IF NOT EXISTS item (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    classe TEXT NOT NULL CHECK (classe IN ('insumo','preparo','embalagem','revenda','consumo')),
    unidade TEXT NOT NULL CHECK (unidade IN ('g','kg','ml','l','un','fatia')),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_item_nome ON item (loja_id, lower(nome));

-- Uma versão por salvamento; vale a mais recente do dono. Dono: produto (meia Grande ou Broto, ou unidade do calzone,
-- bebida, acompanhamento), adicional por tamanho, preparo (item) ou base do tamanho (massa aberta, caixa: uma por pizza).
CREATE TABLE IF NOT EXISTS ficha_versao (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    produto_id BIGINT REFERENCES produto(id),
    adicional_id BIGINT REFERENCES adicional(id),
    item_id BIGINT REFERENCES item(id),
    tamanho TEXT CHECK (tamanho IN ('grande','broto')),
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_ficha_dono CHECK (
        (produto_id IS NOT NULL AND adicional_id IS NULL AND item_id IS NULL AND tamanho IS NULL) OR
        (adicional_id IS NOT NULL AND produto_id IS NULL AND item_id IS NULL AND tamanho IS NOT NULL) OR
        (item_id IS NOT NULL AND produto_id IS NULL AND adicional_id IS NULL AND tamanho IS NULL) OR
        (tamanho IS NOT NULL AND produto_id IS NULL AND adicional_id IS NULL AND item_id IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_ficha_produto ON ficha_versao (produto_id, id DESC) WHERE produto_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ficha_adicional ON ficha_versao (adicional_id, tamanho, id DESC) WHERE adicional_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ficha_item ON ficha_versao (item_id, id DESC) WHERE item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ficha_base ON ficha_versao (loja_id, tamanho, id DESC) WHERE tamanho IS NOT NULL AND adicional_id IS NULL;

CREATE TABLE IF NOT EXISTS ficha_linha (
    id BIGSERIAL PRIMARY KEY,
    versao_id BIGINT NOT NULL REFERENCES ficha_versao(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    perda_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (perda_pct >= 0 AND perda_pct <= 100),
    -- Quando o ingrediente entra: na montagem (antes do forno) ou depois do forno (batata palha, cobertura doce).
    fase TEXT NOT NULL DEFAULT 'montagem' CHECK (fase IN ('montagem','pos_forno')),
    UNIQUE (versao_id, item_id)
);

DROP TRIGGER IF EXISTS trg_ficha_versao_so_insercao ON ficha_versao;
CREATE TRIGGER trg_ficha_versao_so_insercao BEFORE UPDATE OR DELETE ON ficha_versao
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
DROP TRIGGER IF EXISTS trg_ficha_linha_so_insercao ON ficha_linha;
CREATE TRIGGER trg_ficha_linha_so_insercao BEFORE UPDATE OR DELETE ON ficha_linha
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();

DROP TRIGGER IF EXISTS trg_ficha_versao_so_insercao_trunc ON ficha_versao;
CREATE TRIGGER trg_ficha_versao_so_insercao_trunc BEFORE TRUNCATE ON ficha_versao
    FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();
DROP TRIGGER IF EXISTS trg_ficha_linha_so_insercao_trunc ON ficha_linha;
CREATE TRIGGER trg_ficha_linha_so_insercao_trunc BEFORE TRUNCATE ON ficha_linha
    FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();

-- Etapas de produção: cadastro, modelo por tipo de produto e exceção por produto.
CREATE TABLE IF NOT EXISTS etapa (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    funcao TEXT NOT NULL CHECK (funcao IN ('massa','pizzaiolo','acabamento','automatica')),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_etapa_nome ON etapa (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS etapa_modelo (
    tipo TEXT NOT NULL CHECK (tipo IN ('pizza','calzone','bebida','acompanhamento')),
    etapa_id BIGINT NOT NULL REFERENCES etapa(id),
    ordem INTEGER NOT NULL CHECK (ordem > 0),
    tempo_min NUMERIC(6,2) CHECK (tempo_min >= 0),
    PRIMARY KEY (tipo, etapa_id),
    UNIQUE (tipo, ordem)
);

CREATE TABLE IF NOT EXISTS produto_etapa (
    produto_id BIGINT NOT NULL REFERENCES produto(id),
    etapa_id BIGINT NOT NULL REFERENCES etapa(id),
    ordem INTEGER NOT NULL CHECK (ordem > 0),
    tempo_min NUMERIC(6,2) CHECK (tempo_min >= 0),
    PRIMARY KEY (produto_id, etapa_id),
    UNIQUE (produto_id, ordem)
);
