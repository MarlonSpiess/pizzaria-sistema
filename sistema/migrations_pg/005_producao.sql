-- Fatia 1D: produção. A unidade de trabalho é a pizza (ou calzone). Eventos, retrocessos, perdas e etiquetas são só de inserção.

CREATE TABLE IF NOT EXISTS motivo_retrocesso (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    avisa_estoque BOOLEAN NOT NULL DEFAULT false,  -- falta de insumo avisa Estoques (fatia futura)
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_motivo_retrocesso ON motivo_retrocesso (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS motivo_perda (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_motivo_perda ON motivo_perda (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS pizza_producao (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    item_id BIGINT REFERENCES item_pedido(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('pizza','calzone')),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto','unico')),
    sabores TEXT NOT NULL,
    adicionais TEXT,
    observacoes TEXT,
    situacao TEXT NOT NULL DEFAULT 'na lista'
        CHECK (situacao IN ('na lista','em montagem','no forno','saiu do forno','acabada','perdida','cancelada')),
    ordem NUMERIC(24,6) NOT NULL,
    responsavel_id BIGINT REFERENCES usuario(id),
    original_id BIGINT REFERENCES pizza_producao(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pizza_fila ON pizza_producao (loja_id, situacao, ordem);
CREATE INDEX IF NOT EXISTS idx_pizza_pedido ON pizza_producao (pedido_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pizza_refacao ON pizza_producao (original_id) WHERE original_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS evento_producao (
    id BIGSERIAL PRIMARY KEY,
    pizza_id BIGINT NOT NULL REFERENCES pizza_producao(id),
    situacao TEXT NOT NULL,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evento_producao ON evento_producao (pizza_id, id);

CREATE TABLE IF NOT EXISTS retrocesso (
    id BIGSERIAL PRIMARY KEY,
    pizza_id BIGINT NOT NULL REFERENCES pizza_producao(id),
    motivo_id BIGINT NOT NULL REFERENCES motivo_retrocesso(id),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS lote_massa (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto')),
    quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 1000),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

-- Contagem de massa aberta feita pelo operador. O saldo é a última contagem mais os lotes, menos o que foi usado e perdido depois dela.
CREATE TABLE IF NOT EXISTS contagem_massa (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tamanho TEXT NOT NULL CHECK (tamanho IN ('grande','broto')),
    quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 0 AND 1000),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS perda (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('massa','pizza')),
    tamanho TEXT CHECK (tamanho IN ('grande','broto','unico')),
    quantidade INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 1000),
    pizza_id BIGINT REFERENCES pizza_producao(id),
    motivo_id BIGINT NOT NULL REFERENCES motivo_perda(id),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS etiqueta_impressa (
    id BIGSERIAL PRIMARY KEY,
    pizza_id BIGINT NOT NULL REFERENCES pizza_producao(id),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['evento_producao','retrocesso','lote_massa','contagem_massa','perda','etiqueta_impressa'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- Da pizza só a situação, a ordem na fila e o responsável mudam; a pizza nunca volta de perdida ou cancelada.
CREATE OR REPLACE FUNCTION pizza_so_andamento() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Pizza não pode ser apagada.';
    END IF;
    IF (NEW.loja_id, NEW.pedido_id, NEW.item_id, NEW.tipo, NEW.tamanho, NEW.sabores, NEW.adicionais, NEW.observacoes, NEW.original_id, NEW.criado_em)
       IS DISTINCT FROM
       (OLD.loja_id, OLD.pedido_id, OLD.item_id, OLD.tipo, OLD.tamanho, OLD.sabores, OLD.adicionais, OLD.observacoes, OLD.original_id, OLD.criado_em) THEN
        RAISE EXCEPTION 'Pizza aceita alterar apenas situação, ordem e responsável.';
    END IF;
    IF OLD.situacao IN ('perdida','cancelada','acabada') AND NEW.situacao IS DISTINCT FROM OLD.situacao
       AND NOT (OLD.situacao = 'acabada' AND NEW.situacao = 'perdida') THEN
        RAISE EXCEPTION 'Pizza % é final.', OLD.situacao;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_pizza_so_andamento ON pizza_producao;
CREATE TRIGGER trg_pizza_so_andamento BEFORE UPDATE OR DELETE ON pizza_producao
    FOR EACH ROW EXECUTE FUNCTION pizza_so_andamento();
