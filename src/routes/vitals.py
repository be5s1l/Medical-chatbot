from fastapi import APIRouter, HTTPException
from loguru import logger

from src.controllers.vitals_analysis import VitalsController
from src.helpers.validators import VitalsRequest, VitalsResponse

router = APIRouter(prefix="/upload", tags=["Vitals"])

_vitals_controller: VitalsController | None = None


def get_vitals_controller() -> VitalsController:
    global _vitals_controller
    if _vitals_controller is None:
        _vitals_controller = VitalsController()
    return _vitals_controller


def _clean_vitals(body: VitalsRequest) -> dict:
    d = body.model_dump()
    if d.get("heart_rate") == 0:
        d["heart_rate"] = None
    if d.get("glucose_level") == 0:
        d["glucose_level"] = None
    if d.get("temperature") == 0:
        d["temperature"] = None
    if d.get("blood_pressure") == "":
        d["blood_pressure"] = None
    return d


@router.post("/vitals", response_model=VitalsResponse)
async def upload_vitals(request: VitalsRequest):
    try:
        payload = _clean_vitals(request)
        out = get_vitals_controller().process(payload)
        return VitalsResponse(**out)
    except Exception as e:
        logger.error("Vitals error: {}", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
