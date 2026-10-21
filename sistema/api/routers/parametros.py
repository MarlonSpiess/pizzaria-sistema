from fastapi import APIRouter, Depends

from api.config import LOJA_ID
from api.database import agora, auditar, get_db
from api.schemas import ParametroIn
from api.security import requer
from api.services import parametros as svc

router = APIRouter(prefix="/parametros", tags=["parametros"])


@router.get("")
def listar(sessao=Depends(requer("parametros.ver")), conn=Depends(get_db)):
    return list(svc.vigentes(conn, LOJA_ID).values())


@router.put("/{chave}")
def definir(chave: str, dados: ParametroIn, sessao=Depends(requer("parametros.editar")), conn=Depends(get_db)):
    texto = svc.normalizar(chave, dados.valor)
    antes = svc.vigentes(conn, LOJA_ID)[chave]["valor"]
    conn.execute("INSERT INTO parametro (loja_id, chave, valor, vigente_desde, criado_por) VALUES (%s, %s, %s, %s, %s)",
                 (LOJA_ID, chave, texto, agora(), sessao["usuario_id"]))
    depois = svc.vigentes(conn, LOJA_ID)[chave]["valor"]
    auditar(conn, sessao, "definir", "parametro", chave, antes={"valor": antes}, depois={"valor": depois})
    conn.commit()
    return svc.vigentes(conn, LOJA_ID)[chave]


@router.get("/{chave}/historico")
def historico(chave: str, sessao=Depends(requer("parametros.ver")), conn=Depends(get_db)):
    svc.normalizar(chave, None)  # valida a chave (404 se desconhecida)
    return conn.execute("SELECT p.valor, p.vigente_desde, u.usuario AS alterado_por FROM parametro p "
                        "LEFT JOIN usuario u ON u.id = p.criado_por WHERE p.loja_id = %s AND p.chave = %s "
                        "ORDER BY p.id DESC LIMIT 100", (LOJA_ID, chave)).fetchall()
