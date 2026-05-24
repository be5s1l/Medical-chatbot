from __future__ import annotations

import src.core.logger  # noqa: F401 — configure loguru on import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from src.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Medical Assistant API",
        description="General health information only — not a diagnostic tool.",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "gemini_configured": bool(settings.gemini_api_key),
            "gemini_model": settings.gemini_model,
        }

    return app


app = create_app()

