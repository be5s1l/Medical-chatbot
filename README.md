## AI Medical Chatbot (v1)

**Important**: This system is a triage assistant only. It does **not** diagnose, prescribe, or replace licensed medical professionals. Every user-facing path should reinforce that users must consult a qualified clinician.

### Recommended runtime

- **Python**: 3.10 or 3.11 is the most compatible choice for scientific stacks (PyTorch, some wheels). Python 3.12+ can work but you may need to adjust versions.
- **OpenAI**: set `OPENAI_API_KEY` for RAG + document/vitals explanations.
- **Tesseract**: install the Windows binary and point `TESSERACT_PATH` at `tesseract.exe`.

### 1) Setup (Windows PowerShell)

From the `medical_chatbot/` folder (or create the venv one level up and use it here):

```powershell
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in `medical_chatbot/` (do not commit). You can start from `.env.example`.

```env
OPENAI_API_KEY=sk-...   # only needed if LLM_PROVIDER=openai
HUGGINGFACE_TOKEN=hf_...
CHROMA_DB_PATH=./data/chroma_db
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
LOG_LEVEL=DEBUG
EMERGENCY_KEYWORDS=chest pain,stroke,unconscious,severe bleeding,can't breathe
# LLM backend: use local Ollama instead of OpenAI:
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
# Optional: return the real error message in JSON `detail` on 500 (local dev only)
APP_DEBUG=true
```

Always start the API from the **`medical_chatbot/`** folder so `.env` is found (same folder as `uvicorn`).

### 2) Seed the knowledge base (required for RAG)

```powershell
python .\scripts\seed_knowledge_base.py
```

### 3) Run the API

```powershell
uvicorn src.main:app --reload
```

Open Swagger UI at `http://localhost:8000/docs`.

### 4) Run the Streamlit app

Second terminal, from `medical_chatbot/`:

```powershell
streamlit run .\apps\streamlit_app\app.py
```

Optional: `API_BASE_URL` if the API is not on localhost.

### 5) Run tests

From `medical_chatbot/`:

```powershell
pytest tests -v
```

### 6) Docker

From `medical_chatbot/` (requires Docker Desktop):

```powershell
docker compose up --build
```

Ensure `.env` exists beside `docker-compose.yml` (or remove `env_file` from the compose file).

### Optional: CheXNet / X-ray stack

Install PyTorch + `torchxrayvision` per your platform, then:

```powershell
pip install -r requirements-vision.txt
```

Without this, `/upload/image` still returns a safe placeholder explaining that the vision stack is unavailable.

### API summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/chat` | Symptom triage + RAG |
| POST | `/upload/document` | PDF text + summary |
| POST | `/upload/image` | Image classification (when vision deps installed) |
| POST | `/upload/vitals` | Vitals rules + LLM explanation |

### Presentation checklist

1. Show deterministic emergency escalation (e.g. “chest pain” → emergency copy, no RAG).
2. Show a normal symptom query with retrieved sources in the model output (after seeding).
3. Upload a **de-identified** sample PDF and a sample image.
4. Submit vitals that trigger rule-based escalation (e.g. high BP).
5. State the safety disclaimer aloud and in slides.

### Troubleshooting

- **`500 Internal Server error` on `/chat`**: Check the **terminal where `uvicorn` is running** — the full traceback is logged. Common causes:
  1. **`OPENAI_API_KEY` missing or wrong** — add it to `.env` in `medical_chatbot/`, or set `$env:OPENAI_API_KEY` in PowerShell before `uvicorn`.
  2. **Wrong working directory** — run `uvicorn` from `medical_chatbot/` so `.env` loads.
  3. **Chroma / embeddings failing** (Windows DLL / gRPC) — see below; you may see errors when querying the vector DB.
  4. **No credits / billing** on the OpenAI account — the API returns an error until billing is enabled.
- **See the real error in the HTTP response (dev only)**: set `APP_DEBUG=true` in `.env`, restart uvicorn; the JSON `detail` field will contain the exception message.
- **Chroma / gRPC / NumPy DLL errors on locked-down Windows**: corporate Application Control can block native DLLs. Use Docker, a different machine, or Python 3.11 from python.org (non-Store).
- **Empty RAG answers**: run the seed script and confirm `CHROMA_DB_PATH` matches the API process.
