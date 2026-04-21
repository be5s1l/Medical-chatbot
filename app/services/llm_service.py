import json
import re
from typing import Any, Dict

from loguru import logger

from app.models.schemas import SessionState, ChatResponseData, StructuredDiagnosis, Urgency
from src.core.config import settings


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

    async def generate_response(self, session: SessionState, is_final: bool) -> ChatResponseData:
        """Generate response based on chat history as a strict ChatResponseData structure."""
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are a medical reasoning AI. 
        - Your output will be consumed by an API. Do NOT use emojis, markdown formatting, or conversational filler inside structured fields.
        - Analyze the user symptoms and provide structured medical intelligence.
        - Do NOT give a final diagnosis. Only suggest possible causes.
        - Ask follow-up questions if you need more context."""

        history_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.messages])

        if not is_final:
            prompt = """
            Based on the conversation so far, ask 1 to 2 follow-up questions to gather missing medical details 
            (e.g., duration, severity, related symptoms).
            Return ONLY valid JSON in this exact format:
            {
                "message": "A single conversational string asking the follow-up questions.",
                "follow_up_questions": ["Question 1", "Question 2"]
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
                "message": "A brief natural language summary of the findings (plain text, no markdown).",
                "risk_level": "LOW | MEDIUM | HIGH | EMERGENCY",
                "structured": {
                    "summary": "1-2 sentence clinical summary.",
                    "possible_causes": ["Cause 1", "Cause 2"],
                    "advice": ["Advice 1", "Advice 2"],
                    "when_to_worry": ["Red flag 1", "Red flag 2"],
                    "recommended_doctors": ["Specialist 1", "Specialist 2"],
                    "risk": "Brief explanation of the risk level."
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
