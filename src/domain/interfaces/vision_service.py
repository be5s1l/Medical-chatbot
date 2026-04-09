from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    label: str
    confidence: float
    findings: list[str] | None = None


class IVisionService(ABC):
    @abstractmethod
    def classify(self, image_path: str) -> ClassificationResult:
        raise NotImplementedError

