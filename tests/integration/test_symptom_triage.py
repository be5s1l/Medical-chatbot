from unittest.mock import MagicMock, patch

from src.controllers.symptom_triage import SymptomTriageController
from src.domain.entities.triage import TriageLevel


@patch("src.controllers.symptom_triage.MedicalRAGChain")
@patch("src.controllers.symptom_triage.BioBERTService")
def test_emergency_bypasses_rag(MockNLP, MockRAG):
    controller = SymptomTriageController()
    result = controller.process("I have chest pain and cannot breathe")
    assert result.level == TriageLevel.EMERGENCY
    MockRAG.return_value.query.assert_not_called()
    MockNLP.return_value.extract_symptoms.assert_not_called()


@patch("src.controllers.symptom_triage.MedicalRAGChain")
@patch("src.controllers.symptom_triage.BioBERTService")
def test_normal_query_calls_rag(MockNLP, MockRAG):
    MockRAG.return_value.query = MagicMock(return_value="General advice response")
    MockNLP.return_value.extract_symptoms = MagicMock(return_value=[])
    controller = SymptomTriageController()
    result = controller.process("I have a slight cough")
    MockRAG.return_value.query.assert_called_once()
    assert "IMPORTANT" in result.response_text or "does NOT diagnose" in result.response_text
