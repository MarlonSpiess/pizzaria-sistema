"""Integração com canais de venda por consulta (varredura) e aviso de status.

O sistema chama o canal; o canal não chama o sistema. O adaptador de cada canal implementa duas operações.
O adaptador real do Anota Ai está PENDENTE da documentação da API: sem token e sem URL configurados, nada é chamado.
"""
import json
import logging
from typing import Protocol

from api.config import LOJA_ID
from api.database import agora, hoje
from api.services.caixa import ultimo_caixa

log = logging.getLogger("pizzaria.canais")
EVENTOS = ("pronto", "finalizado")
ESPERA_MAX_S = 300  # espera máxima entre tentativas de aviso


class Adaptador(Protocol):
    codigo: str

    def configurado(self) -> bool: ...

    def buscar_novos(self) -> list[dict]:
        """Pedidos novos do canal. Cada item traz ao menos {"id_externo": str} e o conteúdo bruto."""

    def avisar(self, id_externo: str, evento: str) -> None:
        """Informa o status ao canal. Levanta exceção se falhar."""


def varrer(conn, canal_id: int, adaptador: Adaptador) -> int:
    """Uma varredura: guarda na fila de entrada o que ainda não está lá. Repetir é seguro (idempotente)."""
    novos = adaptador.buscar_novos()
    n = 0
    for item in novos:
        if not isinstance(item, dict) or not item.get("id_externo"):
            log.warning("Item sem id_externo ignorado na varredura do canal %s.", canal_id)
            continue
        ext = str(item["id_externo"])[:80]
        r = conn.execute(
            "INSERT INTO entrada_canal (loja_id, canal_id, id_externo, conteudo, recebido_em) VALUES (%s,%s,%s,%s::jsonb,%s) "
            "ON CONFLICT (canal_id, id_externo) DO NOTHING", (LOJA_ID, canal_id, ext, json.dumps(item, default=str), agora()))
        n += r.rowcount
    conn.commit()
    return n


def evento_da_situacao(tipo: str, nova: str) -> str | None:
    """Qual aviso o canal recebe quando o pedido muda de situação (regra pelo manual do Anota Ai, a confirmar com a API).

    No Anota Ai "Pronto" já diz ao cliente "a caminho" (entrega) ou "disponível para retirada".
    - Retirada: pronta no balcão (acabado) = Pronto; retirada pelo cliente = Finalizado.
    - Entrega: "Pronto" só quando o entregador sai (despachado), para o cliente não ser avisado antes da hora.
      Finalizar a entrega (cliente recebeu) fica PENDENTE: o sistema não tem confirmação de entrega.
    """
    if tipo == "retirada":
        return "pronto" if nova == "acabado" else "finalizado" if nova == "despachado ou retirado" else None
    if tipo == "entrega" and nova == "despachado ou retirado":
        return "pronto"
    return None


