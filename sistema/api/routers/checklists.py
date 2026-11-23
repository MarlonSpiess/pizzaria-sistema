"""Checklists (melhoria M4): início, acompanhamento e fim do dia por função, pendências, aderência e pontos de controle do pedido."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.config import LOJA_ID
from api.database import get_db, hoje
from api.schemas import ControlePedidoIn, ExecucaoIn, NovaVersaoChecklistIn, ResolverPendenciaIn, RespostaChecklistIn
from api.security import requer, requer_alguma
from api.services import checklists as svc

router = APIRouter(prefix="/checklists", tags=["checklists"])


@router.get("/hoje")
def do_dia(sessao=Depends(requer("checklist.executar")), conn=Depends(get_db)):
    """Checklists do dia que têm item para a função de quem pergunta, com as execuções e o andamento de cada uma."""
    return svc.hoje_do_perfil(conn, sessao, LOJA_ID, hoje())


@router.post("/execucoes", status_code=201)
def iniciar(d: ExecucaoIn, response: Response, sessao=Depends(requer("checklist.executar")), conn=Depends(get_db)):
    r = svc.iniciar(conn, sessao, LOJA_ID, d.modelo, d.turno, hoje())
    if not r["criada"]:
        response.status_code = 200  # devolveu a execução que já existia
    return r


@router.get("/execucoes/{exec_id}")
def detalhe(exec_id: int, sessao=Depends(requer("checklist.executar")), conn=Depends(get_db)):
    return svc.detalhe(conn, sessao, LOJA_ID, exec_id)


@router.put("/execucoes/{exec_id}/itens/{item_id}")
def responder(exec_id: int, item_id: int, d: RespostaChecklistIn, sessao=Depends(requer("checklist.executar")), conn=Depends(get_db)):
    return svc.responder(conn, sessao, LOJA_ID, exec_id, item_id, d)


@router.post("/execucoes/{exec_id}/concluir")
def concluir(exec_id: int, sessao=Depends(requer("checklist.resolver")), conn=Depends(get_db)):
    """Concluir a execução inteira é da gerência: cada função responde os itens dela, a gerência confere e fecha."""
    return svc.concluir(conn, sessao, LOJA_ID, exec_id)


@router.get("/pendencias")
def pendencias(todas: bool = Query(default=False), sessao=Depends(requer("checklist.ver")), conn=Depends(get_db)):
    return svc.pendencias(conn, LOJA_ID, so_abertas=not todas)


@router.post("/pendencias/{pid}/resolver")
def resolver(pid: int, d: ResolverPendenciaIn, sessao=Depends(requer("checklist.resolver")), conn=Depends(get_db)):
    return svc.resolver_pendencia(conn, sessao, LOJA_ID, pid, d.resolucao)


@router.get("/aderencia")
def aderencia(de: Optional[date] = Query(default=None), ate: Optional[date] = Query(default=None),
              sessao=Depends(requer("checklist.ver")), conn=Depends(get_db)):
    fim = ate or hoje()
    ini = de or fim - timedelta(days=6)
    if ini > fim:
        raise HTTPException(status_code=400, detail="A data inicial não pode ser depois da final.")
    if (fim - ini).days > 92:
        raise HTTPException(status_code=400, detail="Escolha um período de até 93 dias.")
    return svc.aderencia(conn, LOJA_ID, ini, fim)


@router.get("/modelos")
def modelos(sessao=Depends(requer("checklist.gerir")), conn=Depends(get_db)):
    return svc.listar_modelos(conn, LOJA_ID)


@router.post("/modelos/padrao", status_code=201)
def instalar_padrao(sessao=Depends(requer("checklist.gerir")), conn=Depends(get_db)):
    """Instala os três modelos padrão que a loja ainda não tem. Pode repetir sem efeito."""
    return {"instalados": svc.instalar_padrao(conn, sessao, LOJA_ID)}


@router.post("/modelos/{codigo}/versoes", status_code=201)
def nova_versao(codigo: str, d: NovaVersaoChecklistIn, sessao=Depends(requer("checklist.gerir")), conn=Depends(get_db)):
    return svc.nova_versao(conn, sessao, LOJA_ID, codigo, [i.model_dump() for i in d.itens])


@router.post("/pedidos/{pedido_id}/controles", status_code=201)
def controle(pedido_id: int, d: ControlePedidoIn,
             sessao=Depends(requer_alguma("vendas.criar", "entregas.despachar", "vendas.gerir")), conn=Depends(get_db)):
    """Pontos de controle do pedido: leitura de volta (atendente), conferência final (acabamento) e causa do atraso (gerência)."""
    return svc.registrar_controle(conn, sessao, LOJA_ID, pedido_id, d.ponto, d.ok, d.texto)


@router.get("/pedidos/{pedido_id}/controles")
def controles(pedido_id: int, sessao=Depends(requer_alguma("vendas.ver", "entregas.despachar")), conn=Depends(get_db)):
    return svc.controles_do_pedido(conn, LOJA_ID, pedido_id)
