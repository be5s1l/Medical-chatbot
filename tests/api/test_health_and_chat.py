import os
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    # Ensure tests don't accidentally require real keys.
    os.environ.setdefault("GROQ_API_KEY", "test")
    os.environ.setdefault("GROQ_MODEL", "llama-3.3-70b-versatile")
    # Reload settings after env is set (Settings reads env at import time).
    import src.core.config as config_mod

    importlib.reload(config_mod)
    import app.main as main_mod

    importlib.reload(main_mod)
    return TestClient(main_mod.create_app())


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_returns_strict_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    # Stub GroqService to keep tests offline.
    from app.services import groq_service as groq_mod

    async def fake_analyze(self, *, user_input: str):
        return {
            "summary": "Summary.",
            "possible_causes": ["Possible cause 1"],
            "advice": "Advice.",
            "urgency": "low",
        }

    monkeypatch.setattr(groq_mod.GroqService, "analyze", fake_analyze)

    r = client.post("/chat", json={"query": "I have a headache"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"summary", "possible_causes", "advice", "urgency"}
    assert body["urgency"] in {"low", "medium", "high"}

