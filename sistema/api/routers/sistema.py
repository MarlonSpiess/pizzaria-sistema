from fastapi import APIRouter, Depends

from api.database import auditar, get_db
from api.security import requer
from api.services import backup

router = APIRouter(prefix="/sistema", tags=["sistema"])


@router.get("/backup")
def situacao_backup(sessao=Depends(requer("sistema.backup.ver")), conn=Depends(get_db)):
    return backup.situacao(conn)


@router.post("/backup")
def rodar_backup(sessao=Depends(requer("sistema.backup.rodar")), conn=Depends(get_db)):
    conn.rollback()  # encerra a transação do request antes do dump longo; o backup usa conexão própria
    resultado = backup.fazer_backup(sessao["usuario"])
    auditar(conn, sessao, "backup_manual", "backup", resultado["arquivo"], depois={"sucesso": resultado["sucesso"]})
    conn.commit()
    return resultado
