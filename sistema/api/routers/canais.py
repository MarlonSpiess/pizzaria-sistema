"""Canais de venda: cadastro, fila de entrada e mapa de produtos. Estrutura apenas, sem chamada externa."""
from fastapi import APIRouter, Depends, HTTPException

from api.config import LOJA_ID
from api.database import agora, auditar, get_db, transacao
from api.schemas import Base
from api.security import requer

router = APIRouter(prefix="/canais", tags=["canais"])
PADRAO = (("anotaai", "Anota Ai"), ("ifood", "iFood"))


class MapaIn(Base):
    produto_id: int
    id_externo: str


class AtivoIn(Base):
    ativo: bool


class RecusaIn(Base):
    motivo: str


def _texto(v: str, maximo: int = 120) -> str:
    v = (v or "").strip()
    if not v or len(v) > maximo:
        raise HTTPException(status_code=422, detail=f"Texto obrigatório, até {maximo} caracteres.")
    return v


def _canal(conn, cid: int) -> dict:
    c = conn.execute("SELECT id, codigo, nome, ativo, aceitar_sozinho FROM canal_venda WHERE id = %s AND loja_id = %s", (cid, LOJA_ID)).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Canal não encontrado.")
    return c


@router.get("")
def listar(sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    for codigo, nome in PADRAO:
        conn.execute("INSERT INTO canal_venda (loja_id, codigo, nome) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (LOJA_ID, codigo, nome))
    conn.commit()
    return conn.execute(
        "SELECT c.id, c.codigo, c.nome, c.ativo, c.aceitar_sozinho, "
        "(SELECT count(*) FROM entrada_canal e WHERE e.canal_id = c.id AND e.situacao = 'pendente') AS pendentes, "
        "(SELECT count(*) FROM mapa_produto_canal m WHERE m.canal_id = c.id) AS produtos_mapeados "
        "FROM canal_venda c WHERE c.loja_id = %s ORDER BY c.id", (LOJA_ID,)).fetchall()


@router.get("/loja")
def estado_loja(sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    r = conn.execute("SELECT loja_aberta, loja_aberta_desde FROM loja WHERE id = %s", (LOJA_ID,)).fetchone()
    return {"loja_aberta": bool(r and r["loja_aberta"]), "desde": r["loja_aberta_desde"] if r else None}


@router.patch("/loja")
def definir_loja(d: AtivoIn, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    """Flag manual da gerência: liga quando a loja já pode receber pedidos dos canais; desliga ao fechar. Não muda sozinha."""
    r = conn.execute("SELECT loja_aberta FROM loja WHERE id = %s FOR UPDATE", (LOJA_ID,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Loja não encontrada.")
    if r["loja_aberta"] == d.ativo:  # nada mudou: não regrava a hora da última troca
        conn.rollback()
        return {"loja_aberta": d.ativo, "desde": conn.execute("SELECT loja_aberta_desde FROM loja WHERE id = %s", (LOJA_ID,)).fetchone()["loja_aberta_desde"]}
    quando = agora()
    conn.execute("UPDATE loja SET loja_aberta = %s, loja_aberta_desde = %s WHERE id = %s", (d.ativo, quando, LOJA_ID))
    auditar(conn, sessao, "loja_aberta", "loja", LOJA_ID, antes={"loja_aberta": r["loja_aberta"]}, depois={"loja_aberta": d.ativo})
    conn.commit()
    return {"loja_aberta": d.ativo, "desde": quando}


@router.patch("/{cid}/ativo")
def ativar(cid: int, d: AtivoIn, sessao=Depends(requer("canais.configurar")), conn=Depends(get_db)):
    ativo = d.ativo
    c = _canal(conn, cid)
    conn.execute("UPDATE canal_venda SET ativo = %s WHERE id = %s AND loja_id = %s", (ativo, cid, LOJA_ID))
    auditar(conn, sessao, "ativar" if ativo else "desativar", "canal_venda", cid, antes={"ativo": c["ativo"]}, depois={"ativo": ativo})
    conn.commit()
    return {**c, "ativo": ativo}


@router.patch("/{cid}/aceitar-sozinho")
def aceitar_sozinho(cid: int, d: AtivoIn, sessao=Depends(requer("canais.configurar")), conn=Depends(get_db)):
    """Liga ou desliga o aceite automático do canal. Desligado, a gerência aceita cada pedido explicitamente."""
    c = conn.execute("SELECT id, aceitar_sozinho FROM canal_venda WHERE id = %s AND loja_id = %s FOR UPDATE", (cid, LOJA_ID)).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Canal não encontrado.")
    conn.execute("UPDATE canal_venda SET aceitar_sozinho = %s WHERE id = %s AND loja_id = %s", (d.ativo, cid, LOJA_ID))
    auditar(conn, sessao, "aceitar_sozinho", "canal_venda", cid, antes={"aceitar_sozinho": c["aceitar_sozinho"]}, depois={"aceitar_sozinho": d.ativo})
    conn.commit()
    return {"id": cid, "aceitar_sozinho": d.ativo}


@router.get("/{cid}/fila")
def fila(cid: int, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    _canal(conn, cid)
    return conn.execute("SELECT id, id_externo, situacao, motivo, recebido_em, pedido_id FROM entrada_canal WHERE canal_id = %s AND loja_id = %s ORDER BY id DESC LIMIT 100", (cid, LOJA_ID)).fetchall()


@router.post("/fila/{eid}/recusar")
def recusar(eid: int, d: RecusaIn, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    motivo = _texto(d.motivo, 200)
    e = conn.execute("SELECT id, situacao FROM entrada_canal WHERE id = %s AND loja_id = %s FOR UPDATE", (eid, LOJA_ID)).fetchone()
    if not e:
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")
    if e["situacao"] not in ("pendente", "bloqueada"):
        raise HTTPException(status_code=409, detail="Esta entrada já foi tratada ou está sendo importada.")
    conn.execute("UPDATE entrada_canal SET situacao = 'recusada', motivo = %s WHERE id = %s AND loja_id = %s", (motivo, eid, LOJA_ID))  # TODO API: avisar o canal da recusa
    auditar(conn, sessao, "recusar", "entrada_canal", eid, depois={"motivo": motivo})
    conn.commit()
    return {"id": eid, "situacao": "recusada", "motivo": motivo}


@router.post("/fila/{eid}/reprocessar")
def reprocessar(eid: int, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    """A gerência resolveu o impedimento (ex.: cardápio ou estoque): o pedido bloqueado volta para a fila de importação."""
    e = conn.execute("SELECT id, situacao FROM entrada_canal WHERE id = %s AND loja_id = %s FOR UPDATE", (eid, LOJA_ID)).fetchone()
    if not e:
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")
    if e["situacao"] != "bloqueada":
        raise HTTPException(status_code=409, detail="Só entrada bloqueada pode voltar para a fila.")
    conn.execute("UPDATE entrada_canal SET situacao = 'pendente', motivo = NULL, importacao_tentativas = 0 WHERE id = %s AND loja_id = %s", (eid, LOJA_ID))
    auditar(conn, sessao, "reprocessar", "entrada_canal", eid)
    conn.commit()
    return {"id": eid, "situacao": "pendente"}


@router.get("/{cid}/produtos")
def mapa(cid: int, sessao=Depends(requer("vendas.gerir")), conn=Depends(get_db)):
    _canal(conn, cid)
    return conn.execute(
        "SELECT p.id AS produto_id, p.nome, p.tipo, m.id_externo FROM produto p "
        "LEFT JOIN mapa_produto_canal m ON m.produto_id = p.id AND m.canal_id = %s "
        "WHERE p.loja_id = %s AND p.ativo ORDER BY p.tipo, p.nome", (cid, LOJA_ID)).fetchall()


@router.put("/{cid}/produtos")
def mapear(cid: int, d: MapaIn, sessao=Depends(requer("canais.configurar")), conn=Depends(get_db)):
    _canal(conn, cid)
    ext = _texto(d.id_externo, 80)
    if not conn.execute("SELECT 1 FROM produto WHERE id = %s AND loja_id = %s AND ativo", (d.produto_id, LOJA_ID)).fetchone():
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    with transacao(conn):
        conn.execute("INSERT INTO mapa_produto_canal (canal_id, produto_id, id_externo) VALUES (%s,%s,%s) "
                     "ON CONFLICT (canal_id, produto_id) DO UPDATE SET id_externo = EXCLUDED.id_externo, "
                     "pausado_no_canal = CASE WHEN mapa_produto_canal.id_externo = EXCLUDED.id_externo THEN mapa_produto_canal.pausado_no_canal ELSE false END", (cid, d.produto_id, ext))
        auditar(conn, sessao, "mapear", "mapa_produto_canal", d.produto_id, depois={"canal_id": cid, "id_externo": ext})
    return {"produto_id": d.produto_id, "id_externo": ext}
