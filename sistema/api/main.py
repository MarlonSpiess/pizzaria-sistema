"""Aplicação FastAPI: API em /api, telas na mesma origem (sem CORS). Rotas de API são registradas antes das telas."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.config import DB_CONFIG, DOCS_ENABLED
from api.database import pool
from api.routers import auditoria, auth, parametros, sistema, usuarios

log = logging.getLogger("pizzaria")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
LIMITE_CORPO = 1_000_000  # 1 MB basta para qualquer pedido da loja


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="Sistema Integrado da Pizzaria", lifespan=lifespan,
              docs_url="/docs" if DOCS_ENABLED else None, redoc_url=None,
              openapi_url="/openapi.json" if DOCS_ENABLED else None)
app.add_middleware(GZipMiddleware, minimum_size=1024)

_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def cabecalhos_e_limite(request: Request, call_next):
    tamanho = request.headers.get("content-length")
    if tamanho and tamanho.isdigit() and int(tamanho) > LIMITE_CORPO:
        return JSONResponse(status_code=413, content={"detail": "Corpo da requisição grande demais."})
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = _CSP
    if request.url.path.startswith("/api") or request.url.path in ("/", "/health"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(RequestValidationError)
async def _validacao(request: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        campo = ".".join(str(x) for x in e["loc"] if x not in ("body", "query", "path"))
        msg = e["msg"].removeprefix("Value error, ")
        msgs.append(f"{campo}: {msg}" if campo else msg)
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs) or "Dados inválidos."})


@app.exception_handler(Exception)
async def _erro_geral(request: Request, exc: Exception):
    log.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno. Tente novamente; se persistir, avise o administrador."})


@app.get("/health")
def health():
    """200 se o servidor e o banco respondem. Sem dado sensível na resposta."""
    try:
        with psycopg.connect(host=DB_CONFIG["host"], port=DB_CONFIG["port"], dbname=DB_CONFIG["dbname"],
                             user=DB_CONFIG["user"], password=DB_CONFIG["password"], connect_timeout=3) as c:
            c.execute("SELECT 1")
        return {"status": "ok"}
    except psycopg.Error:
        return JSONResponse(status_code=503, content={"status": "db_indisponivel"})


for r in (auth.router, usuarios.router, parametros.router, auditoria.router, sistema.router):
    app.include_router(r, prefix="/api")


@app.api_route("/api/{caminho:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def _api_inexistente(caminho: str):
    raise HTTPException(status_code=404, detail="Rota não encontrada.")


app.mount("/static", StaticFiles(directory=FRONTEND / "static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONTEND / "app.html")
