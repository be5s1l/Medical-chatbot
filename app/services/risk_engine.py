from app.models.schemas import SessionState, Urgency


class RiskEngine:
    @staticmethod
    def check_emergency(text: str) -> bool:
        """
        Rule-based emergency detection based on predefined keywords.
        """
        emergency_keywords = [
            "chest pain",
            "shortness of breath",
            "severe bleeding",
            "unconscious",
            "unconsciousness",
            "passing out",
            "fainting",
            "can't breathe",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in emergency_keywords)

    @staticmethod
    def assess_risk(symptoms: list[str]) -> Urgency:
        """
        Assess risk level from symptoms matching against predefined severity levels.
        """
        high_keywords = ["fainting", "severe pain", "vision loss", "paralysis", "weakness"]
        medium_keywords = ["dizziness", "fever", "vomiting", "nausea", "migraine"]
        
        symptoms_text = " ".join(symptoms).lower()
        
        for keyword in high_keywords:
            if keyword in symptoms_text:
                return Urgency.high
                
        for keyword in medium_keywords:
            if keyword in symptoms_text:
                return Urgency.medium
                
        # Default to low if no major keywords present
        return Urgency.low
