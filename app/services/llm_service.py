import json
import re
from typing import Any, Dict, List

from loguru import logger

from app.models.schemas import SessionState
from src.core.config import settings

_DISCLAIMER = "This is not a medical diagnosis. Please consult a healthcare professional."

_RISK_EMOJI = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🔴 High",
    "emergency": "⚠️ Emergency",
}


def _strip_markdown(text: str) -> str:
    """
    Remove common markdown symbols that LLMs inject even when told not to.
    Strips: **bold**, *italic*, __bold__, _italic_, ## headers, ---, > blockquotes, `code`.
    """
    # Remove horizontal rules
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove ATX headers (## Title)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold+italic (*** or ___)
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    text = re.sub(r"_{3}(.+?)_{3}", r"\1", text)
    # Remove bold (** or __)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text)
    # Remove italic (* or _) — careful not to strip bullet •
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"\1", text)
    # Remove inline code backticks
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove blockquote markers
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _bullet_list(items: List[str]) -> str:
    """Convert a list of strings into bullet-point lines using •."""
    return "\n".join(f"• {_strip_markdown(item).strip()}" for item in items if str(item).strip())


def _split_to_bullets(text: str) -> str:
    """Split a paragraph/newline-separated text into bullet lines."""
    clean = _strip_markdown(text)
    lines = [line.strip().lstrip("-•*").strip() for line in re.split(r"\n+", clean) if line.strip()]
    return _bullet_list(lines)


def format_final_response(data: Dict[str, Any]) -> str:
    """
    Assemble the structured, emoji-sectioned plain-text response
    from the JSON fields returned by the LLM.
    """
    empathy = _strip_markdown(str(data.get("empathy", "")).strip())
    summary = _strip_markdown(str(data.get("summary", "")).strip())
    causes_raw = data.get("possible_causes", [])
    what_to_do_raw = _strip_markdown(str(data.get("what_you_can_do", "")).strip())
    concerned_raw = _strip_markdown(str(data.get("when_to_be_concerned", "")).strip())
    specialist = _strip_markdown(str(data.get("recommended_specialist", "General Practitioner (GP)")).strip())
    risk_val = str(data.get("risk_level", "medium")).lower()
    if risk_val not in _RISK_EMOJI:
        risk_val = "medium"
    risk_label = _RISK_EMOJI[risk_val]

    # Format possible causes
    if isinstance(causes_raw, list):
        causes_bullets = _bullet_list(causes_raw)
    else:
        causes_bullets = _split_to_bullets(str(causes_raw))

    # Format what you can do
    what_bullets = _split_to_bullets(what_to_do_raw)

    # Format when to be concerned
    concerned_bullets = _split_to_bullets(concerned_raw)

    parts = []

    # Friendly intro
    if empathy:
        parts.append(f"Hi, I'm MediBot 👋\n{empathy}")
    else:
        parts.append("Hi, I'm MediBot 👋\nI'm here to help you understand what might be going on.")

    # Summary
    if summary:
        parts.append(f"🧠 Summary\n{summary}")

    # Possible Causes
    if causes_bullets:
        parts.append(f"🔍 Possible Causes\n{causes_bullets}")

    # What You Can Do
    if what_bullets:
        parts.append(f"💡 What You Can Do\n{what_bullets}")

    # When to Be Concerned
    if concerned_bullets:
        parts.append(f"⚠️ When to Be Concerned\n{concerned_bullets}")

    # Recommended Doctor
    if specialist:
        parts.append(f"🩺 Recommended Doctor\n{specialist}")

    # Risk Level
    parts.append(f"📊 Risk Level: {risk_label}")

    # Disclaimer
    parts.append(_DISCLAIMER)

    return "\n\n".join(parts)


