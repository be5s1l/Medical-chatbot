from __future__ import annotations

import src.core.logger  # noqa: F401 — configure loguru on import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.image import router as image_router
from app.routers.lab import router as lab_router


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
    app.include_router(image_router)
    app.include_router(lab_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

