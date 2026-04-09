import re
from pathlib import Path

from loguru import logger

from src.core.constants import DEFAULT_DISCLAIMER
from src.helpers.safety_layer import check_emergency, handle_emergency, inject_disclaimer
from src.infrastructure.llm.langchain_chain import MedicalRAGChain
from src.infrastructure.nlp.biobert_service import BioBERTService
from src.infrastructure.vector_db.chroma_service import ChromaDBService


class FileIngestionController:
    def __init__(self) -> None:
        from src.infrastructure.ocr.tesseract_service import TesseractOCRService

        self.ocr = TesseractOCRService()
        self.nlp = BioBERTService()
        self.rag = MedicalRAGChain()
        self.vector_db = ChromaDBService()

    def process_document(self, file_path: str) -> dict:
        text = self.ocr.extract_text(file_path)
        logger.debug("OCR/PDF text length: {}", len(text))
        if check_emergency(text):
            tr = handle_emergency(text)
            return {
                "summary": "",
                "key_findings": [],
                "response": tr.response_text,
                "disclaimer": tr.disclaimer,
            }

        summary = self.nlp.summarize(text, max_length=200)
        llm = self.rag.summarize_document(text[:8000])
        key_findings = self._bullet_findings(llm)
        safe = inject_disclaimer(llm)

        try:
            self.vector_db.add_documents([{"text": text[:2000], "source": f"upload:{Path(file_path).name}"}])
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not index uploaded document: {}", exc)

        return {
            "summary": summary,
            "key_findings": key_findings,
            "response": safe,
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    def _bullet_findings(self, llm_text: str) -> list[str]:
        lines = [ln.strip() for ln in llm_text.splitlines() if ln.strip()]
        bullets = [re.sub(r"^[-*]\s*", "", ln) for ln in lines if ln.lstrip().startswith(("-", "*"))]
        if bullets:
            return bullets[:12]
        return [ln[:200] for ln in lines[:8]]


class ImageIngestionController:
    def __init__(self) -> None:
        from src.infrastructure.vision.chexnet_service import CheXNetVisionService

        self.vision = CheXNetVisionService()

    def process_image(self, file_path: str) -> dict:
        # Filename alone is not clinical text; skip emergency on path.
        result = self.vision.classify(file_path)
        findings = result.findings or []
        narrative = (
            f"Model label: {result.label} (confidence {result.confidence:.2f}). "
            f"Findings are not a diagnosis. Discuss any image with a qualified clinician.\n"
            + "\n".join(findings)
        )
        return {
            "classification": result.label,
            "confidence": result.confidence,
            "findings": findings or [narrative[:500]],
            "disclaimer": DEFAULT_DISCLAIMER,
        }
