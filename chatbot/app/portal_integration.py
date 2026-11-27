"""Acrescenta o portal ao FastAPI RAG já existente sem mudar endpoints do chatbot.
A página original do WhatsApp usa /portal/. A UI do RAG continua servida em /.
"""
import os
import logging
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

LOG = logging.getLogger(__name__)
PORTAL_DIR = Path(__file__).resolve().parent.parent / "portal_frontend"

def attach_portal(app: FastAPI) -> None:
    """Chamado uma vez a partir de app/main.py; sem tocar na UI do RAG."""
    if not (PORTAL_DIR / "index.html").is_file():
        raise RuntimeError(f"Portal não encontrado: {PORTAL_DIR}")

    @app.get("/portal-api/noticias", tags=["Portal"])
    def public_news(size: int = Query(default=30, ge=1, le=100),
                    sort: str = Query(default="publicadoEm,desc", max_length=80)):
        """Proxy de leitura, somente notícias: contorna CORS sem expor endpoints privados."""
        backend = os.getenv("CAOGUIA_BACKEND_URL", "http://127.0.0.1:8080").rstrip("/")
        try:
            result = requests.get(backend + "/api/noticias", params={"size": size,"sort": sort},timeout=7)
            result.raise_for_status()
            return JSONResponse(result.json())
        except (requests.ConnectionError, requests.Timeout):
            raise HTTPException(status_code=503,detail="Backend de notícias indisponível. Inicie o Spring Boot na porta 8080.")
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", 502)
            LOG.warning("Backend notícias respondeu HTTP %s", status)
            raise HTTPException(status_code=502,detail=f"Backend de notícias retornou HTTP {status}.")
        except ValueError:
            raise HTTPException(status_code=502,detail="Resposta inválida do backend de notícias.")

    app.mount("/portal", StaticFiles(directory=str(PORTAL_DIR), html=True),name="portal")
