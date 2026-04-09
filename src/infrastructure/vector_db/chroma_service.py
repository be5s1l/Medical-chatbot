import uuid

from src.core.config import settings
from src.domain.interfaces.vector_db import IVectorDB


class ChromaDBService(IVectorDB):
    """ChromaDB-backed vector store. Imports `chromadb` lazily to avoid heavy/grpc imports at app load."""

    COLLECTION_NAME = "medical_knowledge"

    def __init__(self) -> None:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        emb_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=emb_fn,
        )

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        results = self.collection.query(query_texts=[query], n_results=n_results)
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        out: list[dict] = []
        for doc, meta in zip(documents, metadatas):
            meta = meta or {}
            out.append({"text": doc, "source": meta.get("source", "Unknown")})
        return out

    def add_documents(self, docs: list[dict]) -> None:
        if not docs:
            return
        self.collection.add(
            documents=[d["text"] for d in docs],
            metadatas=[{"source": d.get("source", "")} for d in docs],
            ids=[str(uuid.uuid4()) for _ in docs],
        )
