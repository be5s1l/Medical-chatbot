from src.domain.entities.symptom import Severity
from src.infrastructure.nlp.biobert_service import BioBERTService


def test_extract_symptoms_returns_entities():
    service = BioBERTService()
    service._ner = lambda text: [
        {"word": "headache", "score": 0.95, "entity_group": "MISC"},
    ]
    symptoms = service.extract_symptoms("I have a headache")
    assert len(symptoms) == 1
    assert symptoms[0].name == "headache"


def test_severity_inferred_from_context():
    service = BioBERTService()
    service._ner = lambda text: [
        {"word": "pain", "score": 0.9, "entity_group": "MISC"},
    ]
    symptoms = service.extract_symptoms("I have severe crushing pain")
    assert symptoms[0].severity == Severity.SEVERE
