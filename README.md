# AI Medical Chatbot Microservice

This repository contains an AI-powered Medical Chatbot microservice designed specifically for integration with other backends (such as .NET) and frontend applications (such as Flutter).

> **Note:** This API is completely stateless and headless. There is no graphical user interface (UI) included. State is managed via `session_id` identifiers.

## Architecture Structure
The intended production flow is:
**Flutter frontend (Client)** ↔ **.NET (Main Backend)** ↔ **FastAPI (AI Microservice)**

The AI microservice specializes **only** in:
- AI medical reasoning.
- Analyzing symptoms.
- Continuous dialogue and follow-up question generation.
- Risk and urgency assessment.

It **does not handle**:
- Authentication / Authorization.
- Database persistance.
- User interface rendering.

## Features
- **Symptom analysis:** Extracts multi-symptom descriptions and infers duration/severity.
- **Multi-turn conversation:** Evaluates if sufficient context is available. If not, it requests precise follow-up questions from the user.
- **Risk scoring:** Continuously scores risk levels (`LOW`, `MEDIUM`, `HIGH`, `EMERGENCY`) and escalates automatically.
- **Format Integrity:** Outputs strict, clean JSON. Does not generate emojis, markup, or chat UI artifacts.

## Medical Record Integration
The AI microservice integrates securely with medical records provided by the .NET backend. 
- **Data Source:** Medical data is received as part of the `ChatRequest` payload via the `medical_context` field. The .NET backend acts as the sole source of truth.
- **Enhanced Reasoning:** When provided, the AI filters relevant conditions, medications, and labs, injecting them into its prompt context to offer highly personalized possible causes and advice.
- **Ephemeral Storage:** Medical data is **not permanently stored** by this microservice. It is kept only in memory tied to the active `session_id`.

## Setup Instructions

### Requirements
- Python 3.10+
- A valid Gemini API Key

### Installation

1. Create a virtual environment (optional but recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # Or `.venv\Scripts\activate` on Windows
```

2. Install dependencies:
```bash
cd medical_chatbot
pip install -r requirements.txt
```

3. Configure Environment Variables:
Copy `.env.example` to `.env` and assign your keys:
```env
# medical_chatbot/.env
GEMINI_API_KEY="your-gemini-key-here"
```

### Running the server

```bash
cd medical_chatbot
uvicorn main:app --reload
```

## API Documentation

The API uses standard structured wrappers. A swagger UI representation is available at `/docs` when the API is running locally.

### Start a Chat Evaluation
**Endpoint:** `POST /api/v1/chat`

#### Request body Example
```json
{
  "session_id": "0df0bf86-53d9-4cfc-b4db-5ec9de032ae2",
  "message": "I've had a headache for 3 days and my vision is suddenly blurry.",
  "type": "text",
  "metadata": {
    "age": 32,
    "gender": "male"
  }
}
```

#### Response body Example (Follow-up)
*If the AI reasons it does not have enough context yet.*
```json
{
  "success": true,
  "data": {
    "message": "Could you tell me if you are experiencing any nausea or light sensitivity with the headache?",
    "risk_level": "HIGH",
    "follow_up_questions": [
      "Are you experiencing any nausea?",
      "Are you sensitive to light?"
    ],
    "structured": null
  },
  "error": null
}
```

#### Response body Example (Structured Result)
*If the AI reasons it has comprehensive information or after several turns.*
```json
{
  "success": true,
  "data": {
    "message": "I've analyzed your symptoms and generated a structured response regarding your vision and headache.",
    "risk_level": "HIGH",
    "follow_up_questions": [],
    "structured": {
      "summary": "Patient is experiencing a 3-day history of headaches accompanied by a sudden onset of blurry vision.",
      "possible_causes": [
        "Migraine with aura",
        "Elevated intracranial pressure",
        "Severe hypertension"
      ],
      "advice": [
        "Rest in a quiet, dark room.",
        "Avoid looking at screens.",
        "Seek medical attention promptly given the sudden visual changes."
      ],
      "when_to_worry": [
        "Loss of consciousness",
        "Weakness in the limbs",
        "Difficulty speaking"
      ],
      "recommended_doctors": [
        "Ophthalmologist",
        "Neurologist",
        "Emergency Medicine Physician"
      ],
      "risk": "High physical risk; sudden blurry vision coupled with headache requires urgent clinical evaluation."
    }
  },
  "error": null
}
```

#### Error Response Example
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Description of the error"
  }
}
```
