"""
CyberSentinel AI — FastAPI application entrypoint.

Run locally (after `pip install -r backend/requirements.txt`):
    uvicorn app.main:app --reload --app-dir backend

This file could not be started in the development sandbox (fastapi/uvicorn
are not installed there and there is no network to install them) — it is
written to FastAPI's current API and `uvicorn app.main:app --app-dir backend`
should be the first command run against it locally.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import documents, events, incidents, metrics
from app.core.config import get_settings
from app.db.session import init_db

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agentic network security investigation & response platform (portfolio project).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Basic in-memory per-IP rate limiting -----------------------------------
# Adequate for a single-process demo deployment; a real multi-instance
# deployment would move this to Redis. Documented as a known limitation.
_request_log: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    _request_log[client_ip] = [t for t in _request_log[client_ip] if now - t < window]

    if len(_request_log[client_ip]) >= settings.rate_limit_per_minute:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})

    _request_log[client_ip].append(now)
    return await call_next(request)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(events.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs"}
