DEFAULT_DISCLAIMER = (
    "IMPORTANT: This AI assistant provides general health information only. "
    "It does NOT diagnose medical conditions or replace professional medical advice. "
    "Always consult a qualified healthcare provider for medical decisions."
)

# Simple v1 ranges (not medical-grade; triage heuristics only)
VITAL_RANGES = {
    "heart_rate": {"low": 50, "high": 110, "emergency_low": 40, "emergency_high": 140},
    "glucose_level": {"low": 70, "high": 180, "emergency_low": 54, "emergency_high": 300},
    "temperature_c": {"low": 36.0, "high": 38.0, "emergency_low": 35.0, "emergency_high": 40.0},
}

