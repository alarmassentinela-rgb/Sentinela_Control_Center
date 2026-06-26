# -*- coding: utf-8 -*-
"""COC Gateway (BFF) — base Sprint 0.

Expone health/observabilidad y la base de la API `/v1`. La identidad (OTP WhatsApp,
JWT), la agregación y el handshake con Odoo (`sentinela_api`) se agregan en WS-5.
OpenAPI/Swagger en /docs (WS-8).
"""
import uuid

import structlog
from fastapi import FastAPI, Request

from .config import settings
from .logging_setup import configure_logging, bind_request_id

configure_logging(settings.log_level)
log = structlog.get_logger("coc.gateway")

app = FastAPI(
    title="COC Sentinela — Gateway API",
    version="0.1.0",
    description=(
        "Backend-for-Frontend del Centro de Operaciones del Cliente. "
        "Identidad/OTP/JWT, agregación y orquestación sobre sentinela_api (Odoo). "
        "Odoo es la fuente de verdad; el gateway nunca sustituye las record rules de Odoo."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    bind_request_id(rid)
    log.info("request.start", method=request.method, path=request.url.path)
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    log.info("request.end", status=response.status_code, path=request.url.path)
    return response


@app.get("/health", tags=["infra"], summary="Liveness")
async def health():
    return {"status": "ok", "service": "coc-gateway", "version": app.version}


@app.get("/readyz", tags=["infra"], summary="Readiness")
async def readyz():
    # WS-5/WS-8: verificar conexión a Odoo (sentinela_api) y a la DB del gateway.
    return {"status": "ready"}


# WS-5: routers de /v1/auth/* y passthrough /v1/me se montan aquí.
# WS-8: /metrics (prometheus) se monta aquí.
