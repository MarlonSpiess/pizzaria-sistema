"""Integração com canais de venda por consulta (varredura) e aviso de status.

O sistema chama o canal; o canal não chama o sistema. O adaptador de cada canal implementa duas operações.
O adaptador real do Anota Ai está PENDENTE da documentação da API: sem token e sem URL configurados, nada é chamado.
"""
import json
import logging
from typing import Protocol

from api.config import LOJA_ID
from api.database import agora

log = logging.getLogger("pizzaria.canais")
EVENTOS = ("pronto", "saiu_entrega", "disponivel_retirada")
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
    """Qual aviso o canal recebe quando o pedido muda de situação."""
    if nova == "acabado":
        return "disponivel_retirada" if tipo == "retirada" else "pronto"
    if nova == "despachado ou retirado" and tipo == "entrega":
        return "saiu_entrega"
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