class LLMService:
    def __init__(self) -> None:
        from langchain_groq import ChatGroq  # type: ignore

        if not getattr(settings, "groq_api_key", ""):
            raise RuntimeError("GROQ_API_KEY is not set")
        self._llm = ChatGroq(
            model_name=getattr(settings, "groq_model", "llama-3.3-70b-versatile"),
            groq_api_key=getattr(settings, "groq_api_key", ""),
            temperature=0.1,
        )

    async def analyze_input(self, user_text: str) -> Dict[str, Any]:
        """Extract symptoms and determine if enough context is provided."""
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = f"""
        Extract the user's symptoms and how long they've had them (duration).
        Determine if there is enough context. (At least 1 symptom + its duration, OR >= 2 symptoms).
        Return ONLY valid JSON in this exact format:
        {{
            "symptoms": ["symptom1", "symptom2"],
            "duration": "duration if mentioned, else empty string",
            "has_enough_info": true or false
        }}
        User input: "{user_text}"
        """

        try:
            msg = await self._llm.ainvoke(
                [
                    SystemMessage(content="You extract structured medical information."),
                    HumanMessage(content=prompt),
                ]
            )
            text = (getattr(msg, "content", None) or str(msg)).strip()

            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                text = m.group(0)
            return json.loads(text)
        except Exception as exc:
            logger.error(f"Failed to analyze input: {exc}")
            return {"symptoms": [], "duration": "", "has_enough_info": False}

    async def generate_response(self, session: SessionState, is_final: bool) -> Dict[str, Any]:
        """Generate a response based on chat history — either a follow-up question or a structured final report."""
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are a compassionate medical assistant chatbot.
        - Be empathetic and speak in a natural, human tone.
        - Ask follow-up questions when you need more context.
        - Do NOT give final diagnoses — only suggest possible causes.
        - Always recommend consulting a real doctor.
        - Keep answers clear, calm, and easy to understand."""

        history_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.messages])

        if not is_final:
            prompt = (
                "Based on the conversation so far, ask 1 to 2 warm, empathetic follow-up questions "
                "to gather missing details (e.g. duration, severity, related symptoms). "
                "Write in plain, conversational text only. Do NOT use markdown or bullet symbols."
            )
            try:
                msg = await self._llm.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Chat history:\n{history_str}\n\nTask: {prompt}"),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()
                return {"message": text, "is_final": False}
            except Exception as exc:
                logger.error(f"Failed asking follow-up: {exc}")
                return {"message": "Could you tell me a little more about your symptoms?", "is_final": False}
        else:
            prompt = """
Analyze the gathered symptoms and chat history. Return ONLY valid JSON in this exact format with no extra text:
{
    "empathy": "A short (1 sentence) empathetic, human opening — e.g. I understand how uncomfortable this can feel.",
    "summary": "A 1-2 sentence plain-language summary of what the user is experiencing.",
    "possible_causes": ["Cause 1", "Cause 2", "Cause 3"],
    "what_you_can_do": "2-4 short actionable home-care tips separated by newlines. Start each with an emoji.",
    "when_to_be_concerned": "2-3 short red-flag signs separated by newlines.",
    "recommended_specialist": "Name of the doctor specialty to consult (e.g. General Practitioner, Cardiologist).",
    "risk_level": "low | medium | high | emergency"
}

Rules:
- Use plain conversational English. No markdown. No ** or ## or __ symbols.
- Keep each value short and easy to read.
- possible_causes must be a JSON array of strings.
- risk_level must be exactly one of: low, medium, high, emergency.
"""
            symptoms_str = ", ".join(session.symptoms)

            try:
                msg = await self._llm.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(
                            content=(
                                f"Chat history:\n{history_str}\n\n"
                                f"Symptoms: {symptoms_str}\n"
                                f"Duration: {session.duration}\n"
                                f"Assessed Risk: {session.risk_level}\n\n"
                                f"Task:{prompt}"
                            )
                        ),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()

                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
                data = json.loads(text)

                # Normalize risk level
                risk_val = str(data.get("risk_level", "medium")).lower()
                if risk_val not in {"low", "medium", "high", "emergency"}:
                    risk_val = "medium"
                data["risk_level"] = risk_val

                # Build the clean formatted message
                formatted = format_final_response(data)

                return {
                    "message": formatted,
                    "is_final": True,
                    "empathy": data.get("empathy"),
                    "summary": data.get("summary"),
                    "possible_causes": data.get("possible_causes"),
                    "what_you_can_do": data.get("what_you_can_do"),
                    "when_to_be_concerned": data.get("when_to_be_concerned"),
                    "recommended_specialist": data.get("recommended_specialist"),
                    "disclaimer": _DISCLAIMER,
                    "risk_level": risk_val,
                }
            except Exception as exc:
                logger.exception("Failed generating final response")
                return {
                    "message": (
                        "Hi, I'm MediBot 👋\n"
                        "I understand this can be worrying.\n\n"
                        "I wasn't able to generate a detailed report right now. "
                        "Please reach out to a healthcare professional for guidance.\n\n"
                        + _DISCLAIMER
                    ),
                    "is_final": True,
                }
