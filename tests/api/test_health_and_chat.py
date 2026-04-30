import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    # Ensure tests don't require a real Gemini key.
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    os.environ.setdefault("GEMINI_MODEL", "gemini-1.5-flash")

    import importlib
    import src.core.config as config_mod
    importlib.reload(config_mod)

    import app.main as main_mod
    importlib.reload(main_mod)
    return TestClient(main_mod.create_app())


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_returns_api_response_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Stub LLMService so the test runs fully offline."""
    from app.models.schemas import ChatResponseData, Urgency
    from app.services import llm_service as llm_mod

    async def fake_analyze(self, user_text: str):
        return {"symptoms": ["headache"], "duration": "1 day", "has_enough_info": True}

    async def fake_generate(self, session, is_final: bool):
        return ChatResponseData(
            message="Based on your symptoms, please consult a doctor.",
            risk_level=Urgency.medium,
            follow_up_questions=[],
            structured=None,
        )

    monkeypatch.setattr(llm_mod.LLMService, "analyze_input", fake_analyze)
    monkeypatch.setattr(llm_mod.LLMService, "generate_response", fake_generate)

    r = client.post("/api/v1/chat", json={"session_id": "test-123", "message": "I have a headache"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body["data"]
    assert "risk_level" in body["data"]
