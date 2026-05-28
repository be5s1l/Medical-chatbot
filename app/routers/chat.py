from __future__ import annotations

from fastapi import APIRouter
from loguru import logger

from app.models.schemas import ChatRequest, ChatResponseData, APIResponse, ErrorDetail, Urgency, ResponseType
from app.services.conversation_manager import ConversationManager
from app.services.llm_service import LLMService, QuotaExceededError
from app.services.gemini_quota import enrich_quota_error
from app.services.risk_engine import RiskEngine

router = APIRouter(tags=["Chat"])

_conversation_manager = ConversationManager()
_llm_service: LLMService | None = None

# Ordered pipeline steps for quota progress logging and resume guidance.
_PIPELINE_STEPS = [
    "Emergency keyword screening",
    "Doctor-search intent detection via Gemini (llm_service.detect_doctor_intent)",
    "User message stored in session",
    "Symptom analysis via Gemini (llm_service.analyze_input)",
    "Session updated with symptoms and medical context",
    "Risk level assessed from symptoms",
    "Chat response via Gemini (llm_service.generate_response)",
]

_OPERATION_FAILED_INDEX = {
    "detect_doctor_intent": 1,
    "analyze_input": 3,
    "generate_response": 6,
    "generate_response_raw": 6,
    "generate_response_for_doctors": 6,
}

_OPERATION_RESUME = {
    "detect_doctor_intent": (
        "POST /api/v1/chat with the same session_id and message "
        "(re-runs from llm_service.detect_doctor_intent)"
    ),
    "analyze_input": (
        "POST /api/v1/chat with the same session_id and message "
        "(re-runs from llm_service.analyze_input)"
    ),
    "generate_response": (
        "POST /api/v1/chat with the same session_id and message "
        "(session state is saved; re-runs from llm_service.generate_response)"
    ),
    "generate_response_for_doctors": (
        "POST /api/v1/chat with the same session_id, empty message, and tool_result "
        "(re-runs from llm_service.generate_response_for_doctors)"
    ),
    "generate_response_raw": "llm_service.generate_response_raw(prompt)",
}


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def _build_quota_progress(operation: str, *, is_final: bool | None = None) -> tuple[list[str], list[str], str]:
    failed_index = _OPERATION_FAILED_INDEX.get(operation, len(_PIPELINE_STEPS) - 1)
    completed = list(_PIPELINE_STEPS[:failed_index])
    remaining = list(_PIPELINE_STEPS[failed_index:])
    if operation == "generate_response" and is_final is not None:
        mode = "final structured diagnosis" if is_final else "follow-up questions"
        remaining = [f"{step} [{mode}]" if "generate_response" in step else step for step in remaining]
    resume = _OPERATION_RESUME.get(operation, f"llm_service (operation={operation})")
    return completed, remaining, resume


@router.post("/api/v1/chat", response_model=APIResponse)
async def chat(body: ChatRequest):
    session_id = body.session_id
    user_text = body.message
    is_final: bool | None = None

    try:
        llm_service = get_llm_service()

        # ---------------------------------------------------------------
        # Branch B — Client is returning doctor results from the .NET backend.
        # Skip the symptom pipeline entirely; ask the AI to present the list.
        # ---------------------------------------------------------------
        if body.tool_result and body.tool_result.tool == "get_doctors":
            logger.info(
                "[AGENT] tool_result received for 'get_doctors' | session={} | doctors={}",
                session_id,
                len(body.tool_result.doctors),
            )
            session = _conversation_manager.get_session(session_id)
            llm_response = await llm_service.generate_response_for_doctors(
                session, body.tool_result.doctors
            )
            logger.info(f"[AGENT] Doctor list presented to patient: \"{llm_response.message}\"")
            _conversation_manager.add_message(session_id, "assistant", llm_response.message)
            return APIResponse(success=True, data=llm_response)

        # ---------------------------------------------------------------
        # Normal flow — process patient message
        # ---------------------------------------------------------------
        if RiskEngine.check_emergency(user_text):
            emergency_message = (
                "Your symptoms may indicate a medical emergency. Please call emergency services "
                "(911 / 112) or go to the nearest emergency room immediately. Do not stay alone."
            )
            data = ChatResponseData(
                type=ResponseType.chat,
                message=emergency_message,
                risk_level=Urgency.emergency,
                follow_up_questions=[],
                structured=None,
            )
            return APIResponse(success=True, data=data)

        logger.info(f"[INFO] New request received - Session: {session_id}")
        logger.info(f"[INFO] User: \"{user_text}\"")
        _conversation_manager.add_message(session_id, "user", user_text)

        # ---------------------------------------------------------------
        # Branch A — Detect doctor-search intent before symptom analysis.
        # If the patient wants a doctor, return a get_doctors tool call immediately.
        # ---------------------------------------------------------------
        doctor_params = await llm_service.detect_doctor_intent(user_text)
        if doctor_params is not None:
            logger.info(
                "[AGENT] Doctor intent detected | session={} | specialization={} | location={} | min_rating={}",
                session_id,
                doctor_params.specialization,
                doctor_params.location,
                doctor_params.min_rating,
            )
            tool_call_message = "Let me find the right doctor for you."
            _conversation_manager.add_message(session_id, "assistant", tool_call_message)
            data = ChatResponseData(
                type=ResponseType.get_doctors,
                message=tool_call_message,
                risk_level=Urgency.low,
                follow_up_questions=[],
                structured=None,
                search_params=doctor_params,
            )
            return APIResponse(success=True, data=data)

        # ---------------------------------------------------------------
        # Symptom analysis pipeline (unchanged)
        # ---------------------------------------------------------------
        analysis = await llm_service.analyze_input(user_text)
        symptoms = analysis.get("symptoms", [])
        duration = analysis.get("duration", "")
        has_enough_info = analysis.get("has_enough_info", False)

        medical_context_dict = body.medical_context.model_dump() if body.medical_context else None
        _conversation_manager.update_session(session_id, symptoms, duration, medical_context_dict)
        session = _conversation_manager.get_session(session_id)

        session.risk_level = RiskEngine.assess_risk(session.symptoms).value

        is_final = has_enough_info
        llm_response = await llm_service.generate_response(session, is_final=is_final)

        logger.info(f"[INFO] Bot: \"{llm_response.message}\"")
        _conversation_manager.add_message(session_id, "assistant", llm_response.message)

        return APIResponse(success=True, data=llm_response)

    except QuotaExceededError as exc:
        completed, remaining, resume = _build_quota_progress(
            exc.operation or "unknown",
            is_final=is_final,
        )
        enrich_quota_error(exc, completed=completed, remaining=remaining, resume_point=resume)

        logger.error(
            "[QUOTA] Gemini quota exhausted | session={} | operation={} | completed={} | remaining={} | resume={}",
            session_id,
            exc.operation,
            exc.completed,
            exc.remaining,
            exc.resume_point,
        )

        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="QUOTA_EXCEEDED",
                message=exc.format_user_message(),
            ),
        )
    except RuntimeError as exc:
        # Common production misconfiguration: GEMINI_API_KEY not injected into the runtime environment.
        if str(exc) == "GEMINI_API_KEY is not set":
            return APIResponse(
                success=False,
                data=None,
                error=ErrorDetail(
                    code="CONFIGURATION_ERROR",
                    message=(
                        "GEMINI_API_KEY is not set. If deploying to Railway, add GEMINI_API_KEY "
                        "to the service Variables and redeploy."
                    ),
                ),
            )
        raise
    except Exception as exc:
        logger.error(f"[ERROR] Exception: {exc}")
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=str(exc),
            ),
        )
