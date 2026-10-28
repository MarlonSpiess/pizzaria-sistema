-- Fatia 2A: Estoques. Saldo nunca é digitado: vem da soma dos movimentos (só inserção). Custo médio móvel em histórico de inserção.

CREATE TABLE IF NOT EXISTS local_estoque (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_local_estoque ON local_estoque (loja_id, lower(nome));

-- Parâmetros de estoque de cada item. Sem linha, o item vale os padrões do serviço (lote nos insumos e preparos).
CREATE TABLE IF NOT EXISTS item_estoque (
    item_id BIGINT PRIMARY KEY REFERENCES item(id),
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    unidade_compra TEXT,
    fator_compra NUMERIC(14,4) NOT NULL DEFAULT 1 CHECK (fator_compra > 0),  -- quantas unidades do item cabem em uma unidade de compra
    local_padrao_id BIGINT REFERENCES local_estoque(id),
    estoque_minimo NUMERIC(14,4) CHECK (estoque_minimo IS NULL OR estoque_minimo >= 0),
    ponto_pedido NUMERIC(14,4) CHECK (ponto_pedido IS NULL OR ponto_pedido >= 0),
    estoque_maximo NUMERIC(14,4) CHECK (estoque_maximo IS NULL OR estoque_maximo >= 0),
    controla_lote BOOLEAN NOT NULL DEFAULT true,
    critico BOOLEAN NOT NULL DEFAULT false,  -- contagem diária
    fornecedor_habitual_id BIGINT,
    atualizado_em TIMESTAMPTZ NOT NULL,
    atualizado_por BIGINT REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS lote_estoque (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    codigo TEXT NOT NULL,
    validade DATE,
    entrada_em TIMESTAMPTZ NOT NULL,
    custo_unit NUMERIC(14,6),
    origem TEXT NOT NULL,
    UNIQUE (item_id, codigo)
);

CREATE TABLE IF NOT EXISTS movimento_estoque (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    item_id BIGINT NOT NULL REFERENCES item(id),
    local_id BIGINT NOT NULL REFERENCES local_estoque(id),
    lote_id BIGINT REFERENCES lote_estoque(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada_compra','entrada_inicial','saida_venda','saida_producao','perda','consumo_interno',
                                       'ajuste_inventario','transferencia_saida','transferencia_entrada','devolucao_fornecedor')),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade <> 0),  -- com sinal: entrada positiva, saída negativa
    custo_unit NUMERIC(14,6),
    motivo TEXT,
    origem_tipo TEXT,
    origem_id BIGINT,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mov_estoque_item ON movimento_estoque (item_id, local_id, lote_id);
CREATE INDEX IF NOT EXISTS idx_mov_estoque_data ON movimento_estoque (loja_id, data, tipo);

CREATE TABLE IF NOT EXISTS custo_item (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    custo_medio NUMERIC(14,6) NOT NULL CHECK (custo_medio >= 0),
    saldo_apos NUMERIC(14,4) NOT NULL,
    movimento_id BIGINT REFERENCES movimento_estoque(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_custo_item ON custo_item (item_id, id DESC);

-- Inventário: contagem cega (o esperado só aparece em 'conferido'), depois o ajuste com motivo.
CREATE TABLE IF NOT EXISTS inventario (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('diario','mensal','avulso')),
    situacao TEXT NOT NULL DEFAULT 'aberto' CHECK (situacao IN ('aberto','conferido','fechado')),
    observacao TEXT,
    aberto_por BIGINT REFERENCES usuario(id),
    aberto_em TIMESTAMPTZ NOT NULL,
    conferido_em TIMESTAMPTZ,
    fechado_por BIGINT REFERENCES usuario(id),
    fechado_em TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS inventario_linha (
    id BIGSERIAL PRIMARY KEY,
    inventario_id BIGINT NOT NULL REFERENCES inventario(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    contado NUMERIC(14,4) CHECK (contado IS NULL OR contado >= 0),
    esperado NUMERIC(14,4),
    diferenca NUMERIC(14,4),
    motivo TEXT,
    UNIQUE (inventario_id, item_id)
);

-- Sinal de que o consumo de uma origem (pizza acabada, pedido) já foi baixado: a baixa nunca roda duas vezes.
CREATE TABLE IF NOT EXISTS baixa_origem (
    origem_tipo TEXT NOT NULL,
    origem_id BIGINT NOT NULL,
    fase TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (origem_tipo, origem_id, fase)
);

-- O que a baixa automática não conseguiu fazer (produto sem ficha, erro) fica à vista para quem cuida do estoque.
CREATE TABLE IF NOT EXISTS pendencia_estoque (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('sem_ficha','erro_baixa')),
    produto_id BIGINT REFERENCES produto(id),
    origem_tipo TEXT,
    origem_id BIGINT,
    detalhe TEXT,
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pendencia_estoque ON pendencia_estoque (loja_id, tipo, produto_id);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['movimento_estoque','custo_item','baixa_origem','pendencia_estoque'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- Lote: nada muda depois de criado, exceto a validade corrigida enquanto o lote não teve saída (regra no serviço); aqui só impede apagar.
CREATE OR REPLACE FUNCTION lote_nao_apaga() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Lote não pode ser apagado.'; END IF;
    IF (NEW.loja_id, NEW.item_id, NEW.codigo, NEW.entrada_em, NEW.custo_unit, NEW.origem) IS DISTINCT FROM
       (OLD.loja_id, OLD.item_id, OLD.codigo, OLD.entrada_em, OLD.custo_unit, OLD.origem) THEN
        RAISE EXCEPTION 'Lote aceita alterar apenas a validade.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_lote_nao_apaga ON lote_estoque;
CREATE TRIGGER trg_lote_nao_apaga BEFORE UPDATE OR DELETE ON lote_estoque FOR EACH ROW EXECUTE FUNCTION lote_nao_apaga();

-- Inventário só avança (aberto, conferido, fechado). A linha só muda enquanto o inventário permite: contado em aberto; esperado e motivo ao conferir e fechar.
CREATE OR REPLACE FUNCTION inventario_so_avanca() RETURNS trigger AS $$
DECLARE ordem TEXT[] := ARRAY['aberto','conferido','fechado'];
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Inventário não pode ser apagado.'; END IF;
    IF (NEW.loja_id, NEW.tipo, NEW.aberto_por, NEW.aberto_em) IS DISTINCT FROM (OLD.loja_id, OLD.tipo, OLD.aberto_por, OLD.aberto_em) THEN
        RAISE EXCEPTION 'Inventário aceita alterar apenas a situação.';
    END IF;
    IF OLD.situacao = 'fechado' THEN RAISE EXCEPTION 'Inventário fechado não muda.'; END IF;
    IF NEW.situacao IS DISTINCT FROM OLD.situacao
       AND array_position(ordem, NEW.situacao) IS DISTINCT FROM array_position(ordem, OLD.situacao) + 1 THEN
        RAISE EXCEPTION 'Inventário só avança: aberto, conferido, fechado.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_inventario_so_avanca ON inventario;
CREATE TRIGGER trg_inventario_so_avanca BEFORE UPDATE OR DELETE ON inventario FOR EACH ROW EXECUTE FUNCTION inventario_so_avanca();

CREATE OR REPLACE FUNCTION inventario_linha_regra() RETURNS trigger AS $$
DECLARE sit TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Linha de inventário não pode ser apagada.'; END IF;
    SELECT situacao INTO sit FROM inventario WHERE id = OLD.inventario_id;
    IF (NEW.inventario_id, NEW.item_id) IS DISTINCT FROM (OLD.inventario_id, OLD.item_id) THEN
        RAISE EXCEPTION 'Linha de inventário não troca de item.';
    END IF;
    IF sit = 'fechado' THEN RAISE EXCEPTION 'Inventário fechado não muda.'; END IF;
    IF sit <> 'aberto' AND NEW.contado IS DISTINCT FROM OLD.contado THEN
        RAISE EXCEPTION 'Depois da conferência a contagem não muda.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_inventario_linha_regra ON inventario_linha;
CREATE TRIGGER trg_inventario_linha_regra BEFORE UPDATE OR DELETE ON inventario_linha FOR EACH ROW EXECUTE FUNCTION inventario_linha_regra();
