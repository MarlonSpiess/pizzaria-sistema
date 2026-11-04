"""Rotina em segundo plano: a cada segundo consulta os canais ativos e envia os avisos de status pendentes.

Só age em canal ATIVO e com adaptador configurado. Falha do canal (internet, token) não derruba o sistema: registra e tenta de novo.
"""
import logging
import os
import threading
import time

from api.config import LOJA_ID
from api.database import pool
from api.services import canais
from api.services.anotaai import AnotaAi

log = logging.getLogger("pizzaria.varredor")
def _intervalo() -> float:
    try:
        return max(1.0, float(os.getenv("CANAIS_INTERVALO_S", "1")))
    except ValueError:
        return 1.0


INTERVALO_S = _intervalo()
_proxima_varredura: dict[str, float] = {}
_falhas: dict[str, int] = {}
ADAPTADORES = [AnotaAi()]
_parar = threading.Event()
_thread: threading.Thread | None = None


def ciclo(adaptadores=None) -> None:
    """Um ciclo para cada canal ativo com adaptador configurado. Só um processo por vez trabalha em cada canal (trava no banco)."""
    for ad in (adaptadores if adaptadores is not None else ADAPTADORES):
        if not ad.configurado():
            continue
        with pool.connection() as conn:
            c = conn.execute("SELECT id FROM canal_venda WHERE loja_id = %s AND codigo = %s AND ativo", (LOJA_ID, ad.codigo)).fetchone()
            if not c:
                continue
            if not conn.execute("SELECT pg_try_advisory_lock(%s, %s) AS ok", (21, c["id"])).fetchone()["ok"]:
                continue
            try:
                if time.monotonic() >= _proxima_varredura.get(ad.codigo, 0):
                    try:
                        canais.varrer(conn, c["id"], ad)
                        _falhas[ad.codigo] = 0
                    except Exception as e:  # noqa: BLE001
                        conn.rollback()
                        n = _falhas[ad.codigo] = _falhas.get(ad.codigo, 0) + 1
                        _proxima_varredura[ad.codigo] = time.monotonic() + min(60, 2 ** min(n, 6))  # espera crescente se o canal cair
                        if n in (1, 10) or n % 60 == 0:
                            log.warning("Varredura do canal %s falhou (%s seguidas): %s", ad.codigo, n, type(e).__name__)
                canais.enviar_avisos(conn, c["id"], ad)
            finally:
                conn.rollback()
                conn.execute("SELECT pg_advisory_unlock(%s, %s)", (21, c["id"]))
                conn.commit()


def _laco() -> None:
    while not _parar.is_set():
        try:
            ciclo()
        except Exception as e:  # noqa: BLE001
            log.warning("Ciclo do varredor falhou: %s", type(e).__name__)
        _parar.wait(INTERVALO_S)


def iniciar() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    if not any(a.configurado() for a in ADAPTADORES):
        log.info("Varredor de canais desligado: nenhum canal configurado.")
        return
    _parar.clear()
    _thread = threading.Thread(target=_laco, name="varredor-canais", daemon=True)
    _thread.start()


def parar() -> None:
    _parar.set()
    global _thread
    if _thread:
        _thread.join(timeout=5)
        _thread = None
