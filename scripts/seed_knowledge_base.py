import sys
from pathlib import Path

# Allow `python scripts/seed_knowledge_base.py` from repo `medical_chatbot/` folder
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.medical_knowledge_snippets import MEDICAL_DOCUMENTS
from src.infrastructure.vector_db.chroma_service import ChromaDBService


if __name__ == "__main__":
    db = ChromaDBService()
    db.add_documents(MEDICAL_DOCUMENTS)
    print(f"Seeded {len(MEDICAL_DOCUMENTS)} documents into ChromaDB")

