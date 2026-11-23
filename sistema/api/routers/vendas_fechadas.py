"""Fechar vendas por ingrediente: a gerência marca o ingrediente em falta e o sistema fecha os sabores que o usam."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import LOJA_ID
from api.database import auditar, get_db
from api.schemas import Base
from api.security import requer
from api.services import ingredientes as svc

router = APIRouter(prefix="/vendas-fechadas", tags=["vendas-fechadas"])


class FaltaIn(Base):
    em_falta: bool


def _item(conn, item_id: int, so_ativo: bool = True) -> dict:
    i = conn.execute("SELECT id, nome, classe FROM item WHERE id = %s AND loja_id = %s" + (" AND ativo" if so_ativo else ""), (item_id, LOJA_ID)).fetchone()
    if not i:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    return i


@router.get("/ingredientes")
def ingredientes(busca: Optional[str] = Query(default=None, max_length=60), sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    """Itens que alguma ficha usa (para achar 'Ovo'), com a marca de em falta."""
    filtro, params = "", [LOJA_ID]
    if busca and busca.strip():
        filtro, params = " AND i.nome ILIKE %s", [LOJA_ID, "%" + busca.strip().replace("%", "").replace("_", "").replace("\\", "") + "%"]
    return conn.execute(
        "SELECT i.id, i.nome, i.classe, EXISTS (SELECT 1 FROM ingrediente_em_falta f WHERE f.item_id = i.id AND f.reaberto_em IS NULL) AS em_falta "
        f"FROM item i WHERE i.loja_id = %s AND i.ativo AND i.classe IN ('insumo','preparo','revenda'){filtro} "
        "AND EXISTS (SELECT 1 FROM ficha_linha fl WHERE fl.item_id = i.id) ORDER BY i.nome LIMIT 100", params).fetchall()


@router.get("/ingredientes/{item_id}/sabores")
def sabores(item_id: int, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    """Antes de marcar: quais sabores fecham (para a gerência conferir)."""
    i = _item(conn, item_id)
    return {"ingrediente": i["nome"], "sabores": svc.sabores_que_usam(conn, [item_id])}


@router.put("/ingredientes/{item_id}/falta")
def falta(item_id: int, d: FaltaIn, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    i = _item(conn, item_id, so_ativo=d.em_falta)  # item desativado ainda pode ser reaberto
    if d.em_falta and not conn.execute("SELECT 1 FROM ficha_linha WHERE item_id = %s LIMIT 1", (item_id,)).fetchone():
        raise HTTPException(status_code=400, detail="Nenhuma ficha usa este item.")
    mudou = svc.marcar_falta(conn, item_id, d.em_falta, sessao["usuario_id"])
    afetados = svc.sabores_que_usam(conn, [item_id])
    if mudou:
        auditar(conn, sessao, "falta" if d.em_falta else "reabrir", "ingrediente_em_falta", item_id,
                depois={"ingrediente": i["nome"], "em_falta": d.em_falta, "sabores": [s["nome"] for s in afetados]})
    conn.commit()
    return {"ingrediente": i["nome"], "em_falta": d.em_falta, "sabores": afetados, "mudou": mudou}


@router.get("")
def fechadas(sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    """Sabores com a venda fechada agora e o motivo, mais o ingrediente em falta."""
    fech = svc.produtos_fechados(conn)
    prods = conn.execute("SELECT id, nome, tipo FROM produto WHERE loja_id = %s AND id = ANY(%s) ORDER BY nome", (LOJA_ID, list(fech))).fetchall() if fech else []
    return {"ingredientes_em_falta": svc.ingredientes_em_falta(conn),
            "sabores_fechados": [{**p, "motivo": ", ".join(fech[p["id"]])} for p in prods]}
