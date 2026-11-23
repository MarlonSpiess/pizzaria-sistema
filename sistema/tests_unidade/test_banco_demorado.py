"""Consulta além do statement_timeout: 504 sem Retry-After (repetir daria o mesmo), não 503 "tente novamente"."""
import psycopg
from fastapi.testclient import TestClient

from api.main import app


def _rota_que_estoura():
    raise psycopg.errors.QueryCanceled("canceling statement due to statement timeout")


def test_consulta_demorada_responde_504_sem_pedir_repeticao():
    app.add_api_route("/api/_teste_demorada", _rota_que_estoura, methods=["GET"])
    app.router.routes.insert(0, app.router.routes.pop())  # antes da rota que serve o frontend
    try:
        r = TestClient(app).get("/api/_teste_demorada")
    finally:
        app.router.routes = [x for x in app.router.routes if getattr(x, "path", "") != "/api/_teste_demorada"]
    assert r.status_code == 504
    assert "retry-after" not in r.headers
    assert "demorou demais" in r.json()["detail"]
