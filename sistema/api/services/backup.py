"""
Backup do banco: pg_dump em formato custom, cópia para as pastas extras (ex.: pasta do Google Drive para
computador e pasta do computador de Marlon) e retenção dos últimos N arquivos em cada pasta.
O PC da loja não fica ligado de madrugada: o backup roda ao fechar o dia ou pelo botão "fazer backup agora".
Usa conexão própria (não a do request) e trava de sessão: só um backup por vez, mesmo entre o servidor e o script.
Mensagens devolvidas ao usuário são fixas; o detalhe técnico vai só para o log do servidor.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException

from api.config import (BACKUP_ATRASO_HORAS, BACKUP_DIR, BACKUP_DIRS_EXTRA, BACKUP_RETENCAO, DB_CONFIG, LOJA_ID,
                        PG_DUMP)
from api.database import agora, get_connection

log = logging.getLogger("pizzaria.backup")
_PREFIXO = "pizzaria_"


def _podar(pasta: Path) -> None:
    arquivos = sorted(pasta.glob(f"{_PREFIXO}*.dump"), key=lambda p: p.name, reverse=True)
    for antigo in arquivos[BACKUP_RETENCAO:]:
        try:
            antigo.unlink()
        except OSError:
            log.warning("não foi possível apagar backup antigo %s", antigo)


def fazer_backup(acionado_por: str) -> dict:
    conn = get_connection()
    conn.autocommit = True
    try:
        if not conn.execute("SELECT pg_try_advisory_lock(3, 1) AS ok").fetchone()["ok"]:
            raise HTTPException(status_code=409, detail="Já existe um backup em andamento. Aguarde terminar.")
        try:
            return _executar(conn, acionado_por)
        finally:
            conn.execute("SELECT pg_advisory_unlock(3, 1)")
    finally:
        conn.close()


def _executar(conn, acionado_por: str) -> dict:
    inicio = agora()
    nome = f"{_PREFIXO}{DB_CONFIG['dbname']}_{inicio.strftime('%Y%m%d_%H%M%S_%f')}.dump"
    caminho = Path(BACKUP_DIR) / nome
    sucesso, detalhe, copias_ok, copias_falha, tamanho = False, None, 0, 0, None
    env = dict(os.environ, PGPASSWORD=DB_CONFIG["password"])
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([PG_DUMP, "-Fc", "-h", str(DB_CONFIG["host"]), "-p", str(DB_CONFIG["port"]),
                            "-U", DB_CONFIG["user"], "-d", DB_CONFIG["dbname"], "-f", str(caminho)],
                           env=env, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            log.error("pg_dump falhou: %s", r.stderr.strip()[-500:])
            detalhe = "O pg_dump falhou. Veja o registro do servidor."
        else:
            os.chmod(caminho, 0o600)  # contém hashes de senha
            sucesso, tamanho = True, caminho.stat().st_size
            _podar(caminho.parent)
            for extra in BACKUP_DIRS_EXTRA:
                try:
                    pasta = Path(extra.strip())
                    pasta.mkdir(parents=True, exist_ok=True)
                    destino = pasta / nome
                    shutil.copy2(caminho, destino)
                    if destino.stat().st_size != tamanho:
                        raise OSError("tamanho da cópia difere do original")
                    _podar(pasta)
                    copias_ok += 1
                except OSError as e:
                    copias_falha += 1
                    log.error("cópia do backup para %s falhou: %s", extra.strip(), e)
                    detalhe = "Uma ou mais cópias extras falharam. Veja o registro do servidor."
    except FileNotFoundError:
        log.error("pg_dump não encontrado (%s)", PG_DUMP)
        detalhe = "O programa pg_dump não foi encontrado. Defina PG_DUMP_PATH."
    except subprocess.TimeoutExpired:
        log.error("pg_dump excedeu o tempo limite")
        detalhe = "O pg_dump excedeu o tempo limite."
    except OSError as e:
        log.error("erro de arquivo no backup: %s", e)
        detalhe = "Não foi possível gravar na pasta de backup."
    if not sucesso:
        try:  # não deixa dump parcial entrar na retenção
            caminho.unlink(missing_ok=True)
        except OSError:
            pass
    conn.execute(
        "INSERT INTO backup_registro (loja_id, iniciado_em, concluido_em, sucesso, arquivo, tamanho_bytes, copias_ok, "
        "copias_falha, detalhe, acionado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (LOJA_ID, inicio, agora(), sucesso, nome if sucesso else None, tamanho, copias_ok, copias_falha, detalhe,
         acionado_por))
    return {"sucesso": sucesso, "arquivo": nome if sucesso else None, "tamanho_bytes": tamanho,
            "copias_ok": copias_ok, "copias_falha": copias_falha, "detalhe": detalhe}


def situacao(conn) -> dict:
    ultimo_ok = conn.execute("SELECT concluido_em, arquivo, tamanho_bytes, copias_ok, copias_falha, detalhe, acionado_por "
                             "FROM backup_registro WHERE loja_id = %s AND sucesso ORDER BY id DESC LIMIT 1",
                             (LOJA_ID,)).fetchone()
    ultima_tentativa = conn.execute("SELECT iniciado_em, sucesso, detalhe FROM backup_registro WHERE loja_id = %s "
                                    "ORDER BY id DESC LIMIT 1", (LOJA_ID,)).fetchone()
    atrasado = True
    if ultimo_ok:
        horas = (agora() - ultimo_ok["concluido_em"]).total_seconds() / 3600
        atrasado = horas > BACKUP_ATRASO_HORAS
    return {"ultimo_sucesso": ultimo_ok, "ultima_tentativa": ultima_tentativa, "atrasado": atrasado,
            "limite_horas": BACKUP_ATRASO_HORAS,
            "copias_extras_configuradas": len(BACKUP_DIRS_EXTRA)}
