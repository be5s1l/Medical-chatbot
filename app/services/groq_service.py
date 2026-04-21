from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from app.services.llm_service import _DISCLAIMER, format_final_response
from src.core.config import settings


GROQ_PROMPT_STANDARD = """You are a compassionate and intelligent medical assistant chatbot.

Your role is to:
- Listen carefully to users describing their symptoms
- Provide helpful, empathetic medical guidance
- Detect emergencies and respond with urgency when needed
- Always remind users that you are not a replacement for professional medical advice

Language and Tone:
- Communicate in a warm, clear, and empathetic tone.
- Sound natural and human — never robotic.
- Adapt to the user's language. If they write in Arabic or mix Arabic and English, respond accordingly.
- Your outputs MUST be in the same language the user uses.

Formatting rules (STRICT):
- Do NOT use any markdown symbols: no **, no __, no ##, no --- separators.
- Do NOT use bold or italic markers.
- Use plain conversational sentences.
- Keep each section short and easy to read at a glance.

Risk handling:
- Adjust response based on risk level: low, medium, high, emergency
- low → reassurance + simple home advice
- medium → advice + suggest seeing a doctor if symptoms persist
- high → recommend seeing a doctor soon
- emergency → instruct immediate medical care urgently

Medical safety:
- Do NOT give a final diagnosis
- Only suggest possible causes
- Always include a disclaimer

Return ONLY valid JSON. No extra text outside the JSON.
"""

_REQUIRED_DISCLAIMER = _DISCLAIMER

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _coerce_to_full_response(obj: Any) -> dict:
    """
    Normalize extended JSON from Groq into a fully formatted
    plain-text response dict compatible with ChatResponse.
    """
    if not isinstance(obj, dict):
        raise ValueError("Model did not return a JSON object")

    # Normalise possible_causes
    causes = obj.get("possible_causes", [])
    if isinstance(causes, str):
        causes = [c.strip() for c in causes.split("\n") if c.strip()]
    if not isinstance(causes, list):
        causes = []
    causes = [str(c).strip() for c in causes if str(c).strip()][:12]
    obj["possible_causes"] = causes

    # Normalise urgency → risk_level (groq returns "urgency" key)
    urgency = str(obj.get("urgency", obj.get("risk_level", "medium"))).strip().lower()
    if urgency not in {"low", "medium", "high", "emergency"}:
        urgency = "medium"
    obj["risk_level"] = urgency

    # Safe defaults for missing fields
    if not obj.get("summary"):
        obj["summary"] = "Summary unavailable."
    if not obj.get("empathy"):
        obj["empathy"] = "I understand this can be concerning."
    if not obj.get("recommended_specialist"):
        obj["recommended_specialist"] = "General Practitioner (GP)"

    # Build the clean, formatted plain-text message using the shared formatter
    formatted = format_final_response(obj)

    return {
        "message": formatted,
        "is_final": True,
        "empathy": obj.get("empathy"),
        "summary": obj.get("summary"),
        "possible_causes": causes,
        "what_you_can_do": obj.get("what_you_can_do"),
        "when_to_be_concerned": obj.get("when_to_be_concerned"),
        "recommended_specialist": obj.get("recommended_specialist"),
        "disclaimer": _DISCLAIMER,
        "risk_level": urgency,
    }


class GroqService:
    def __init__(self) -> None:
        from langchain_groq import ChatGroq  # type: ignore

        if not getattr(settings, "groq_api_key", ""):
            raise RuntimeError("GROQ_API_KEY is not set")
        self._llm = ChatGroq(
            model_name=getattr(settings, "groq_model", "llama-3.3-70b-versatile"),
            groq_api_key=getattr(settings, "groq_api_key", ""),
            temperature=0.1,
        )

    async def analyze(self, *, user_input: str) -> dict:
        """
        Ask Groq to output extended JSON with all structured fields,
        then format into a clean, human-friendly plain-text response.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            "\nReturn ONLY valid JSON in this exact format with no extra text outside the JSON:\n"
            + (
                '{\n'
                '  "empathy": "A short (1 sentence) warm empathetic opening. No markdown.",\n'
                '  "summary": "A 1-2 sentence plain-language summary of the user symptoms.",\n'
                '  "possible_causes": ["Cause 1", "Cause 2"],\n'
                '  "what_you_can_do": "2-4 short actionable tips separated by newlines. Start each with an emoji.",\n'
                '  "when_to_be_concerned": "2-3 short red-flag signs separated by newlines.",\n'
                '  "recommended_specialist": "Doctor specialty name.",\n'
                '  "urgency": "low | medium | high | emergency"\n'
                '}\n'
            )
            + "\nUser content:\n"
            + user_input.strip()
        )

        try:
            msg = await self._llm.ainvoke(
                [SystemMessage(content=GROQ_PROMPT_STANDARD), HumanMessage(content=prompt)]
            )
        except Exception as exc:
            msg_txt = str(exc)
            if len(msg_txt) > 500:
                msg_txt = msg_txt[:500] + "..."
            raise RuntimeError(f"Groq API error: {msg_txt}") from exc

        text = (getattr(msg, "content", None) or str(msg)).strip()

        # Parse JSON as robustly as possible.
        try:
            obj = json.loads(text)
        except Exception:
            m = _JSON_RE.search(text)
            if not m:
                logger.warning("Groq response was not JSON. First 300 chars: {}", text[:300])
                raise RuntimeError("LLM did not return JSON")
            obj = json.loads(m.group(0))

        return _coerce_to_full_response(obj)
