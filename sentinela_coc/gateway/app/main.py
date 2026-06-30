# -*- coding: utf-8 -*-
"""COC Gateway (BFF). Health/observabilidad + autenticación (OTP + sesiones cortas).

La identidad vive aquí; la autorización en Odoo (record rules) vía sesión efímera.
OpenAPI/Swagger en /docs.
"""
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registra modelos en Base)
from .config import settings
from .db import Base, engine
from .logging_setup import bind_request_id, configure_logging
from .routers import auth as auth_router
from .routers import devices as devices_router
from .routers import ledger as ledger_router
from .routers import magic as magic_router
from .routers import payments as payments_router
from .routers import payments_webhook as payments_webhook_router
from .routers import portal as portal_router
from .routers import providers as providers_router
from .routers import sessions as sessions_router

configure_logging(settings.log_level)
log = structlog.get_logger("coc.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        log.info("db_ready")
    except Exception as e:  # en pruebas se usa un engine de test (override)
        log.warning("db_init_skipped", error=str(e))
    yield


app = FastAPI(
    title="COC Sentinela — Gateway API",
    version="0.4.0",
    description=(
        "Backend-for-Frontend del Centro de Operaciones del Cliente. Identidad "
        "(OTP + sesiones cortas) en el gateway; autorización en Odoo (record rules)."
    ),
    docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,  # autenticación por Bearer, no por cookies
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    expose_headers=["X-Request-Id"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request.state.request_id = rid
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
    return {"status": "ready"}


app.include_router(auth_router.router)
app.include_router(sessions_router.router)
app.include_router(devices_router.router)
app.include_router(magic_router.public)
app.include_router(magic_router.internal)
app.include_router(providers_router.router)
app.include_router(portal_router.router)
app.include_router(ledger_router.router)
app.include_router(payments_router.router)
app.include_router(payments_webhook_router.router)
