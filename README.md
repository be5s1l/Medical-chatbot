# Medical-Chatbot (monorepo folder)

The application code lives in **`medical_chatbot/`**.

## Run the API (from this folder)

**Option A — launcher (recommended):**

```powershell
.\start-api.ps1
```

**Option B — manual:**

```powershell
cd .\medical_chatbot
..\.\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload
```

If you run `uvicorn src.main:app` from **this** directory instead of `medical_chatbot/`, you will get `ModuleNotFoundError: No module named 'src'`.

Full setup and Streamlit instructions: see [medical_chatbot/README.md](medical_chatbot/README.md).
