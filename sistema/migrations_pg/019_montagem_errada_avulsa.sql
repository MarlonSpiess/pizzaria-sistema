-- Montagem errada (sabor ou formato/esteira): a pizza errada vira AVULSA (pode ser vendida à parte; sai do pedido) e a pizza certa recomeça.
-- Sem ingredientes: a pizza volta ao fim da fila e a gerência é avisada. Os avisos da Produção ficam numa tabela (só o "resolvido" muda, pela rota).
ALTER TABLE pizza_producao DROP CONSTRAINT IF EXISTS pizza_producao_situacao_check;
ALTER TABLE pizza_producao ADD CONSTRAINT pizza_producao_situacao_check
    CHECK (situacao IN ('na lista','em montagem','no forno','saiu do forno','acabada','perdida','cancelada','avulsa'));

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
    IF OLD.situacao IN ('perdida','cancelada','acabada','avulsa') AND NEW.situacao IS DISTINCT FROM OLD.situacao
       AND NOT (OLD.situacao = 'acabada' AND NEW.situacao = 'perdida') THEN
        RAISE EXCEPTION 'Pizza % é final.', OLD.situacao;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS aviso_producao (
    id BIGSERIAL PRIMARY KEY,
    loja_id INTEGER NOT NULL REFERENCES loja(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('sabor_errado','formato','sem_ingredientes')),
    pizza_id BIGINT NOT NULL REFERENCES pizza_producao(id),
    nova_pizza_id BIGINT REFERENCES pizza_producao(id),
    criado_por BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    resolvido_em TIMESTAMPTZ,
    resolvido_por BIGINT REFERENCES usuario(id)
);
CREATE INDEX IF NOT EXISTS idx_aviso_producao_aberto ON aviso_producao (loja_id, criado_em DESC) WHERE resolvido_em IS NULL;
CREATE INDEX IF NOT EXISTS idx_aviso_producao_pizza ON aviso_producao (pizza_id);

-- Destino da pizza avulsa: vendida (sem perda) ou descartada (vira perda, com motivo). Uma linha por pizza; só inserção.
CREATE TABLE IF NOT EXISTS pizza_avulsa_destino (
    pizza_id BIGINT PRIMARY KEY REFERENCES pizza_producao(id),
    destino TEXT NOT NULL CHECK (destino IN ('vendida','perda')),
    motivo_id BIGINT REFERENCES motivo_perda(id),
    usuario_id BIGINT REFERENCES usuario(id),
    criado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_avulsa_motivo CHECK ((destino = 'perda') = (motivo_id IS NOT NULL))
);
DROP TRIGGER IF EXISTS trg_avulsa_destino_so_insercao ON pizza_avulsa_destino;
CREATE TRIGGER trg_avulsa_destino_so_insercao BEFORE UPDATE OR DELETE ON pizza_avulsa_destino
    FOR EACH ROW EXECUTE FUNCTION recusar_alteracao();
