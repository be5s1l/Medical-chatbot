from abc import ABC, abstractmethod


class IVectorDB(ABC):
    @abstractmethod
    def search(self, query: str, n_results: int = 5) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def add_documents(self, docs: list[dict]) -> None:
        raise NotImplementedError

