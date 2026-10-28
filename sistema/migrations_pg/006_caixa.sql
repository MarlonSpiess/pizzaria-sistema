-- Fatia 1E: fechamento de caixa. Um caixa por dia e uma gaveta por loja. Movimentos, contagens, acertos e estornos são só de inserção.

CREATE TABLE IF NOT EXISTS maquininha (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_maquininha ON maquininha (loja_id, lower(nome));

-- Taxa e prazo de recebimento por forma de pagamento, e por maquininha quando houver (alimenta Contas a Receber).
CREATE TABLE IF NOT EXISTS regra_recebimento (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    forma TEXT NOT NULL CHECK (forma IN ('dinheiro','pix','credito','debito')),
    maquininha_id BIGINT REFERENCES maquininha(id),
    taxa_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (taxa_pct >= 0 AND taxa_pct <= 100),
    prazo_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_dias >= 0 AND prazo_dias <= 365),
    vigente_desde TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_regra_recebimento ON regra_recebimento (loja_id, forma, maquininha_id, id DESC);

CREATE TABLE IF NOT EXISTS motivo_movimento (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('sangria','suprimento')),
    vira_despesa BOOLEAN NOT NULL DEFAULT false,  -- sangria de pequena despesa segue para Contas a Pagar
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_motivo_movimento ON motivo_movimento (loja_id, tipo, lower(nome));

CREATE TABLE IF NOT EXISTS caixa_dia (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    situacao TEXT NOT NULL DEFAULT 'aberto' CHECK (situacao IN ('aberto','contado','fechado')),
    fundo_troco NUMERIC(10,2) NOT NULL CHECK (fundo_troco >= 0),
    aberto_por BIGINT REFERENCES usuario(id),
    aberto_em TIMESTAMPTZ NOT NULL,
    contado_por BIGINT REFERENCES usuario(id),
    contado_em TIMESTAMPTZ,
    fechado_por BIGINT REFERENCES usuario(id),
    fechado_em TIMESTAMPTZ,
    aprovado_por BIGINT REFERENCES usuario(id),
    justificativa TEXT,
    UNIQUE (loja_id, data)
);

CREATE TABLE IF NOT EXISTS movimento_caixa (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('sangria','suprimento')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    motivo_id BIGINT NOT NULL REFERENCES motivo_movimento(id),
    motivo_nome TEXT NOT NULL,  -- cópia do momento: renomear o motivo depois não reescreve o passado
    vira_despesa BOOLEAN NOT NULL DEFAULT false,
    observacao TEXT,
    comprovante TEXT,
    usuario_id BIGINT REFERENCES usuario(id),
    autorizado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_movimento_caixa ON movimento_caixa (loja_id, data);

-- Estorno de pedido cancelado depois de pago: uma linha por forma de pagamento, na data do cancelamento.
CREATE TABLE IF NOT EXISTS estorno (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    pedido_id BIGINT NOT NULL REFERENCES pedido(id),
    forma TEXT NOT NULL CHECK (forma IN ('dinheiro','pix','credito','debito')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    motivo TEXT NOT NULL,
    usuario_id BIGINT REFERENCES usuario(id),
    autorizado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_estorno ON estorno (loja_id, data);

-- Contagem cega: o valor contado é gravado junto com o esperado e a diferença no mesmo instante, depois de informado.
CREATE TABLE IF NOT EXISTS contagem_caixa (
    id BIGSERIAL PRIMARY KEY,
    caixa_id BIGINT NOT NULL REFERENCES caixa_dia(id),
    forma TEXT NOT NULL CHECK (forma IN ('dinheiro','pix','credito','debito')),
    contado NUMERIC(14,2) NOT NULL CHECK (contado >= 0),
    esperado NUMERIC(14,2) NOT NULL,
    diferenca NUMERIC(14,2) NOT NULL CHECK (diferenca = contado - esperado),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    UNIQUE (caixa_id, forma)
);

-- Entrega atribuída a um entregador (terceiro). O acerto do dinheiro acontece no fim do turno.
CREATE TABLE IF NOT EXISTS entrega (
    pedido_id BIGINT PRIMARY KEY REFERENCES pedido(id),
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    entregador_id BIGINT NOT NULL REFERENCES entregador(id),
    valor_entrega NUMERIC(10,2) NOT NULL CHECK (valor_entrega >= 0),
    atribuido_por BIGINT REFERENCES usuario(id),
    atribuido_em TIMESTAMPTZ NOT NULL,
    acerto_id BIGINT
);
CREATE INDEX IF NOT EXISTS idx_entrega_data ON entrega (loja_id, data, entregador_id);

CREATE TABLE IF NOT EXISTS acerto_entregador (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    data DATE NOT NULL,
    entregador_id BIGINT NOT NULL REFERENCES entregador(id),
    pedidos INTEGER NOT NULL CHECK (pedidos > 0),
    dinheiro_recebido NUMERIC(10,2) NOT NULL CHECK (dinheiro_recebido >= 0),  -- líquido do troco, o que volta à gaveta
    valor_entregas NUMERIC(10,2) NOT NULL CHECK (valor_entregas >= 0),
    diaria NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (diaria >= 0),
    total_devido NUMERIC(10,2) NOT NULL CHECK (total_devido >= 0),
    saldo_gaveta NUMERIC(10,2) NOT NULL,  -- dinheiro recebido menos o devido ao entregador: o que entra (+) ou sai (-) da gaveta
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_acerto_total CHECK (total_devido = valor_entregas + diaria AND saldo_gaveta = dinheiro_recebido - total_devido)
);
CREATE INDEX IF NOT EXISTS idx_acerto ON acerto_entregador (loja_id, data, entregador_id);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['movimento_caixa','estorno','contagem_caixa','acerto_entregador','regra_recebimento'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- Da entrega só o acerto pode ser preenchido, uma vez. Do caixa só a situação e os dados de fechamento avançam; nunca volta.
CREATE OR REPLACE FUNCTION entrega_so_acerto() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Entrega não pode ser apagada.'; END IF;
    IF (NEW.pedido_id, NEW.loja_id, NEW.data, NEW.entregador_id, NEW.valor_entrega, NEW.atribuido_por, NEW.atribuido_em)
       IS DISTINCT FROM (OLD.pedido_id, OLD.loja_id, OLD.data, OLD.entregador_id, OLD.valor_entrega, OLD.atribuido_por, OLD.atribuido_em) THEN
        RAISE EXCEPTION 'Entrega aceita alterar apenas o acerto.';
    END IF;
    IF OLD.acerto_id IS NOT NULL AND NEW.acerto_id IS DISTINCT FROM OLD.acerto_id THEN
        RAISE EXCEPTION 'Entrega já foi acertada.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_entrega_so_acerto ON entrega;
CREATE TRIGGER trg_entrega_so_acerto BEFORE UPDATE OR DELETE ON entrega FOR EACH ROW EXECUTE FUNCTION entrega_so_acerto();

CREATE OR REPLACE FUNCTION caixa_so_avanca() RETURNS trigger AS $$
DECLARE ordem TEXT[] := ARRAY['aberto','contado','fechado'];
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Caixa não pode ser apagado.'; END IF;
    IF (NEW.loja_id, NEW.data, NEW.fundo_troco, NEW.aberto_por, NEW.aberto_em) IS DISTINCT FROM
       (OLD.loja_id, OLD.data, OLD.fundo_troco, OLD.aberto_por, OLD.aberto_em) THEN
        RAISE EXCEPTION 'Caixa aceita alterar apenas contagem e fechamento.';
    END IF;
    IF NEW.situacao IS DISTINCT FROM OLD.situacao
       AND array_position(ordem, NEW.situacao) IS DISTINCT FROM array_position(ordem, OLD.situacao) + 1 THEN
        RAISE EXCEPTION 'Caixa só avança: aberto, contado, fechado.';
    END IF;
    IF OLD.situacao = 'fechado' THEN RAISE EXCEPTION 'Caixa fechado não muda.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_caixa_so_avanca ON caixa_dia;
CREATE TRIGGER trg_caixa_so_avanca BEFORE UPDATE OR DELETE ON caixa_dia FOR EACH ROW EXECUTE FUNCTION caixa_so_avanca();
