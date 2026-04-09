import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock

from src.domain.entities.triage import TriageLevel, TriageResult
from src.main import app
from src.routes import chat as chat_routes


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_returns_200():
    fake = TriageResult(
        level=TriageLevel.NON_URGENT,
        conditions=["headache"],
        response_text="Advice text.\n\n---\nIMPORTANT: disclaimer",
        source="Test",
    )
    mock_c = MagicMock()
    mock_c.process.return_value = fake
    prev = chat_routes.symptom_controller
    chat_routes.symptom_controller = mock_c
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/chat", json={"query": "I have a headache"})
    finally:
        chat_routes.symptom_controller = prev
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_chat_rejects_short_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"query": "ab"})
    assert response.status_code == 422
