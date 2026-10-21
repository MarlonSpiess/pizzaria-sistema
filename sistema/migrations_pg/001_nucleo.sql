-- Fatia 1A: Núcleo. Loja, usuários, sessões, bloqueio de login, parâmetros, auditoria e registro de backup.

CREATE TABLE IF NOT EXISTS loja (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usuario (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    usuario TEXT NOT NULL CHECK (usuario = lower(usuario)),
    nome TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (perfil IN
        ('administrador','proprietario','gerente','subgerente','atendente','massa','pizzaiolo','acabamento')),
    ativo BOOLEAN NOT NULL DEFAULT true,
    deve_trocar_senha BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_login ON usuario (loja_id, usuario);

CREATE TABLE IF NOT EXISTS sessao (
    token TEXT PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessao_usuario ON sessao(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sessao_expira ON sessao(expira_em);

-- Chave = IP + usuário digitado (exista ou não), para não revelar se o usuário existe.
CREATE TABLE IF NOT EXISTS login_falha (
    id BIGSERIAL PRIMARY KEY,
    chave TEXT NOT NULL,
    tentativa_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_login_falha_chave ON login_falha(chave, tentativa_em);
CREATE INDEX IF NOT EXISTS idx_login_falha_tentativa ON login_falha(tentativa_em);

-- Histórico de parâmetros: cada alteração é uma linha nova; vale a mais recente por chave.
CREATE TABLE IF NOT EXISTS parametro (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    chave TEXT NOT NULL,
    valor TEXT,
    vigente_desde TIMESTAMPTZ NOT NULL,
    criado_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_parametro_chave ON parametro(loja_id, chave, id DESC);

-- Auditoria: só inserção.
CREATE TABLE IF NOT EXISTS auditoria (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL,
    quando TIMESTAMPTZ NOT NULL,
    usuario_id BIGINT,
    usuario TEXT,
    acao TEXT NOT NULL,
    entidade TEXT NOT NULL,
    entidade_id TEXT,
    antes JSONB,
    depois JSONB
);
CREATE INDEX IF NOT EXISTS idx_auditoria_quando ON auditoria(loja_id, quando DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_entidade ON auditoria(entidade, entidade_id);

CREATE OR REPLACE FUNCTION recusar_alteracao() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Tabela % aceita apenas inserção.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auditoria_so_insercao ON auditoria;
CREATE TRIGGER trg_auditoria_so_insercao BEFORE UPDATE OR DELETE ON auditoria
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
DROP TRIGGER IF EXISTS trg_auditoria_so_insercao_trunc ON auditoria;
CREATE TRIGGER trg_auditoria_so_insercao_trunc BEFORE TRUNCATE ON auditoria
    FOR EACH STATEMENT EXECUTE FUNCTION recusar_alteracao();

CREATE TABLE IF NOT EXISTS backup_registro (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL,
    iniciado_em TIMESTAMPTZ NOT NULL,
    concluido_em TIMESTAMPTZ,
    sucesso BOOLEAN NOT NULL DEFAULT false,
    arquivo TEXT,
    tamanho_bytes BIGINT,
    copias_ok INTEGER NOT NULL DEFAULT 0,
    copias_falha INTEGER NOT NULL DEFAULT 0,
    detalhe TEXT,
    acionado_por TEXT
);
CREATE INDEX IF NOT EXISTS idx_backup_registro ON backup_registro(loja_id, iniciado_em DESC);
