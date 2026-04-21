from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.schemas import ChatRequest, ChatResponse, Urgency
from app.services.conversation_manager import ConversationManager
from app.services.llm_service import LLMService
from app.services.risk_engine import RiskEngine
from src.core.config import settings

router = APIRouter(tags=["Chat"])

# Singletons for services
_conversation_manager = ConversationManager()
_llm_service: LLMService | None = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        session_id = body.session_id
        user_text = body.query
        
        # 1. Rule-based emergency check FIRST
        if RiskEngine.check_emergency(user_text):
            # Emergency override route
            emergency_message = (
                "Hi, I'm MediBot 👋\n"
                "I'm very concerned about what you've described — please take this seriously.\n\n"
                "🧠 Summary\n"
                "Your symptoms may indicate a medical emergency that requires immediate attention.\n\n"
                "💡 What You Can Do\n"
                "• 🚨 Call emergency services (911 / 15 / 112) right now\n"
                "• 🚗 Go to the nearest emergency room immediately\n"
                "• 🧍 Do not stay alone — ask someone to stay with you\n\n"
                "⚠️ When to Be Concerned\n"
                "• You are already in a situation that needs urgent care\n\n"
                "🩺 Recommended Doctor\n"
                "Emergency Medicine Specialist — go to the ER now\n\n"
                "📊 Risk Level: ⚠️ Emergency\n\n"
                "This is not a medical diagnosis. Please consult a healthcare professional."
            )
            return ChatResponse(
                message=emergency_message,
                is_final=True,
                risk_level=Urgency.emergency,
                disclaimer="This is not a medical diagnosis. Please consult a healthcare professional.",
            )
            
        # 2. Add message to context
        _conversation_manager.add_message(session_id, "user", user_text)
        
        # 3. Analyze LLM for symptoms
        llm_service = get_llm_service()
        analysis = await llm_service.analyze_input(user_text)
        symptoms = analysis.get("symptoms", [])
        duration = analysis.get("duration", "")
        has_enough_info = analysis.get("has_enough_info", False)
        
        # Update session memory
        _conversation_manager.update_session(session_id, symptoms, duration)
        session = _conversation_manager.get_session(session_id)
        
        # 4. Continually assess risk based on growing symptom tracker
        session.risk_level = RiskEngine.assess_risk(session.symptoms).value
        
        # 5. Decide to ask follow-up questions vs. generate response
        bot_msgs_count = sum(1 for m in session.messages if m["role"] == "assistant")
        
        # Ask at most 2 follow-ups if we don't have enough info
        is_final = has_enough_info or (bot_msgs_count >= 2)
        
        # 6. Generate Context-Aware Response
        llm_response = await llm_service.generate_response(session, is_final=is_final)
        
        # Add generated answer to history
        if not is_final:
            _conversation_manager.add_message(session_id, "assistant", llm_response.get("message", ""))
        else:
            _conversation_manager.add_message(session_id, "assistant", "Final structured medical response delivered.")
            
        return ChatResponse(**llm_response)

    except Exception as exc:
        logger.exception("Chat error")
        detail = str(exc) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from exc
