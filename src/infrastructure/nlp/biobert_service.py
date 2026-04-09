from __future__ import annotations

from src.domain.entities.symptom import Severity, SymptomEntity
from src.domain.interfaces.nlp_service import INLPService
from src.infrastructure.nlp.symptom_mapper import map_symptom_to_icd10


class BioBERTService(INLPService):
    """NER-based entity extraction; summarization uses a small model or safe fallback."""

    MODEL_NAME = "dslim/bert-base-NER"

    def __init__(self) -> None:
        self._ner = None

    @property
    def ner_pipeline(self):
        if self._ner is None:
            from transformers import pipeline as hf_pipeline

            self._ner = hf_pipeline(
                "ner",
                model=self.MODEL_NAME,
                aggregation_strategy="simple",
            )
        return self._ner

    def extract_symptoms(self, text: str) -> list[SymptomEntity]:
        entities = self.ner_pipeline(text)
        symptoms: list[SymptomEntity] = []
        seen: set[str] = set()
        for ent in entities:
            if float(ent.get("score", 0)) <= 0.75:
                continue
            word = str(ent.get("word", "")).strip()
            if not word or word.lower() in seen:
                continue
            seen.add(word.lower())
            symptoms.append(
                SymptomEntity(
                    name=word,
                    severity=self._infer_severity(text, word),
                    icd10_code=map_symptom_to_icd10(word),
                )
            )
        return symptoms

    def _infer_severity(self, text: str, symptom: str) -> Severity:
        text_lower = text.lower()
        if any(w in text_lower for w in ("severe", "extreme", "unbearable", "crushing")):
            return Severity.SEVERE
        if any(w in text_lower for w in ("moderate", "significant", "strong")):
            return Severity.MODERATE
        return Severity.MILD

    def summarize(self, text: str, max_length: int = 200) -> str:
        t = (text or "").strip()
        if len(t) <= max_length:
            return t
        try:
            from transformers import pipeline as hf_pipeline

            summarizer = hf_pipeline("summarization", model="facebook/bart-large-cnn")
            out = summarizer(t[:4096], max_length=max_length, min_length=min(30, max_length - 1))
            return str(out[0]["summary_text"])
        except Exception:
            return t[: max_length - 3] + "..."
