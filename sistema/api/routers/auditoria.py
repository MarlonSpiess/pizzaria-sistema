from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.config import LOJA_ID
from api.database import get_db
from api.security import requer

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("")
def listar(entidade: Optional[str] = Query(default=None, max_length=40), limite: int = Query(default=100, ge=1, le=500),
           deslocamento: int = Query(default=0, ge=0, le=1_000_000), sessao=Depends(requer("auditoria.ver")), conn=Depends(get_db)):
    filtro, params = "", [LOJA_ID]
    if entidade:
        filtro, params = " AND entidade = %s", [LOJA_ID, entidade]
    total = conn.execute(f"SELECT count(*) AS n FROM auditoria WHERE loja_id = %s{filtro}", params).fetchone()["n"]
    dados = conn.execute(
        "SELECT id, quando, usuario, acao, entidade, entidade_id, antes, depois FROM auditoria "
        f"WHERE loja_id = %s{filtro} ORDER BY id DESC LIMIT %s OFFSET %s", (*params, limite, deslocamento)).fetchall()
    return {"data": dados, "total": total, "limit": limite, "offset": deslocamento}
