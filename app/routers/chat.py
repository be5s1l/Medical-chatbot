from __future__ import annotations

from fastapi import APIRouter
from loguru import logger

from app.models.schemas import ChatRequest, ChatResponseData, APIResponse, ErrorDetail, Urgency
from app.services.conversation_manager import ConversationManager
from app.services.llm_service import LLMService, QuotaExceededError
from app.services.risk_engine import RiskEngine

router = APIRouter(tags=["Chat"])

# Singletons for memory and LLM logic
_conversation_manager = ConversationManager()
_llm_service: LLMService | None = None

def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


@router.post("/api/v1/chat", response_model=APIResponse)
async def chat(body: ChatRequest):
    try:
        session_id = body.session_id
        user_text = body.message
        
        # 1. Rule-based emergency check FIRST
        if RiskEngine.check_emergency(user_text):
            # Emergency override route: short circuits standard handling
            emergency_message = "Your symptoms may indicate a medical emergency. Please call emergency services (911 / 112) or go to the nearest emergency room immediately. Do not stay alone."
            data = ChatResponseData(
                message=emergency_message,
                risk_level=Urgency.emergency,
                follow_up_questions=[],
                structured=None
            )
            return APIResponse(success=True, data=data)
            
        # 2. Add message to context
        logger.info(f"[INFO] New request received - Session: {session_id}")
        logger.info(f"[INFO] User: \"{user_text}\"")
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
        
        # 5. Determine whether to ask follow-up or generate Final response
        # Removed bot message limit as per requirement (no session limits)
        is_final = has_enough_info
        
        # 6. Generate Context-Aware Response
        llm_response = await llm_service.generate_response(session, is_final=is_final)
        
        # Add generated answer to history
        logger.info(f"[INFO] Bot: \"{llm_response.message}\"")
        _conversation_manager.add_message(session_id, "assistant", llm_response.message)
            
        return APIResponse(success=True, data=llm_response)

    except QuotaExceededError as exc:
        logger.error(f"[ERROR] Quota Exceeded: {exc}")
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="QUOTA_EXCEEDED",
                message="The Gemini API token limit has been reached. Please try again later."
            )
        )
    except Exception as exc:
        logger.error(f"[ERROR] Exception: {exc}")
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=str(exc)
            )
        )
