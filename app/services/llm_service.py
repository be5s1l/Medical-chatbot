import json
import re
from typing import Any, Dict, List

from loguru import logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.models.schemas import (
    SessionState, ChatResponseData, StructuredDiagnosis, Urgency,
    ResponseType, DoctorSearchParams, DoctorResult,
    UIComponent, UIComponentType,
)
from src.core.config import settings
from app.services.conversation_manager import ARABIC_SYSTEM_TEMPLATE, ENGLISH_SYSTEM_TEMPLATE
from app.services.context_filter import ContextFilter
from app.services.gemini_quota import QuotaExceededError, invoke_with_quota_handling

# Re-export for callers that import from llm_service.
__all__ = ["LLMService", "QuotaExceededError"]


class LLMService:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
            timeout=30,
        )

    async def _invoke(self, messages: List[BaseMessage], *, operation: str):
        """Single Gemini call with quota detection and limited retries."""

        async def _call():
            return await self._llm.ainvoke(messages)

        return await invoke_with_quota_handling(_call, operation=operation)

    # ------------------------------------------------------------------
    # Agentic doctor search helpers
    # ------------------------------------------------------------------

    async def detect_doctor_intent(self, user_text: str) -> DoctorSearchParams | None:
        """
        Check whether the user wants to find/book a doctor.
        Returns DoctorSearchParams with extracted filters if intent is found,
        or None if this is a normal medical/symptom message.
        """
        prompt = f"""
        Determine whether the user's message expresses an intent to FIND, SEE, or BOOK a doctor.
        Examples of positive intent: "I need a cardiologist", "find me a doctor near Cairo", "who is a good dermatologist?"
        Examples of negative intent (symptoms only): "I have a headache", "my stomach hurts"

        If the intent is to find a doctor, extract:
        - specialization (e.g. "cardiologist", "dermatologist") — null if not mentioned
        - location (city or area, e.g. "Cairo") — null if not mentioned
        - min_rating (float 0-5 based on words like "highly rated", "good", "best") — null if not mentioned

        Return ONLY valid JSON:
        If YES: {{"wants_doctor": true, "specialization": "...", "location": "...", "min_rating": null}}
        If NO:  {{"wants_doctor": false}}

        User message: "{user_text}"
        """
        try:
            msg = await self._invoke(
                [
                    SystemMessage(content="You are an intent classifier for a medical assistant. Be concise and accurate."),
                    HumanMessage(content=prompt),
                ],
                operation="detect_doctor_intent",
            )
            text = (getattr(msg, "content", None) or str(msg)).strip()
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                text = m.group(0)
            data = json.loads(text)
            if not data.get("wants_doctor", False):
                return None
            return DoctorSearchParams(
                specialization=data.get("specialization") or None,
                location=data.get("location") or None,
                min_rating=data.get("min_rating") or None,
            )
        except QuotaExceededError:
            raise
        except Exception as exc:
            logger.error(f"Failed to detect doctor intent: {exc}")
            return None

    async def generate_response_for_doctors(
        self,
        session: SessionState,
        doctors: List[DoctorResult],
    ) -> ChatResponseData:
        """
        Given a list of DoctorResult objects fetched by the client, ask Gemini
        to present them conversationally in the user's language.
        """
        system_prompt = self._get_system_prompt()
        history_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in session.messages])

        if not doctors:
            no_result_prompt = (
                "The patient was searching for a doctor but no results were found. "
                "Politely let them know and suggest they try a different search or consult online."
        )
            try:
                msg = await self._invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=f"Chat history:\n{history_str}\n\nTask: {no_result_prompt}"),
                    ],
                    operation="generate_response_for_doctors",
                )
                reply = (getattr(msg, "content", None) or str(msg)).strip()
            except QuotaExceededError:
                raise
            except Exception:
                reply = "Sorry, I couldn't find any doctors matching your criteria. Please try a different search."
            return ChatResponseData(
                type=ResponseType.chat,
                message=reply,
                risk_level=Urgency.low,
                follow_up_questions=[],
                structured=None,
            )

        # Build a numbered doctor list for the prompt
        doctor_lines = []
        for i, doc in enumerate(doctors, start=1):
            parts = [f"{i}. {doc.name} — {doc.specialization}"]
            if doc.clinic:
                parts.append(f"Clinic: {doc.clinic}")
            if doc.location:
                parts.append(f"Location: {doc.location}")
            if doc.rating is not None:
                parts.append(f"Rating: {doc.rating}/5")
            if doc.available is not None:
                parts.append("Available" if doc.available else "Not available right now")
            doctor_lines.append(" | ".join(parts))
        doctors_str = "\n".join(doctor_lines)

        present_prompt = f"""
        The patient was looking for a doctor. Here are the results fetched from the system:

{doctors_str}

        Present these doctors to the patient in a friendly, readable way in the user's language.
        - Keep it concise.
        - Highlight availability and rating.
        - End by asking if they would like to book with any of them.
        - Do NOT add markdown, bullet symbols, or emojis inside structured fields.
        """
        try:
            msg = await self._invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Chat history:\n{history_str}\n\nTask: {present_prompt}"),
                ],
                operation="generate_response_for_doctors",
            )
            reply = (getattr(msg, "content", None) or str(msg)).strip()
        except QuotaExceededError:
            raise
        except Exception as exc:
            logger.error(f"Failed generating doctor list response: {exc}")
            reply = "Here are the doctors I found for you: " + ", ".join(d.name for d in doctors)

        return ChatResponseData(
            type=ResponseType.chat,
            message=reply,
            risk_level=Urgency.low,
            follow_up_questions=[],
            structured=None,
        )

    async def generate_response_raw(self, prompt: str) -> str:
        """Reusable function to generate a raw text response from the LLM."""
        msg = await self._invoke([HumanMessage(content=prompt)], operation="generate_response_raw")
        return (getattr(msg, "content", None) or str(msg)).strip()

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
            msg = await self._invoke(
                [
                    SystemMessage(content="You extract structured medical information."),
                    HumanMessage(content=prompt),
                ],
                operation="analyze_input",
            )
            text = (getattr(msg, "content", None) or str(msg)).strip()

            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                text = m.group(0)
            return json.loads(text)
        except QuotaExceededError:
            raise
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

        medical_context_str = ""
        if getattr(session, "medical_context", None):
            filtered_context = ContextFilter.filter_relevant_context(
                session.symptoms, session.medical_context
            )
            if filtered_context:
                mc_lines = [f"* {k.capitalize()}: {v}" for k, v in filtered_context.items()]
                medical_context_str = "Patient Medical Context:\n" + "\n".join(mc_lines) + "\n\n"

        if not is_final:
            prompt = """
            Based on the conversation so far, ask 1 follow-up question to gather a missing medical detail
            (e.g., severity, duration, related symptoms, or body location).

            IMPORTANT — Response rules:
            - If this is the FIRST response after symptoms were described, include a BRIEF empathy sentence.
            - Otherwise, be direct and natural.
            - Ask ONLY 1 question.

            IMPORTANT — UI component rules:
            Choose the most appropriate UI widget for the patient to answer:
            * "radio"    → the question has MUTUALLY EXCLUSIVE answers the patient picks ONE of.
                           Use for: severity (Mild/Moderate/Severe), yes/no, duration ranges, single location.
            * "checkbox" → the patient may select MULTIPLE answers.
                           Use for: additional symptoms present, body areas affected.
            * "text"     → the question is open-ended and does not fit a fixed option list.

            If type is "radio" or "checkbox", provide 3–5 short, distinct options in the user's language.
            Always set allow_other to true so the patient can type freely if none fit.

            Return ONLY valid JSON in this exact format:
            {
                "message": "A single conversational string with the follow-up question in the user's language.",
                "follow_up_questions": ["The same question rephrased concisely (in user's language)"],
                "ui_component": {
                    "type": "radio" | "checkbox" | "text",
                    "options": ["Option 1", "Option 2", "Option 3"],
                    "allow_other": true
                }
            }
            """
            try:
                msg = await self._invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(
                            content=f"{medical_context_str}Chat history:\n{history_str}\n\nTask: {prompt}"
                        ),
                    ],
                    operation="generate_response",
                )
                text = (getattr(msg, "content", None) or str(msg)).strip()
                m = re.search(r"\{[\s\S]*\}", text)
                if m:
                    text = m.group(0)
                data = json.loads(text)

                # Parse the ui_component block returned by the LLM
                ui_raw = data.get("ui_component", {})
                try:
                    ui_type = UIComponentType(ui_raw.get("type", "text"))
                except ValueError:
                    ui_type = UIComponentType.text
                ui = UIComponent(
                    type=ui_type,
                    options=ui_raw.get("options", []),
                    allow_other=ui_raw.get("allow_other", True),
                )

                return ChatResponseData(
                    type=ResponseType.chat,
                    message=data.get("message", "Could you tell me a little more about your symptoms?"),
                    risk_level=Urgency.medium,
                    follow_up_questions=data.get("follow_up_questions", []),
                    structured=None,
                    ui=ui,
                )
            except QuotaExceededError:
                raise
            except Exception as exc:
                logger.error(f"Failed asking follow-up: {exc}")
                return ChatResponseData(
                    type=ResponseType.chat,
                    message="Could you tell me a little more about your symptoms?",
                    risk_level=Urgency.medium,
                    follow_up_questions=["Can you describe your symptoms in more detail?"],
                    structured=None,
                    ui=UIComponent(type=UIComponentType.text),
                )

        prompt = """
            Analyze the gathered symptoms and chat history.
            
            # Behavior Rules
            - Use medical context to IMPROVE reasoning.
            - Do NOT blindly rely on it.
            - Do NOT produce a diagnosis.
            - Adjust possible causes based on history.
            
            Return ONLY valid JSON in this exact format:
            {
                "message": "A brief conclusion message in the user's language. If medical history is relevant, optionally include 'Based on your medical history (e.g. diabetes), your symptoms may be related to...'",
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
            msg = await self._invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=(
                            f"{medical_context_str}"
                            f"Chat history:\n{history_str}\n\n"
                            f"Symptoms: {symptoms_str}\n"
                            f"Duration: {session.duration}\n"
                            f"Task: {prompt}"
                        )
                    ),
                ],
                operation="generate_response",
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
                risk=struct_data.get("risk", "Medium physical risk"),
            )

            return ChatResponseData(
                type=ResponseType.chat,
                message=data.get(
                    "message", "I have generated a structured medical report based on your symptoms."
                ),
                risk_level=risk_val,
                follow_up_questions=[],
                structured=structured,
            )

        except QuotaExceededError:
            raise
        except Exception as exc:
            logger.exception("Failed generating final response")
            return ChatResponseData(
                type=ResponseType.chat,
                message="I wasn't able to generate a detailed report right now. Please reach out to a healthcare professional.",
                risk_level=Urgency.medium,
                follow_up_questions=[],
                structured=None,
            )
