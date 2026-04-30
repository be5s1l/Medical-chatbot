import json
import re
from typing import Any, Dict

from loguru import logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.schemas import SessionState, ChatResponseData, StructuredDiagnosis, Urgency
from src.core.config import settings
from app.services.conversation_manager import ARABIC_SYSTEM_TEMPLATE, ENGLISH_SYSTEM_TEMPLATE


class LLMService:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
            timeout=30, # Timeout handling
        )

    async def generate_response_raw(self, prompt: str) -> str:
        """Reusable function to generate a raw text response from the LLM."""
        try:
            msg = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return (getattr(msg, "content", None) or str(msg)).strip()
        except Exception as exc:
            logger.error(f"Gemini API call failed: {exc}")
            return ""

    async def analyze_input(self, user_text: str) -> Dict[str, Any]:
        """Extract symptoms and determine if enough context is provided."""
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

    def _get_system_prompt(self) -> str:
        """Get system prompt based on config language."""
        if settings.app_lang == "ar":
            return ARABIC_SYSTEM_TEMPLATE.messages[0].prompt.template
        return ENGLISH_SYSTEM_TEMPLATE.messages[0].prompt.template

    async def generate_response(self, session: SessionState, is_final: bool) -> ChatResponseData:
        """Generate response based on chat history as a strict ChatResponseData structure."""
        system_prompt = self._get_system_prompt()
        history_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.messages])

        if not is_final:
            prompt = """
            Based on the conversation so far, ask 1 to 2 follow-up questions to gather missing medical details 
            (e.g., duration, severity, related symptoms).
            
            IMPORTANT:
            - If this is the FIRST response after symptoms were described, include a BRIEF empathy sentence.
            - Otherwise, be direct and natural.
            - Ask ONLY 1-2 questions.
            
            Return ONLY valid JSON in this exact format:
            {
                "message": "A single conversational string asking the follow-up questions in the user's language.",
                "follow_up_questions": ["Question 1 (in user's language)", "Question 2 (in user's language)"]
            }
            """
            try:
                msg = await self._llm.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Chat history:\n{history_str}\n\nTask: {prompt}"),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
                data = json.loads(text)
                
                return ChatResponseData(
                    message=data.get("message", "Could you tell me a little more about your symptoms?"),
                    risk_level=Urgency.medium,
                    follow_up_questions=data.get("follow_up_questions", []),
                    structured=None
                )
            except Exception as exc:
                logger.error(f"Failed asking follow-up: {exc}")
                return ChatResponseData(
                    message="Could you tell me a little more about your symptoms?",
                    risk_level=Urgency.medium,
                    follow_up_questions=["Can you describe your symptoms in more detail?"],
                    structured=None
                )
        else:
            prompt = """
            Analyze the gathered symptoms and chat history. Return ONLY valid JSON in this exact format:
            {
                "message": "A brief conclusion message in the user's language.",
                "risk_level": "LOW | MEDIUM | HIGH | EMERGENCY",
                "structured": {
                    "summary": "1-2 sentence clinical summary (in user's language).",
                    "possible_causes": ["Cause 1 (in user's language)", "Cause 2 (in user's language)"],
                    "advice": ["What You Can Do 1 (in user's language)", "What You Can Do 2 (in user's language)"],
                    "when_to_worry": ["When to Be Concerned 1 (in user's language)", "When to Be Concerned 2 (in user's language)"],
                    "recommended_doctors": ["Recommended Doctor 1 (in user's language)", "Recommended Doctor 2 (in user's language)"],
                    "risk": "Brief explanation of the risk level (in user's language)."
                }
            }
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
                                f"Task: {prompt}"
                            )
                        ),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()

                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
                data = json.loads(text)

                risk_val_str = str(data.get("risk_level", "MEDIUM")).upper()
                try:
                    risk_val = Urgency(risk_val_str)
                except ValueError:
                    risk_val = Urgency.medium

                struct_data = data.get("structured", {})
                
                structured = StructuredDiagnosis(
                    summary=struct_data.get("summary", "Summary unavailable."),
                    possible_causes=struct_data.get("possible_causes", []),
                    advice=struct_data.get("advice", []),
                    when_to_worry=struct_data.get("when_to_worry", []),
                    recommended_doctors=struct_data.get("recommended_doctors", []),
                    risk=struct_data.get("risk", "Medium physical risk")
                )

                return ChatResponseData(
                    message=data.get("message", "I have generated a structured medical report based on your symptoms."),
                    risk_level=risk_val,
                    follow_up_questions=[],
                    structured=structured
                )

            except Exception as exc:
                logger.exception("Failed generating final response")
                return ChatResponseData(
                    message="I wasn't able to generate a detailed report right now. Please reach out to a healthcare professional.",
                    risk_level=Urgency.medium,
                    follow_up_questions=[],
                    structured=None
                )
