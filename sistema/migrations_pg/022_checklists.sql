-- Módulo de Checklists (melhoria M4, proposta de 16/11/2026): início, acompanhamento e fim do dia, com registro por função.
-- Modelos têm versões; uma execução aponta para a versão que usou. Respostas são só de inserção (corrigir = nova resposta).

CREATE TABLE IF NOT EXISTS checklist_modelo (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    codigo TEXT NOT NULL CHECK (codigo = lower(codigo)),
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('inicio_dia','acompanhamento','fim_dia')),
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_modelo ON checklist_modelo (loja_id, codigo);

CREATE TABLE IF NOT EXISTS checklist_versao (
    id BIGSERIAL PRIMARY KEY,
    modelo_id BIGINT NOT NULL REFERENCES checklist_modelo(id),
    numero INTEGER NOT NULL CHECK (numero > 0),
    vigente BOOLEAN NOT NULL DEFAULT true,
    publicada_em TIMESTAMPTZ NOT NULL,
    publicada_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_versao ON checklist_versao (modelo_id, numero);
-- no máximo uma versão vigente por modelo
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_versao_vigente ON checklist_versao (modelo_id) WHERE vigente;

CREATE TABLE IF NOT EXISTS checklist_item (
    id BIGSERIAL PRIMARY KEY,
    versao_id BIGINT NOT NULL REFERENCES checklist_versao(id),
    setor TEXT NOT NULL,
    ordem INTEGER NOT NULL CHECK (ordem >= 0),
    codigo TEXT NOT NULL,
    texto TEXT NOT NULL,
    criterio TEXT,
    perfil_responsavel TEXT CHECK (perfil_responsavel IN
        ('administrador','proprietario','gerente','subgerente','atendente','massa','pizzaiolo','acabamento')),  -- nulo = qualquer função
    tipo_resposta TEXT NOT NULL DEFAULT 'marcar' CHECK (tipo_resposta IN ('marcar','numero','automatico')),
    fonte_auto TEXT CHECK (fonte_auto IN ('caixa_aberto','loja_aberta','backup_do_dia')),
    unidade TEXT,
    limite_min NUMERIC(8,2),
    limite_max NUMERIC(8,2),
    limite_min_param TEXT,  -- chave de parâmetro da loja que define o limite mínimo (vale quando preenchida)
    limite_max_param TEXT,  -- idem para o máximo
    obrigatorio BOOLEAN NOT NULL DEFAULT true,
    recorrencia TEXT NOT NULL DEFAULT 'todo_turno' CHECK (recorrencia IN ('todo_turno','diario','semanal','mensal','semestral')),
    origem TEXT,
    CONSTRAINT ck_checklist_item_auto CHECK ((tipo_resposta = 'automatico') = (fonte_auto IS NOT NULL)),
    CONSTRAINT ck_checklist_item_limites CHECK (limite_min IS NULL OR limite_max IS NULL OR limite_min <= limite_max)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_item ON checklist_item (versao_id, codigo);
CREATE INDEX IF NOT EXISTS idx_checklist_item_versao ON checklist_item (versao_id, ordem);

CREATE TABLE IF NOT EXISTS checklist_execucao (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    versao_id BIGINT NOT NULL REFERENCES checklist_versao(id),
    data DATE NOT NULL,
    turno TEXT NOT NULL DEFAULT 'dia' CHECK (length(turno) BETWEEN 1 AND 30),
    situacao TEXT NOT NULL DEFAULT 'aberta' CHECK (situacao IN ('aberta','concluida','concluida_com_pendencia')),
    iniciada_em TIMESTAMPTZ NOT NULL,
    iniciada_por BIGINT REFERENCES usuario(id),
    concluida_em TIMESTAMPTZ,
    concluida_por BIGINT REFERENCES usuario(id)
);
-- uma execução por modelo (via versão), dia e turno: o índice por versão cobre o caso comum; a regra de modelo fica no serviço
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_execucao ON checklist_execucao (loja_id, versao_id, data, turno);
CREATE INDEX IF NOT EXISTS idx_checklist_execucao_data ON checklist_execucao (loja_id, data);

-- Respostas: só inserção. A resposta vigente de um item é a mais recente da execução.
CREATE TABLE IF NOT EXISTS checklist_resposta (
    id BIGSERIAL PRIMARY KEY,
    execucao_id BIGINT NOT NULL REFERENCES checklist_execucao(id),
    item_id BIGINT NOT NULL REFERENCES checklist_item(id),
    resultado TEXT NOT NULL CHECK (resultado IN ('conforme','nao_conforme','nao_se_aplica')),
    valor_numerico NUMERIC(8,2),
    valor_texto TEXT,
    acao_corretiva TEXT,
    fora_do_limite BOOLEAN NOT NULL DEFAULT false,
    automatica BOOLEAN NOT NULL DEFAULT false,
    respondida_em TIMESTAMPTZ NOT NULL,
    respondida_por BIGINT REFERENCES usuario(id),
    substitui_id BIGINT REFERENCES checklist_resposta(id),
    CONSTRAINT ck_checklist_resposta_acao CHECK (resultado <> 'nao_conforme' OR automatica OR (acao_corretiva IS NOT NULL AND length(btrim(acao_corretiva)) > 0)),
    CONSTRAINT ck_checklist_resposta_na CHECK (resultado <> 'nao_se_aplica' OR (valor_texto IS NOT NULL AND length(btrim(valor_texto)) > 0))
);
CREATE INDEX IF NOT EXISTS idx_checklist_resposta ON checklist_resposta (execucao_id, item_id, id DESC);

DROP TRIGGER IF EXISTS trg_checklist_resposta_so_insercao ON checklist_resposta;
CREATE TRIGGER trg_checklist_resposta_so_insercao BEFORE UPDATE OR DELETE ON checklist_resposta
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
DROP TRIGGER IF EXISTS trg_checklist_resposta_so_insercao_trunc ON checklist_resposta;
CREATE TRIGGER trg_checklist_resposta_so_insercao_trunc BEFORE TRUNCATE ON checklist_resposta
    FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();

CREATE TABLE IF NOT EXISTS checklist_pendencia (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    resposta_id BIGINT NOT NULL REFERENCES checklist_resposta(id),
    descricao TEXT NOT NULL,
    perfil_responsavel TEXT,
    criada_em TIMESTAMPTZ NOT NULL,
    resolvida_em TIMESTAMPTZ,
    resolvida_por BIGINT REFERENCES usuario(id),
    resolucao TEXT,
    CONSTRAINT ck_checklist_pendencia_res CHECK ((resolvida_em IS NULL) = (resolvida_por IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_checklist_pendencia_resposta ON checklist_pendencia (resposta_id);
CREATE INDEX IF NOT EXISTS idx_checklist_pendencia_aberta ON checklist_pendencia (loja_id) WHERE resolvida_em IS NULL;
