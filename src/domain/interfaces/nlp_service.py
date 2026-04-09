from abc import ABC, abstractmethod

from src.domain.entities.symptom import SymptomEntity


class INLPService(ABC):
    @abstractmethod
    def extract_symptoms(self, text: str) -> list[SymptomEntity]:
        raise NotImplementedError

    @abstractmethod
    def summarize(self, text: str, max_length: int = 200) -> str:
        raise NotImplementedError

