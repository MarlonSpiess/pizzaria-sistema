-- Fatia 6: RH gerencial. Funcionários, contratos, escala, ponto, banco de horas, ausências, documentos e folha gerencial.
CREATE TABLE IF NOT EXISTS funcao_rh (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_funcao_rh ON funcao_rh (loja_id, lower(nome));

-- Tipo de escala é cadastro, não código: a legislação pode mudar de 6x1 para 5x2 ou outra.
CREATE TABLE IF NOT EXISTS escala_tipo (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    dias_trabalho INTEGER NOT NULL CHECK (dias_trabalho BETWEEN 1 AND 7),
    dias_folga INTEGER NOT NULL CHECK (dias_folga BETWEEN 0 AND 7),
    horas_semana NUMERIC(5,2) NOT NULL CHECK (horas_semana > 0 AND horas_semana <= 60),
    ativo BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_escala_tipo ON escala_tipo (loja_id, lower(nome));

CREATE TABLE IF NOT EXISTS funcionario (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    nome TEXT NOT NULL,
    telefone TEXT CHECK (telefone IS NULL OR telefone ~ '^[0-9]{8,15}$'),
    funcao_id BIGINT NOT NULL REFERENCES funcao_rh(id),
    usuario_id BIGINT UNIQUE REFERENCES usuario(id),
    admissao DATE NOT NULL,
    desligamento DATE,
    desligamento_motivo TEXT,
    preco_especial BOOLEAN NOT NULL DEFAULT false,  -- direito ao preço de funcionário em Vendas
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_func_desligamento CHECK (desligamento IS NULL OR desligamento >= admissao)
);

-- Contrato: histórico. O valor nunca é editado; um novo contrato encerra o anterior.
CREATE TABLE IF NOT EXISTS contrato (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('clt','intermitente','freelancer','diarista','prolabore','outro')),
    escala_id BIGINT REFERENCES escala_tipo(id),
    forma_pagamento TEXT NOT NULL CHECK (forma_pagamento IN ('mensal','diaria','hora')),
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    vigente_desde DATE NOT NULL,
    vigente_ate DATE,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_contrato_vigencia CHECK (vigente_ate IS NULL OR vigente_ate >= vigente_desde)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_vigente ON contrato (funcionario_id) WHERE vigente_ate IS NULL;

CREATE TABLE IF NOT EXISTS beneficio_funcionario (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    nome TEXT NOT NULL,
    valor_mensal NUMERIC(14,2) NOT NULL CHECK (valor_mensal > 0),
    ativo BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS turno (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    data DATE NOT NULL,
    funcao_id BIGINT NOT NULL REFERENCES funcao_rh(id),
    inicio TIME NOT NULL,
    fim TIME NOT NULL,
    UNIQUE (funcionario_id, data)
);

CREATE TABLE IF NOT EXISTS ponto (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    data DATE NOT NULL,
    entrada TIME NOT NULL,
    saida TIME NOT NULL,
    lancado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    UNIQUE (funcionario_id, data),
    CONSTRAINT ck_ponto_ordem CHECK (saida > entrada)
);

CREATE TABLE IF NOT EXISTS banco_horas (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    data DATE NOT NULL,
    minutos INTEGER NOT NULL CHECK (minutos <> 0),
    motivo TEXT NOT NULL,
    aprovado_por BIGINT NOT NULL REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ausencia (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ferias','afastamento','atestado','falta')),
    inicio DATE NOT NULL,
    fim DATE NOT NULL,
    motivo TEXT,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    CONSTRAINT ck_ausencia_ordem CHECK (fim >= inicio)
);

CREATE TABLE IF NOT EXISTS documento_rh (
    id BIGSERIAL PRIMARY KEY,
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    nome TEXT NOT NULL,
    emitido DATE,
    validade DATE NOT NULL,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL
);

-- Resumo da folha digitado a partir do que o contador entregou: gerencial, não legal.
CREATE TABLE IF NOT EXISTS folha_resumo (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    competencia DATE NOT NULL CHECK (EXTRACT(DAY FROM competencia) = 1),
    funcionario_id BIGINT NOT NULL REFERENCES funcionario(id),
    bruto NUMERIC(14,2) NOT NULL CHECK (bruto >= 0),
    encargos NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (encargos >= 0),
    beneficios NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (beneficios >= 0),
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id),
    UNIQUE (competencia, funcionario_id)
);

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['banco_horas','folha_resumo'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION recusar_alteracao()', t, t);
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_so_insercao_trunc ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_so_insercao_trunc BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao()', t, t);
    END LOOP;
END $$;

CREATE OR REPLACE FUNCTION contrato_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Contrato não pode ser apagado.'; END IF;
    IF (NEW.funcionario_id, NEW.tipo, NEW.escala_id, NEW.forma_pagamento, NEW.valor, NEW.vigente_desde) IS DISTINCT FROM (OLD.funcionario_id, OLD.tipo, OLD.escala_id, OLD.forma_pagamento, OLD.valor, OLD.vigente_desde) THEN
        RAISE EXCEPTION 'Contrato não muda: encerre e crie um novo.';
    END IF;
    IF OLD.vigente_ate IS NOT NULL AND NEW.vigente_ate IS DISTINCT FROM OLD.vigente_ate THEN RAISE EXCEPTION 'Contrato encerrado não muda.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_contrato_regra ON contrato;
CREATE TRIGGER trg_contrato_regra BEFORE UPDATE OR DELETE ON contrato FOR EACH ROW EXECUTE FUNCTION contrato_regra();

CREATE OR REPLACE FUNCTION funcionario_regra() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Funcionário não pode ser apagado: registre o desligamento.'; END IF;
    IF OLD.desligamento IS NOT NULL AND (NEW.desligamento IS DISTINCT FROM OLD.desligamento OR NEW.ativo) THEN RAISE EXCEPTION 'Funcionário desligado não é reativado nem muda a data de desligamento.'; END IF;
    IF NEW.admissao IS DISTINCT FROM OLD.admissao THEN RAISE EXCEPTION 'A data de admissão não muda.'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_funcionario_regra ON funcionario;
CREATE TRIGGER trg_funcionario_regra BEFORE UPDATE OR DELETE ON funcionario FOR EACH ROW EXECUTE FUNCTION funcionario_regra();
