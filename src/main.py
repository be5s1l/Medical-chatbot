import src.core.logger  # noqa: F401 — configure loguru on import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes.chat import router as chat_router
from src.routes.upload import router as upload_router
from src.routes.vitals import router as vitals_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Medical Chatbot API",
        description="Triage assistant — not a diagnostic tool",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(upload_router)
    app.include_router(vitals_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

