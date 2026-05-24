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


class _FakeLLMService:
    """Offline stub; avoids constructing ChatGoogleGenerativeAI in tests."""

    async def analyze_input(self, user_text: str):
        return {"symptoms": ["headache"], "duration": "1 day", "has_enough_info": True}

    async def generate_response(self, session, is_final: bool):
        from app.models.schemas import ChatResponseData, Urgency

        return ChatResponseData(
            message="Based on your symptoms, please consult a doctor.",
            risk_level=Urgency.medium,
            follow_up_questions=[],
            structured=None,
        )


def test_chat_returns_api_response_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Stub LLMService so the test runs fully offline."""
    import app.routers.chat as chat_mod

    monkeypatch.setattr(chat_mod, "get_llm_service", lambda: _FakeLLMService())

    r = client.post("/api/v1/chat", json={"session_id": "test-123", "message": "I have a headache"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body["data"]
    assert "risk_level" in body["data"]


class _QuotaExhaustedLLMService(_FakeLLMService):
    async def analyze_input(self, user_text: str):
        from app.services.gemini_quota import QuotaExceededError

        raise QuotaExceededError(operation="analyze_input")


def test_chat_quota_exceeded_returns_structured_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Quota errors must surface completed/remaining steps and a resume point."""
    import app.routers.chat as chat_mod

    monkeypatch.setattr(chat_mod, "get_llm_service", lambda: _QuotaExhaustedLLMService())

    r = client.post("/api/v1/chat", json={"session_id": "quota-test", "message": "I have a headache"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "QUOTA_EXCEEDED"
    assert "QUOTA LIMIT REACHED" in body["error"]["message"]
    assert "User message stored in session" in body["error"]["message"]
    assert "analyze_input" in body["error"]["message"]
