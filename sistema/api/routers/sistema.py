from fastapi import APIRouter, Depends

from api.database import get_db
from api.security import requer
from api.services import backup

router = APIRouter(prefix="/sistema", tags=["sistema"])


@router.get("/backup")
def situacao_backup(sessao=Depends(requer("sistema.backup.ver")), conn=Depends(get_db)):
    return backup.situacao(conn)


@router.post("/backup")
def rodar_backup(sessao=Depends(requer("sistema.backup.rodar")), conn=Depends(get_db)):
    return backup.fazer_backup(conn, sessao["usuario"])
