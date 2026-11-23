-- Pizza perdida depois de o pedido ficar acabado (decisão de Marlon, 23/11/2026, QA cego C2): o pedido volta de
-- 'acabado' para 'em producao' até a refação ficar pronta. Fora esse retorno, a situação continua só avançando.
CREATE OR REPLACE FUNCTION pedido_so_situacao() RETURNS trigger AS $$
DECLARE ordem TEXT[] := ARRAY['recebido','em producao','acabado','despachado ou retirado'];
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Pedido não pode ser apagado.';
    END IF;
    IF (NEW.loja_id, NEW.data, NEW.id_dia, NEW.canal, NEW.id_canal, NEW.cliente_id, NEW.tipo, NEW.subtotal, NEW.desconto, NEW.acrescimo,
        NEW.taxa_entrega, NEW.taxa_motivo, NEW.total, NEW.observacoes, NEW.chave, NEW.criado_em, NEW.criado_por) IS DISTINCT FROM
       (OLD.loja_id, OLD.data, OLD.id_dia, OLD.canal, OLD.id_canal, OLD.cliente_id, OLD.tipo, OLD.subtotal, OLD.desconto, OLD.acrescimo,
        OLD.taxa_entrega, OLD.taxa_motivo, OLD.total, OLD.observacoes, OLD.chave, OLD.criado_em, OLD.criado_por) THEN
        RAISE EXCEPTION 'Pedido aceita alterar apenas situação, urgência, entrega e número do CF.';
    END IF;
    IF NEW.situacao IS DISTINCT FROM OLD.situacao THEN
        IF OLD.situacao = 'cancelado' OR OLD.situacao = 'despachado ou retirado' THEN
            RAISE EXCEPTION 'Pedido % é final.', OLD.situacao;
        ELSIF NEW.situacao = 'cancelado' THEN
            NULL;
        ELSIF OLD.situacao = 'acabado' AND NEW.situacao = 'em producao' THEN
            NULL;  -- pizza perdida depois de acabado: volta para a produção
        ELSIF array_position(ordem, NEW.situacao) IS DISTINCT FROM array_position(ordem, OLD.situacao) + 1 THEN
            RAISE EXCEPTION 'Situação só avança um passo por vez.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
