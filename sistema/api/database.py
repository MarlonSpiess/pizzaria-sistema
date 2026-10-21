"""
Conexão PostgreSQL e helpers de SQL parametrizada.
Toda regra específica de banco fica isolada aqui; routers e services nunca montam SQL
com dado de usuário (placeholder `%s`, nunca f-string).
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
import psycopg.errors
from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from api.config import DB_CONFIG, LOCK_TIMEOUT_S, LOJA_ID, POOL_MAX, POOL_TIMEOUT_S, STATEMENT_TIMEOUT_S, TZ_BRASIL

_FUSO = ZoneInfo(TZ_BRASIL)


def agora() -> datetime:
    """Hora gerada pelo servidor, no fuso de Brasília (não depende do relógio/locale do host)."""
    return datetime.now(_FUSO)


def hoje():
    return agora().date()


def get_connection(connect_timeout: int = 10) -> psycopg.Connection:
    conn = psycopg.connect(host=DB_CONFIG["host"], port=DB_CONFIG["port"], dbname=DB_CONFIG["dbname"],
                           user=DB_CONFIG["user"], password=DB_CONFIG["password"], row_factory=dict_row,
                           connect_timeout=connect_timeout)
    conn.execute(f"SET TIME ZONE '{TZ_BRASIL}'")
    conn.commit()
    return conn


def _configurar(conn: psycopg.Connection) -> None:
    conn.execute(f"SET TIME ZONE '{TZ_BRASIL}'")
    conn.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT_S}s'")
    conn.execute(f"SET lock_timeout = '{LOCK_TIMEOUT_S}s'")
    conn.commit()


# Pool limitado: sob rajada o excedente espera e depois recebe 503, em vez de esgotar o Postgres.
pool = ConnectionPool(
    kwargs={"host": DB_CONFIG["host"], "port": DB_CONFIG["port"], "dbname": DB_CONFIG["dbname"],
            "user": DB_CONFIG["user"], "password": DB_CONFIG["password"], "row_factory": dict_row,
            "connect_timeout": 5},
    min_size=1, max_size=POOL_MAX, timeout=POOL_TIMEOUT_S, configure=_configurar, open=False,
    check=ConnectionPool.check_connection,
)


def get_db():
    """Dependency FastAPI: conexão do pool durante o request (rollback se sobrou transação aberta)."""
    try:
        try:
            conn = pool.getconn(timeout=min(1.5, POOL_TIMEOUT_S))
        except PoolTimeout:
            pool.check()
            conn = pool.getconn()
    except PoolTimeout:
        raise HTTPException(status_code=503, detail="Servidor ocupado. Tente novamente em instantes.",
                            headers={"Retry-After": "2"})
    try:
        yield conn
    finally:
        try:
            if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                conn.rollback()
        except psycopg.Error:
            pass
        finally:
            pool.putconn(conn)


def traduzir_erro(e: psycopg.Error) -> HTTPException:
    """Erros de integridade viram mensagens em português; detalhe técnico nunca vai ao cliente."""
    if isinstance(e, psycopg.errors.UniqueViolation):
        return HTTPException(status_code=409, detail="Já existe um registro com esses dados.")
    if isinstance(e, psycopg.errors.ForeignKeyViolation):
        return HTTPException(status_code=400, detail="Referência inválida: registro relacionado não encontrado.")
    if isinstance(e, psycopg.errors.CheckViolation):
        return HTTPException(status_code=400, detail="Valor fora do domínio permitido para este campo.")
    if isinstance(e, psycopg.errors.NotNullViolation):
        return HTTPException(status_code=400, detail="Campo obrigatório não informado.")
    if isinstance(e, psycopg.errors.DataError):
        return HTTPException(status_code=400, detail="Dado inválido para este campo.")
    if isinstance(e, psycopg.errors.IntegrityError):
        return HTTPException(status_code=400, detail="Operação viola uma regra de integridade do banco.")
    raise e


def run(conn: psycopg.Connection, sql: str, params=None, fetch: str = "none"):
    """Executa SQL parametrizado e comita. fetch: "none" (rowcount), "one" (dict ou None) ou "all" (lista)."""
    try:
        cur = conn.execute(sql, params or ())
        resultado = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else cur.rowcount
        conn.commit()
        return resultado
    except (psycopg.errors.IntegrityError, psycopg.errors.DataError) as e:
        conn.rollback()
        raise traduzir_erro(e) from e


def auditar(conn: psycopg.Connection, sessao: dict | None, acao: str, entidade: str, entidade_id=None,
            antes=None, depois=None) -> None:
    """Registra na auditoria, na MESMA transação da alteração (quem chama faz o commit)."""
    conn.execute(
        "INSERT INTO auditoria (loja_id, quando, usuario_id, usuario, acao, entidade, entidade_id, antes, depois) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)",
        (LOJA_ID, agora(), sessao["usuario_id"] if sessao else None, sessao["usuario"] if sessao else None,
         acao, entidade, None if entidade_id is None else str(entidade_id),
         None if antes is None else json.dumps(antes, default=str),
         None if depois is None else json.dumps(depois, default=str)))
