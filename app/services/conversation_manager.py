from typing import Dict, List

from app.models.schemas import SessionState


class ConversationManager:
    def __init__(self) -> None:
        # In-memory dictionary to store active conversation sessions
        self.sessions: Dict[str, SessionState] = {}

    def get_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id=session_id)
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_session(session_id)
        session.messages.append({"role": role, "content": content})

    def update_session(self, session_id: str, new_symptoms: List[str], duration: str) -> None:
        session = self.get_session(session_id)
        current_symptoms = set(session.symptoms)
        
        for symptom in new_symptoms:
            current_symptoms.add(symptom)
            
        session.symptoms = list(current_symptoms)
        
        if duration:
            session.duration = duration
