"""
Compatibility entrypoint for `uvicorn src.main:app`.

The production-ready implementation now lives under `app/main.py` using the
target structure: app/routers, app/services, app/models.
"""

from app.main import app  # noqa: F401

