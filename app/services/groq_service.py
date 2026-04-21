from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from src.core.config import settings


GROQ_PROMPT_STANDARD = """You are a compassionate and intelligent medical assistant chatbot.

Your role is to:
- Listen carefully to users describing their symptoms
- Ask relevant follow-up questions to gather more context
- Provide helpful, structured medical guidance
- Detect emergencies and respond with urgency when needed
- Always remind users that you are not a replacement for professional medical advice

Language and Tone:
- Communicate in a warm, clear, and empathetic tone.
- Adapt to the user's language — if they write in Arabic or mix Arabic and English, respond accordingly.
- Your 'summary' and 'advice' outputs MUST be in the same language the user uses.

Response rules:
* Start with a short empathetic sentence
* Use simple, conversational language
* Avoid overly technical wording unless necessary
* Use bullet points for clarity

Risk handling:
* Adjust response based on risk level: LOW, MEDIUM, HIGH, EMERGENCY
* LOW → reassurance + simple advice
* MEDIUM → advice + suggest doctor if persistent
* HIGH → recommend seeing a doctor soon
* EMERGENCY → override everything and instruct immediate medical care

Medical safety:
* Do NOT give a final diagnosis
* Only suggest possible causes
* Always include a disclaimer

Always include:
* Possible causes
* Actionable advice
* When to seek help
* Doctor specialty recommendation

Keep responses clear, helpful, and not too long.
"""

_REQUIRED_DISCLAIMER = "This is not a medical diagnosis. Please consult a healthcare professional."

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _coerce_to_analyze_json(obj: Any) -> dict:
    """Normalize model output into the strict response JSON shape."""
    if not isinstance(obj, dict):
        raise ValueError("Model did not return a JSON object")

    summary = str(obj.get("summary", "")).strip()
    advice = str(obj.get("advice", "")).strip()
    urgency = str(obj.get("urgency", "")).strip().lower()
    causes = obj.get("possible_causes", [])
    if isinstance(causes, str):
        causes = [c.strip() for c in causes.split("\n") if c.strip()]
    if not isinstance(causes, list):
        causes = []
    causes = [str(c).strip() for c in causes if str(c).strip()][:12]

    if urgency not in {"low", "medium", "high", "emergency"}:
        # Safe default if the model violates the contract.
        urgency = "medium"

    if not summary:
        summary = "Summary unavailable."
    if not advice:
        advice = "If symptoms worsen or you are concerned, seek medical care."

    # Enforce the required disclaimer (output schema has no dedicated field).
    if _REQUIRED_DISCLAIMER.lower() not in (summary + "\n" + advice).lower():
        advice = (advice.rstrip() + "\n\n" + _REQUIRED_DISCLAIMER).strip()

    return {
        "summary": summary,
        "possible_causes": causes,
        "advice": advice,
        "urgency": urgency,

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
        Ask Groq to output STRICT JSON:
        {summary, possible_causes, advice, urgency}.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            GROQ_PROMPT_STANDARD
            + "\nReturn ONLY valid JSON in this exact format:\n"
            + '{\n  "summary": "...",\n  "possible_causes": ["..."],\n  "advice": "...",\n  "urgency": "low | medium | high | emergency"\n}\n'
            + "\nUser content:\n"
            + user_input.strip()
        )

        try:
            msg = await self._llm.ainvoke(
                [SystemMessage(content="You are a helpful assistant."), HumanMessage(content=prompt)]
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

        return _coerce_to_analyze_json(obj)

