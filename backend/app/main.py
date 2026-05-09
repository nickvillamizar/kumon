# app/main.py
"""
app/main.py
Entrypoint de la aplicación FastAPI.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.routes import upload, jobs, results, cuestionario, dashboard
from app.routes import estudiantes, profesores, notas, horarios
from app.services.ocr_service import initialize_ocr_reader
import ssl
import certifi

ssl._create_default_https_context = ssl._create_unverified_context

# ================================================================
# LOGGING
# ================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ================================================================
# CORS
# ================================================================
_base_origins: list[str] = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://localhost:8080",
]
_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
_extra_origins: list[str] = [o.strip() for o in _extra.split(",") if o.strip()]
ALLOWED_ORIGINS: list[str] = _base_origins + _extra_origins

# ================================================================
# LIFESPAN
# ================================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("── Startup ─────────────────────────────────────────────────")
    logger.info("Inicializando EasyOCR reader…")
    initialize_ocr_reader()
    logger.info("EasyOCR listo.")
    logger.info("Origins CORS permitidos: %s", ALLOWED_ORIGINS)
    logger.info("────────────────────────────────────────────────────────")
    yield
    logger.info("── Shutdown ───────────────────────────────────────────────")
    logger.info("Aplicación detenida limpiamente.")
    logger.info("────────────────────────────────────────────────────────")

# ================================================================
# APLICACIÓN FASTAPI
# ================================================================
app = FastAPI(
    title="Automatización Kumon",
    description=(
        "API de procesamiento de pruebas diagnósticas Kumon. "
        "Sube un video, extrae métricas cuantitativas y cualitativas, "
        "calcula el semáforo de aprendizaje y genera el boletín PDF."
    ),
    version="0.1.0",
    contact={"name": "Camilo Rubio", "email": "soporte@kumon-automatizacion.local"},
    lifespan=lifespan,
)

# ================================================================
# MIDDLEWARE
# ================================================================
_trusted_hosts_env = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1")
_trusted_hosts: list[str] = [
    h.strip() for h in _trusted_hosts_env.split(",") if h.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ================================================================
# ROUTERS
# ================================================================
app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(results.router)
app.include_router(cuestionario.router)
app.include_router(dashboard.router)
app.include_router(estudiantes.router)
app.include_router(profesores.router)
app.include_router(notas.router)
app.include_router(horarios.router)

# ================================================================
# HEALTH CHECK
# ================================================================
@app.get("/health", tags=["infra"], include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "version": app.version}
