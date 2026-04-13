from __future__ import annotations

from loguru import logger

from src.core.config import settings
from src.infrastructure.llm.prompt_templates import (
    DOC_SUMMARY_PROMPT_TEMPLATE,
    TRIAGE_PROMPT_TEMPLATE,
    VITALS_PROMPT_TEMPLATE,
)
from src.infrastructure.vector_db.chroma_service import ChromaDBService


class MedicalRAGChain:
    """RAG using Chroma retrieval + pluggable chat model."""

    def __init__(self) -> None:
        self._vector_db: ChromaDBService | None = None
        self._llm = None

    def _get_vector_db(self) -> ChromaDBService:
        if self._vector_db is None:
            self._vector_db = ChromaDBService()
        return self._vector_db

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._build_llm()
        return self._llm

    def _build_llm(self):
        provider = (settings.llm_provider or "openai").strip().lower()
        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Ollama provider selected but `langchain-ollama` is not installed. "
                    "Install it and restart."
                ) from exc
            logger.info("Using Ollama model: {}", settings.ollama_model)
            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.1,
            )

        if provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Gemini provider selected but `langchain-google-genai` is not installed. "
                    "Install it and restart."
                ) from exc

            if not settings.gemini_api_key:
                logger.warning("GEMINI_API_KEY is empty. Set it or switch LLM_PROVIDER.")
            model = (settings.gemini_model or "").strip()
            if model and not model.startswith("models/"):
                # The v1beta API returns model ids like `models/gemini-2.0-flash`.
                # Accept shorthand `gemini-2.0-flash` in config for convenience.
                model = f"models/{model}"
            logger.info("Using Gemini model: {}", model or "(unset)")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=settings.gemini_api_key or None,
                temperature=0.1,
            )

        if provider == "groq":
            try:
                from langchain_groq import ChatGroq  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Groq provider selected but `langchain-groq` is not installed. "
                    "Install it and restart."
                ) from exc
            if not settings.groq_api_key:
                logger.warning("GROQ_API_KEY is empty. Set it or switch LLM_PROVIDER.")
            logger.info("Using Groq model: {}", settings.groq_model)
            return ChatGroq(
                model_name=settings.groq_model,
                groq_api_key=settings.groq_api_key or None,
                temperature=0.1,
            )

        # Default: OpenAI
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
        except Exception:  # pragma: no cover
            from langchain_community.chat_models import ChatOpenAI  # type: ignore

        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY is empty. Set it or switch LLM_PROVIDER (e.g. groq, ollama).")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    def query(self, question: str) -> str:
        # Vector DB can be slow on first load (embedding model download). Lazily init and degrade gracefully.
        try:
            hits = self._get_vector_db().search(question, n_results=5)
        except Exception as exc:
            logger.warning("Vector DB search failed (continuing with empty context): {}", exc)
            hits = []
        context_parts = []
        for h in hits:
            src = h.get("source", "Unknown")
            context_parts.append(f"[{src}]\n{h.get('text', '')}")
        context = "\n\n".join(context_parts) if context_parts else "(No matching passages in the knowledge base.)"
        prompt = TRIAGE_PROMPT_TEMPLATE.format(context=context, question=question)
        msg = self.llm.invoke(prompt)
        content = getattr(msg, "content", None) or str(msg)
        return content

    def summarize_document(self, document_text: str) -> str:
        prompt = DOC_SUMMARY_PROMPT_TEMPLATE.format(document_text=document_text[:12000])
        msg = self.llm.invoke(prompt)
        return getattr(msg, "content", None) or str(msg)

    def advise_vitals(self, vitals_text: str) -> str:
        prompt = VITALS_PROMPT_TEMPLATE.format(vitals_text=vitals_text)
        msg = self.llm.invoke(prompt)
        return getattr(msg, "content", None) or str(msg)

