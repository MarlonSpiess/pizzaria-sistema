-- Fatia 3: Contas a Pagar e Receber, contas bancárias, conciliação e fluxo de caixa.
-- Título e baixa: o valor do título nunca muda; o que foi pago é a soma das baixas (só inserção).

CREATE TABLE IF NOT EXISTS conta_bancaria (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    banco TEXT,
    agencia TEXT,
    numero TEXT,
    tipo TEXT NOT NULL DEFAULT 'corrente' CHECK (tipo IN ('corrente','poupanca','caixa_fisico','outro')),
    saldo_inicial NUMERIC(14,2) NOT NULL DEFAULT 0,
    saldo_inicial_data DATE NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_conta_bancaria ON conta_bancaria (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS tipo_despesa (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    natureza TEXT NOT NULL CHECK (natureza IN ('fixa','variavel','pessoal','tributo','financiamento','retirada','outra')),
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_despesa ON tipo_despesa (loja_id, lower(nome));

-- Repasse por canal (Anota Aí, iFood e outros): prazo e taxa vão para os títulos a receber.
CREATE TABLE IF NOT EXISTS canal_repasse (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    canal TEXT NOT NULL,
    taxa_pct NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (taxa_pct >= 0 AND taxa_pct <= 100),
    prazo_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_dias BETWEEN 0 AND 365),
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_canal_repasse ON canal_repasse (loja_id, lower(canal));

CREATE TABLE IF NOT EXISTS recorrente (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    descricao TEXT NOT NULL,
    tipo_despesa_id BIGINT NOT NULL REFERENCES tipo_despesa(id),
    fornecedor_id BIGINT REFERENCES fornecedor(id),
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    dia_vencimento INTEGER NOT NULL CHECK (dia_vencimento BETWEEN 1 AND 28),
    inicio DATE NOT NULL,
    fim DATE,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS titulo (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    sentido TEXT NOT NULL CHECK (sentido IN ('pagar','receber')),
    descricao TEXT NOT NULL,
    fornecedor_id BIGINT REFERENCES fornecedor(id),
    tipo_despesa_id BIGINT REFERENCES tipo_despesa(id),
    canal TEXT,
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    taxa_pct NUMERIC(5,2),  -- a receber: taxa esperada, para a conciliação revelar a taxa real
    vencimento DATE NOT NULL,
    competencia DATE,
    origem_tipo TEXT NOT NULL DEFAULT 'manual' CHECK (origem_tipo IN ('manual','recebimento','sangria','acerto_entregador','recorrencia','fechamento','parcela','manutencao','folha')),
    origem_id BIGINT,
    parcela_num INTEGER,
    parcela_total INTEGER,
    grupo_id BIGINT,
    comprovante TEXT,
    aprovado BOOLEAN NOT NULL DEFAULT true,
    aprovado_por BIGINT REFERENCES usuario(id),
    situacao TEXT NOT NULL DEFAULT 'aberto' CHECK (situacao IN ('aberto','parcial','baixado','cancelado')),
    cancelado_motivo TEXT,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_titulo_venc ON titulo (loja_id, situacao, vencimento);
CREATE UNIQUE INDEX IF NOT EXISTS uq_titulo_origem ON titulo (origem_tipo, origem_id, COALESCE(competencia, DATE '0001-01-01')) WHERE origem_tipo NOT IN ('manual','parcela');

CREATE TABLE IF NOT EXISTS baixa_titulo (
    id BIGSERIAL PRIMARY KEY,
    titulo_id BIGINT NOT NULL REFERENCES titulo(id),
    data DATE NOT NULL,
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),   -- principal quitado
    desconto NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    juros NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (juros >= 0),
    multa NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (multa >= 0),
    valor_movimento NUMERIC(14,2) NOT NULL CHECK (valor_movimento >= 0),  -- o que de fato entrou ou saiu
    forma TEXT NOT NULL CHECK (forma IN ('dinheiro','pix','credito','debito','boleto','transferencia')),
    conta_id BIGINT REFERENCES conta_bancaria(id),  -- vazio: dinheiro da gaveta, que o Fechamento de Caixa já controla
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_baixa_valor CHECK (valor_movimento = valor - desconto + juros + multa)
);
CREATE INDEX IF NOT EXISTS idx_baixa_titulo ON baixa_titulo (titulo_id);
CREATE INDEX IF NOT EXISTS idx_baixa_conta ON baixa_titulo (conta_id, data);

-- Extrato digitado (OFX fica para depois) e o vínculo de cada linha com uma baixa.
CREATE TABLE IF NOT EXISTS extrato_linha (
    id BIGSERIAL PRIMARY KEY,
    conta_id BIGINT NOT NULL REFERENCES conta_bancaria(id),
    data DATE NOT NULL,
    descricao TEXT NOT NULL,
    valor NUMERIC(14,2) NOT NULL CHECK (valor <> 0),  -- com sinal: entrada positiva, saída negativa
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS conciliacao (
    id BIGSERIAL PRIMARY KEY,
    extrato_id BIGINT NOT NULL UNIQUE REFERENCES extrato_linha(id),
    baixa_id BIGINT NOT NULL UNIQUE REFERENCES baixa_titulo(id),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['baixa_titulo','extrato_linha','conciliacao'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

-- Título: o valor, o vencimento e a origem não mudam. Só a situação (pela baixa) e a aprovação. Cancelado e baixado não voltam.
CREATE OR REPLACE FUNCTION titulo_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Título não pode ser apagado: cancele com motivo.'; END IF;
    IF (NEW.loja_id, NEW.sentido, NEW.descricao, NEW.fornecedor_id, NEW.tipo_despesa_id, NEW.canal, NEW.valor, NEW.taxa_pct, NEW.vencimento, NEW.competencia,
        NEW.origem_tipo, NEW.origem_id, NEW.criado_em) IS DISTINCT FROM
       (OLD.loja_id, OLD.sentido, OLD.descricao, OLD.fornecedor_id, OLD.tipo_despesa_id, OLD.canal, OLD.valor, OLD.taxa_pct, OLD.vencimento, OLD.competencia,
        OLD.origem_tipo, OLD.origem_id, OLD.criado_em) THEN
        RAISE EXCEPTION 'Título aceita alterar apenas situação e aprovação.';
    END IF;
    IF OLD.situacao IN ('cancelado','baixado') AND NEW.situacao IS DISTINCT FROM OLD.situacao THEN
        RAISE EXCEPTION 'Título % não muda de situação.', OLD.situacao;
    END IF;
    IF OLD.aprovado AND NOT NEW.aprovado THEN RAISE EXCEPTION 'Aprovação não se desfaz.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_titulo_regra ON titulo;
CREATE TRIGGER trg_titulo_regra BEFORE UPDATE OR DELETE ON titulo FOR EACH ROW EXECUTE FUNCTION titulo_regra();

-- Baixa só entra em título aprovado e não cancelado, e nunca passa do valor do título.
CREATE OR REPLACE FUNCTION baixa_titulo_regra() RETURNS trigger AS $$
DECLARE t RECORD; pago NUMERIC;
BEGIN
    SELECT * INTO t FROM titulo WHERE id = NEW.titulo_id;
    IF t.situacao = 'cancelado' THEN RAISE EXCEPTION 'Título cancelado não recebe baixa.'; END IF;
    IF NOT t.aprovado THEN RAISE EXCEPTION 'Título aguardando aprovação não recebe baixa.'; END IF;
    SELECT COALESCE(sum(valor), 0) INTO pago FROM baixa_titulo WHERE titulo_id = NEW.titulo_id;
    IF pago + NEW.valor > t.valor THEN RAISE EXCEPTION 'A baixa passa do valor do título.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_baixa_titulo_regra ON baixa_titulo;
CREATE TRIGGER trg_baixa_titulo_regra BEFORE INSERT ON baixa_titulo FOR EACH ROW EXECUTE FUNCTION baixa_titulo_regra();
