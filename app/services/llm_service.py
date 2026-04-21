import json
import re
from typing import Any, Dict

from loguru import logger

from app.models.schemas import SessionState
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

    async def generate_response(self, session: SessionState, is_final: bool) -> Dict[str, Any]:
        """Generate response based on chat history. Eiter follow-up question or structured response."""
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """You are a medical assistant chatbot.
        * Be empathetic and natural
        * Ask follow-up questions when needed
        * Do NOT give final diagnoses
        * Suggest possible causes only
        * Always recommend consulting a doctor
        * Adjust response based on risk level
        * Keep answers clear and structured"""

        history_str = "\\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.messages])

        if not is_final:
            prompt = """
            Based on the user's symptoms and history, ask 1 to 2 intelligent follow-up questions to 
            gather missing information (e.g., duration, severity, or any associated symptoms).
            Format as a plain empathetic text message. Return ONLY the text of your response.
            """
            try:
                msg = await self._llm.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Chat history:\\n{history_str}\\n\\nTask: {prompt}"),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()
                return {"message": text, "is_final": False}
            except Exception as exc:
                logger.error(f"Failed asking follow-up: {exc}")
                return {"message": "Could you tell me a little more about your symptoms?", "is_final": False}
        else:
            prompt = """
            Analyze the gathered symptoms and chat history to provide a final structured consultation.
            Return ONLY valid JSON in this exact format:
            {
                "empathy": "A short empathetic sentence",
                "summary": "Brief summary of their condition",
                "possible_causes": ["Cause 1", "Cause 2"],
                "what_you_can_do": "Actionable home care advice",
                "when_to_be_concerned": "Red flags indicating severity",
                "recommended_specialist": "Type of doctor to see",
                "disclaimer": "This is not a medical diagnosis. Please consult a healthcare professional.",
                "risk_level": "low" | "medium" | "high" | "emergency"
            }
            """
            symptoms_str = ", ".join(session.symptoms)
            
            try:
                msg = await self._llm.ainvoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(
                            content=f"Chat history:\\n{history_str}\\n\\nSymptoms extracted: {symptoms_str}\\nDuration: {session.duration}\\nAssessed Risk: {session.risk_level}\\n\\nTask: {prompt}"
                        ),
                    ]
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()
                
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
                data = json.loads(text)
                
                # Transform urgency values safely
                risk_val = str(data.get("risk_level", "medium")).lower()
                if risk_val not in ["low", "medium", "high", "emergency"]:
                    risk_val = "medium"
                    
                data["risk_level"] = risk_val
                data["message"] = "Final report ready."
                data["is_final"] = True
                return data
            except Exception as exc:
                logger.exception("Failed generating final response")
                return {
                    "message": "I apologize, but I am unable to generate a detailed summary at this moment. Please consult a health professional.",
                    "is_final": True,
                }