def enfileirar_aviso(conn, pedido_id: int, canal: str, tipo: str, nova: str) -> None:
    """Chamado na mesma transação da mudança de situação. Só pedido de canal externo gera aviso.

    Não exige canal ativo: se o canal ficar desligado um tempo, o aviso espera e sai quando ele voltar.
    Falha aqui nunca pode impedir a mudança de situação do pedido (savepoint)."""
    if canal == "balcao":
        return
    evento = evento_da_situacao(tipo, nova)
    if not evento:
        return
    try:
        with conn.transaction():
            c = conn.execute("SELECT id FROM canal_venda WHERE loja_id = %s AND codigo = %s", (LOJA_ID, canal)).fetchone()
            if c:
                conn.execute("INSERT INTO aviso_canal (loja_id, canal_id, pedido_id, evento) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                             (LOJA_ID, c["id"], pedido_id, evento))
    except Exception:  # noqa: BLE001
        log.exception("Não foi possível enfileirar o aviso %s do pedido %s", evento, pedido_id)


MAX_TENTATIVAS = 20  # depois disso o aviso fica parado com o erro registrado, para a gerência ver
RESERVA_S = 60       # tempo em que um aviso reservado não é pego por outro ciclo


def enviar_avisos(conn, canal_id: int, adaptador: Adaptador, limite: int = 20) -> int:
    """Reserva (commit curto), envia SEM transação aberta e marca o resultado de cada aviso em seu próprio commit.

    O adaptador real precisa de timeout de rede curto. Entrega é 'pelo menos uma vez': o canal deve aceitar repetição."""
    agora_ = agora()
    pend = conn.execute(
        "SELECT a.id, a.evento, a.tentativas, p.id_canal FROM aviso_canal a JOIN pedido p ON p.id = a.pedido_id "
        "WHERE a.canal_id = %s AND a.enviado_em IS NULL AND a.proxima_tentativa <= %s AND a.tentativas < %s "
        "ORDER BY a.id LIMIT %s FOR UPDATE OF a SKIP LOCKED", (canal_id, agora_, MAX_TENTATIVAS, limite)).fetchall()
    for a in pend:
        conn.execute("UPDATE aviso_canal SET proxima_tentativa = %s + make_interval(secs => %s) WHERE id = %s", (agora_, RESERVA_S, a["id"]))
    conn.commit()
    enviados = 0
    for a in pend:
        erro = None
        try:
            if not a["id_canal"]:
                raise ValueError("Pedido sem identificador no canal.")
            adaptador.avisar(a["id_canal"], a["evento"])
        except Exception as e:  # noqa: BLE001 - qualquer falha do canal só reagenda
            erro = str(e)[:200]
            log.warning("Aviso %s ao canal falhou (tentativa %s).", a["evento"], a["tentativas"] + 1)
        if erro is None:
            conn.execute("UPDATE aviso_canal SET enviado_em = %s, tentativas = tentativas + 1, erro = NULL WHERE id = %s", (agora(), a["id"]))
            enviados += 1
        else:
            espera = min(ESPERA_MAX_S, 2 ** min(a["tentativas"] + 1, 8))
            conn.execute("UPDATE aviso_canal SET tentativas = tentativas + 1, erro = %s, proxima_tentativa = %s + make_interval(secs => %s) WHERE id = %s",
                         (erro, agora(), espera, a["id"]))
        conn.commit()
    return enviados


# ------------------------------------------------------------ importação (estados da entrada)
IMPORTANDO_MAX_S = 120  # PROVISÓRIO: tempo até considerar a importação parada. Revisar com a API; o aceite no canal precisa ser idempotente.
IMPORTACAO_MAX_TENTATIVAS = 3  # depois disso a entrada vira "bloqueada" para a gerência ver, em vez de travar a fila


def ha_importando(conn, canal_id: int) -> bool:
    """Há importação em andamento? Enquanto houver, a varredura espera (decisão de Marlon)."""
    return bool(conn.execute(
        "SELECT 1 FROM entrada_canal WHERE canal_id = %s AND situacao = 'importando' AND importando_desde > %s - make_interval(secs => %s) LIMIT 1",
        (canal_id, agora(), IMPORTANDO_MAX_S)).fetchone())


def liberar_importacoes_paradas(conn, canal_id: int) -> int:
    """Importação parada (o processo caiu no meio) volta para a fila; na 3ª vez vira 'bloqueada' para a gerência decidir."""
    r = conn.execute(
        "UPDATE entrada_canal SET importacao_tentativas = importacao_tentativas + 1, importando_desde = NULL, "
        "situacao = CASE WHEN importacao_tentativas + 1 >= %s THEN 'bloqueada' ELSE 'pendente' END, "
        "motivo = CASE WHEN importacao_tentativas + 1 >= %s THEN 'A importação falhou várias vezes' ELSE motivo END "
        "WHERE canal_id = %s AND situacao = 'importando' AND importando_desde <= %s - make_interval(secs => %s)",
        (IMPORTACAO_MAX_TENTATIVAS, IMPORTACAO_MAX_TENTATIVAS, canal_id, agora(), IMPORTANDO_MAX_S))
    conn.commit()
    return r.rowcount


def iniciar_importacao(conn, canal_id: int) -> dict | None:
    """Pega a próxima entrada pendente e a marca como 'importando' (uma só por vez, seguro com vários processos).
    PENDENTE da API: o aceite no Anota Ai (obrigatório em 15 minutos) e a criação do pedido ainda não existem."""
    e = conn.execute("SELECT id, id_externo, conteudo FROM entrada_canal WHERE canal_id = %s AND situacao = 'pendente' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED",
                     (canal_id,)).fetchone()
    if e:
        conn.execute("UPDATE entrada_canal SET situacao = 'importando', importando_desde = %s WHERE id = %s", (agora(), e["id"]))
    conn.commit()
    return e


def concluir_importacao(conn, entrada_id: int, pedido_id: int) -> None:
    """Marca importada. Quem chama faz o commit junto com a criação do pedido. Falha se a entrada não está mais 'importando'
    (ex.: foi liberada por demora): nesse caso o chamador deve desfazer a transação para não duplicar o pedido."""
    r = conn.execute("UPDATE entrada_canal SET situacao = 'importada', pedido_id = %s, importando_desde = NULL, motivo = NULL WHERE id = %s AND situacao = 'importando'",
                     (pedido_id, entrada_id))
    if r.rowcount != 1:
        raise RuntimeError("A entrada não está mais em importação.")


def bloquear_importacao(conn, entrada_id: int, motivo: str) -> None:
    """A loja não pode produzir este pedido: fica na fila para a gerência decidir. Quem chama faz o commit."""
    r = conn.execute("UPDATE entrada_canal SET situacao = 'bloqueada', motivo = %s, importando_desde = NULL WHERE id = %s AND situacao = 'importando'",
                     (motivo[:200], entrada_id))
    if r.rowcount != 1:
        raise RuntimeError("A entrada não está mais em importação.")


# ------------------------------------------------------------ aceitar sozinho
def pode_aceitar_sozinho(conn, canal: dict, ids_externos: list[str]) -> tuple[bool, str | None]:
    """Decide se o pedido pode ser aceito sem a gerência. Devolve (pode, motivo se não pode).

    Critérios (decisão de Marlon, 04/11/2026): canal ativo com a flag ligada, caixa DE HOJE aberto e todos os itens no mapa
    de produtos (produto ativo). PENDENTE: "loja aberta" (não existe esse estado no sistema; falta definir se é o caixa
    aberto, um horário ou uma pausa). Recebe os identificadores externos dos itens porque o formato do pedido do Anota Ai
    ainda não é conhecido. Releia o canal no banco antes de chamar, para a flag não vir desatualizada.
    """
    if not canal.get("ativo", True):
        return False, "Canal desativado."
    if not canal["aceitar_sozinho"]:
        return False, "Aceite automático desligado."
    c = ultimo_caixa(conn, LOJA_ID)
    if not c or c["situacao"] != "aberto" or c.get("data") != hoje():
        return False, "O caixa de hoje não está aberto."
    ids = sorted({str(i).strip() for i in ids_externos if i is not None and str(i).strip()})
    if not ids:
        return False, "Pedido sem itens identificados."
    mapeados = {r["id_externo"] for r in conn.execute(
        "SELECT m.id_externo FROM mapa_produto_canal m JOIN produto p ON p.id = m.produto_id AND p.ativo AND p.loja_id = %s "
        "WHERE m.canal_id = %s AND m.id_externo = ANY(%s)", (LOJA_ID, canal["id"], ids)).fetchall()}
    faltam = [i for i in ids if i not in mapeados]
    if faltam:
        return False, "Itens fora do mapa de produtos: " + ", ".join(faltam)[:150]
    return True, None
