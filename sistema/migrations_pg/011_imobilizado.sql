-- Fatia 5: Imobilizado. Bens, depreciação mensal, baixa, conferência, plano de manutenção, leituras e ordens de serviço.
CREATE TABLE IF NOT EXISTS categoria_bem (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    taxa_fiscal_pct NUMERIC(5,2) NOT NULL CHECK (taxa_fiscal_pct > 0 AND taxa_fiscal_pct <= 100),
    veiculo BOOLEAN NOT NULL DEFAULT false,  -- veículo pede placa e quilometragem
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_bem ON categoria_bem (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS bem (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    codigo TEXT NOT NULL,  -- plaqueta
    nome TEXT NOT NULL,
    categoria_id BIGINT NOT NULL REFERENCES categoria_bem(id),
    valor_aquisicao NUMERIC(14,2) NOT NULL CHECK (valor_aquisicao > 0),
    data_aquisicao DATE NOT NULL,
    inicio_uso DATE,
    fornecedor_id BIGINT REFERENCES fornecedor(id),
    numero_nota TEXT,
    local_texto TEXT,
    responsavel TEXT,
    numero_serie TEXT,
    placa TEXT,
    quilometragem INTEGER CHECK (quilometragem IS NULL OR quilometragem >= 0),
    critico BOOLEAN NOT NULL DEFAULT false,
    metodo TEXT NOT NULL DEFAULT 'fiscal' CHECK (metodo IN ('fiscal','vida_util')),
    vida_util_meses INTEGER CHECK (vida_util_meses IS NULL OR vida_util_meses BETWEEN 1 AND 600),
    valor_residual NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (valor_residual >= 0),
    garantia_ate DATE,
    seguro_ate DATE,
    apolice TEXT,
    situacao TEXT NOT NULL DEFAULT 'ativo' CHECK (situacao IN ('ativo','baixado')),
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_bem_residual CHECK (valor_residual < valor_aquisicao),
    CONSTRAINT ck_bem_metodo CHECK (metodo = 'fiscal' OR vida_util_meses IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_bem_codigo ON bem (loja_id, lower(codigo));

ALTER TABLE titulo ADD COLUMN IF NOT EXISTS bem_id BIGINT REFERENCES bem(id);

CREATE TABLE IF NOT EXISTS baixa_bem (
    id BIGSERIAL PRIMARY KEY,
    bem_id BIGINT NOT NULL UNIQUE REFERENCES bem(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('venda','perda','descarte','doacao')),
    data DATE NOT NULL,
    valor NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (valor >= 0),
    motivo TEXT NOT NULL,
    aprovado_por BIGINT NOT NULL REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS depreciacao_bem (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    competencia DATE NOT NULL CHECK (EXTRACT(DAY FROM competencia) = 1),
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    criado_em TIMESTAMPTZ NOT NULL,
    UNIQUE (bem_id, competencia)
);
CREATE INDEX IF NOT EXISTS idx_depreciacao_comp ON depreciacao_bem (loja_id, competencia);

CREATE TABLE IF NOT EXISTS conferencia_bem (
    id BIGSERIAL PRIMARY KEY,
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    data DATE NOT NULL,
    encontrado BOOLEAN NOT NULL,
    local_encontrado TEXT,
    observacao TEXT,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS plano_manutencao (
    id BIGSERIAL PRIMARY KEY,
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    tarefa TEXT NOT NULL,
    periodicidade_dias INTEGER NOT NULL CHECK (periodicidade_dias BETWEEN 1 AND 3650),
    antecedencia_dias INTEGER NOT NULL DEFAULT 7 CHECK (antecedencia_dias BETWEEN 0 AND 365),
    ultima_em DATE,
    base_em DATE NOT NULL,  -- de onde conta o primeiro vencimento
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL
);

-- Leitura digitada na inspeção (preditiva) e o limite normal de cada grandeza do bem.
CREATE TABLE IF NOT EXISTS limite_leitura (
    id BIGSERIAL PRIMARY KEY,
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    grandeza TEXT NOT NULL,
    unidade TEXT,
    minimo NUMERIC(14,3),
    maximo NUMERIC(14,3),
    CHECK (minimo IS NOT NULL OR maximo IS NOT NULL),
    UNIQUE (bem_id, grandeza)
);
CREATE TABLE IF NOT EXISTS leitura_bem (
    id BIGSERIAL PRIMARY KEY,
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    grandeza TEXT NOT NULL,
    valor NUMERIC(14,3) NOT NULL,
    data DATE NOT NULL,
    fora_do_normal BOOLEAN NOT NULL,
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS os_numero_seq;
CREATE TABLE IF NOT EXISTS ordem_servico (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    numero BIGINT NOT NULL DEFAULT nextval('os_numero_seq'),
    bem_id BIGINT NOT NULL REFERENCES bem(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('preventiva','preditiva','corretiva')),
    plano_id BIGINT REFERENCES plano_manutencao(id),
    situacao TEXT NOT NULL DEFAULT 'aberta' CHECK (situacao IN ('aberta','em_execucao','fechada','cancelada')),
    descricao TEXT NOT NULL,
    causa TEXT,
    servico_feito TEXT,
    executor_tipo TEXT CHECK (executor_tipo IN ('funcionario','terceiro')),
    executor_nome TEXT,
    fornecedor_id BIGINT REFERENCES fornecedor(id),
    parada_inicio TIMESTAMPTZ,
    parada_fim TIMESTAMPTZ,
    mao_obra NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (mao_obra >= 0),
    custo_pecas NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (custo_pecas >= 0),
    custo_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    precisa_aprovacao BOOLEAN NOT NULL DEFAULT false,
    aprovado_por BIGINT REFERENCES usuario(id),
    aprovado_valor NUMERIC(14,2),
    aberta_em TIMESTAMPTZ NOT NULL,
    aberta_por BIGINT REFERENCES usuario(id),
    fechada_em TIMESTAMPTZ,
    fechada_por BIGINT REFERENCES usuario(id),
    UNIQUE (loja_id, numero)
);
CREATE TABLE IF NOT EXISTS os_peca (
    id BIGSERIAL PRIMARY KEY,
    os_id BIGINT NOT NULL REFERENCES ordem_servico(id),
    item_id BIGINT NOT NULL REFERENCES item(id),
    quantidade NUMERIC(14,4) NOT NULL CHECK (quantidade > 0),
    custo_unit NUMERIC(14,6),
    criado_em TIMESTAMPTZ NOT NULL
);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['baixa_bem','depreciacao_bem','conferencia_bem','leitura_bem','os_peca'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();', t, t);
    END LOOP;
END $$;

-- Bem baixado não muda mais; o valor de aquisição, a data e a categoria nunca mudam.
CREATE OR REPLACE FUNCTION bem_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Bem não pode ser apagado: dê baixa.'; END IF;
    IF (NEW.loja_id, NEW.valor_aquisicao, NEW.data_aquisicao, NEW.categoria_id, NEW.codigo) IS DISTINCT FROM (OLD.loja_id, OLD.valor_aquisicao, OLD.data_aquisicao, OLD.categoria_id, OLD.codigo) THEN
        RAISE EXCEPTION 'Valor, data, categoria e plaqueta do bem não mudam.';
    END IF;
    IF OLD.situacao = 'baixado' THEN RAISE EXCEPTION 'Bem baixado não muda.'; END IF;
    IF OLD.inicio_uso IS NOT NULL AND NEW.inicio_uso IS DISTINCT FROM OLD.inicio_uso THEN RAISE EXCEPTION 'O início de uso não muda depois de informado.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_bem_regra ON bem;
CREATE TRIGGER trg_bem_regra BEFORE UPDATE OR DELETE ON bem FOR EACH ROW EXECUTE FUNCTION bem_regra();

-- Ordem de serviço só avança: aberta, em execução, fechada. Fechada e cancelada não mudam.
CREATE OR REPLACE FUNCTION os_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Ordem de serviço não pode ser apagada: cancele.'; END IF;
    IF (NEW.bem_id, NEW.tipo, NEW.numero, NEW.aberta_em) IS DISTINCT FROM (OLD.bem_id, OLD.tipo, OLD.numero, OLD.aberta_em) THEN RAISE EXCEPTION 'Bem, tipo e número da ordem não mudam.'; END IF;
    IF OLD.situacao IN ('fechada','cancelada') THEN RAISE EXCEPTION 'Ordem % não muda.', OLD.situacao; END IF;
    IF NOT ((OLD.situacao = 'aberta' AND NEW.situacao IN ('aberta','em_execucao','fechada','cancelada')) OR (OLD.situacao = 'em_execucao' AND NEW.situacao IN ('em_execucao','fechada','cancelada'))) THEN
        RAISE EXCEPTION 'Transição inválida da ordem de serviço.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_os_regra ON ordem_servico;
CREATE TRIGGER trg_os_regra BEFORE UPDATE OR DELETE ON ordem_servico FOR EACH ROW EXECUTE FUNCTION os_regra();
