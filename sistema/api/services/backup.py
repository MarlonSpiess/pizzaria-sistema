"""
Backup do banco: pg_dump em formato custom, cópia para as pastas extras (ex.: pasta do Google Drive para
computador e pasta do computador de Marlon) e retenção dos últimos N arquivos em cada pasta.
O PC da loja não fica ligado de madrugada: o backup roda ao fechar o dia ou pelo botão "fazer backup agora".
"""
import os
import shutil
import subprocess
from pathlib import Path

from api.config import (BACKUP_ATRASO_HORAS, BACKUP_DIR, BACKUP_DIRS_EXTRA, BACKUP_RETENCAO, DB_CONFIG, LOJA_ID,
                        PG_DUMP)
from api.database import agora

_PREFIXO = "pizzaria_"


def _podar(pasta: Path) -> None:
    arquivos = sorted(pasta.glob(f"{_PREFIXO}*.dump"), key=lambda p: p.name, reverse=True)
    for antigo in arquivos[BACKUP_RETENCAO:]:
        try:
            antigo.unlink()
        except OSError:
            pass


def fazer_backup(conn, acionado_por: str) -> dict:
    inicio = agora()
    nome = f"{_PREFIXO}{DB_CONFIG['dbname']}_{inicio.strftime('%Y%m%d_%H%M%S')}.dump"
    destino = Path(BACKUP_DIR)
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / nome
    sucesso, detalhe, copias_ok, copias_falha, tamanho = False, None, 0, 0, None
    env = dict(os.environ, PGPASSWORD=DB_CONFIG["password"])
    try:
        r = subprocess.run([PG_DUMP, "-Fc", "-h", str(DB_CONFIG["host"]), "-p", str(DB_CONFIG["port"]),
                            "-U", DB_CONFIG["user"], "-d", DB_CONFIG["dbname"], "-f", str(caminho)],
                           env=env, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            detalhe = "pg_dump falhou: " + (r.stderr.strip().splitlines() or ["sem detalhe"])[-1][:300]
        else:
            sucesso, tamanho = True, caminho.stat().st_size
            _podar(destino)
            for extra in BACKUP_DIRS_EXTRA:
                try:
                    pasta = Path(extra.strip())
                    pasta.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(caminho, pasta / nome)
                    _podar(pasta)
                    copias_ok += 1
                except OSError as e:
                    copias_falha += 1
                    detalhe = ((detalhe + "; ") if detalhe else "") + f"cópia para {extra.strip()} falhou: {e.strerror or e}"
    except FileNotFoundError:
        detalhe = "pg_dump não encontrado: defina PG_DUMP_PATH."
    except subprocess.TimeoutExpired:
        detalhe = "pg_dump excedeu o tempo limite."
    conn.execute(
        "INSERT INTO backup_registro (loja_id, iniciado_em, concluido_em, sucesso, arquivo, tamanho_bytes, copias_ok, "
        "copias_falha, detalhe, acionado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (LOJA_ID, inicio, agora(), sucesso, nome if sucesso else None, tamanho, copias_ok, copias_falha, detalhe,
         acionado_por))
    conn.commit()
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
