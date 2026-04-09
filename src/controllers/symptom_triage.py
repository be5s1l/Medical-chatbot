from loguru import logger

from src.core.constants import DEFAULT_DISCLAIMER
from src.domain.entities.triage import TriageLevel, TriageResult
from src.helpers.safety_layer import check_emergency, handle_emergency, inject_disclaimer
from src.infrastructure.llm.langchain_chain import MedicalRAGChain
from src.infrastructure.nlp.biobert_service import BioBERTService


class SymptomTriageController:
    def __init__(self) -> None:
        self.nlp = BioBERTService()
        self.rag = MedicalRAGChain()

    def process(self, query: str) -> TriageResult:
        logger.info("Processing query: {}", (query or "")[:100])
        if check_emergency(query):
            logger.warning("EMERGENCY detected in query")
            return handle_emergency(query)

        try:
            symptoms = self.nlp.extract_symptoms(query)
        except Exception as exc:
            logger.warning("NLP symptom extraction failed (continuing without entities): {}", exc)
            symptoms = []
        logger.debug("Extracted {} symptom entities", len(symptoms))

        raw_response = self.rag.query(query)
        safe_response = inject_disclaimer(raw_response)

        level = self._infer_triage_level(raw_response)
        return TriageResult(
            level=level,
            conditions=[s.name for s in symptoms],
            response_text=safe_response,
            source="RAG Knowledge Base",
            disclaimer=DEFAULT_DISCLAIMER,
        )

    def _infer_triage_level(self, raw: str) -> TriageLevel:
        t = (raw or "").lower()
        if "emergency" in t and ("call" in t or "911" in t or "immediate" in t):
            return TriageLevel.URGENT
        if "urgent" in t or "er " in t or "emergency department" in t:
            return TriageLevel.URGENT
        if "see a doctor today" in t or "same day" in t:
            return TriageLevel.SEMI_URGENT
        if "self-care" in t or "home care" in t:
            return TriageLevel.SELF_CARE
        return TriageLevel.NON_URGENT
