import re

from src.core.constants import DEFAULT_DISCLAIMER, VITAL_RANGES
from src.domain.entities.triage import TriageLevel
from src.helpers.safety_layer import inject_disclaimer
from src.infrastructure.llm.langchain_chain import MedicalRAGChain


class VitalsController:
    def __init__(self) -> None:
        self.rag = MedicalRAGChain()

    def process(self, payload: dict) -> dict:
        abnormal: list[str] = []
        level = TriageLevel.SELF_CARE

        def escalate(new: TriageLevel) -> None:
            nonlocal level
            level = new if new.value < level.value else level

        bp = payload.get("blood_pressure")
        if bp:
            sys_d, dia_d = self._parse_bp(str(bp))
            if sys_d is not None and dia_d is not None:
                if sys_d >= 180 or dia_d >= 120:
                    abnormal.append(f"Blood pressure very high: {bp}")
                    escalate(TriageLevel.EMERGENCY)
                elif sys_d >= 140 or dia_d >= 90:
                    abnormal.append(f"Blood pressure elevated: {bp}")
                    escalate(TriageLevel.SEMI_URGENT)

        hr = payload.get("heart_rate")
        if hr is not None:
            r = VITAL_RANGES["heart_rate"]
            if hr <= r["emergency_low"] or hr >= r["emergency_high"]:
                abnormal.append(f"Heart rate concerning: {hr} bpm")
                escalate(TriageLevel.URGENT)
            elif hr < r["low"] or hr > r["high"]:
                abnormal.append(f"Heart rate outside typical resting range: {hr} bpm")
                escalate(TriageLevel.NON_URGENT)

        glu = payload.get("glucose_level")
        if glu is not None:
            r = VITAL_RANGES["glucose_level"]
            if glu <= r["emergency_low"] or glu >= r["emergency_high"]:
                abnormal.append(f"Glucose level concerning: {glu}")
                escalate(TriageLevel.URGENT)
            elif glu < r["low"] or glu > r["high"]:
                abnormal.append(f"Glucose outside common target range: {glu}")
                escalate(TriageLevel.SEMI_URGENT)

        temp = payload.get("temperature")
        if temp is not None:
            r = VITAL_RANGES["temperature_c"]
            if temp <= r["emergency_low"] or temp >= r["emergency_high"]:
                abnormal.append(f"Temperature concerning: {temp} °C")
                escalate(TriageLevel.URGENT)
            elif temp < r["low"] or temp > r["high"]:
                abnormal.append(f"Fever or low temp noted: {temp} °C")
                escalate(TriageLevel.SEMI_URGENT)

        vitals_text = "\n".join(f"{k}: {v}" for k, v in payload.items() if v is not None)
        try:
            llm = self.rag.advise_vitals(vitals_text or "No vitals provided.")
        except Exception:
            llm = "Compare your readings with your clinician's targets. When in doubt, seek medical advice."

        if not abnormal:
            abnormal.append("No obvious red-flag ranges detected by rule checks (this is not a diagnosis).")

        response = inject_disclaimer(
            f"Rule-based triage hint: {level.name.replace('_', ' ').title()}.\n\n{llm}"
        )
        return {
            "triage_level": int(level),
            "abnormal_readings": abnormal,
            "response": response,
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    def _parse_bp(self, s: str) -> tuple[int | None, int | None]:
        m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", s)
        if not m:
            return None, None
        return int(m.group(1)), int(m.group(2))
