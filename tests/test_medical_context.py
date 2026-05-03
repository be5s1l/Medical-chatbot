import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_no_medical_context():
    """Scenario 1: No medical context -> normal chatbot behavior"""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test_no_context_001",
            "message": "I have a mild headache.",
            "type": "text"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

def test_chat_with_relevant_context():
    """Scenario 2: With relevant history (e.g. diabetes) -> smarter reasoning"""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test_relevant_context_001",
            "message": "I feel dizzy and a bit shaky.",
            "type": "text",
            "medical_context": {
                "conditions": ["Type 2 Diabetes"],
                "lab_results": ["Blood sugar 180 mg/dL"]
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

def test_chat_with_irrelevant_context():
    """Scenario 3: With irrelevant history -> ignored properly"""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test_irrelevant_context_001",
            "message": "I twisted my ankle playing soccer.",
            "type": "text",
            "medical_context": {
                "conditions": ["Mild dandruff"],
                "medications": ["Vitamin D supplement"]
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
