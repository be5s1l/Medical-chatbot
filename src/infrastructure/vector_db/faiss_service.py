"""Simple in-memory fallback when FAISS/Chroma is not used (no semantic search)."""

from src.domain.interfaces.vector_db import IVectorDB


class FAISSService(IVectorDB):
    def __init__(self) -> None:
        self._docs: list[dict] = []

    def add_documents(self, docs: list[dict]) -> None:
        self._docs.extend(docs)

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        _ = query
        return self._docs[:n_results]
