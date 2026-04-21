import os

import requests
import streamlit as st

# Keep in sync with `src/core/constants.py` (Streamlit often runs without PYTHONPATH).
DEFAULT_DISCLAIMER = (
    "IMPORTANT: This AI assistant provides general health information only. "
    "It does NOT diagnose medical conditions or replace professional medical advice. "
    "Always consult a qualified healthcare provider for medical decisions."
)


st.set_page_config(page_title="AI Medical Chatbot (Triage)", layout="centered")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.title("AI Medical Triage Assistant")
st.caption(
    "This tool provides general triage guidance only. It does not diagnose or replace a licensed clinician."
)

with st.sidebar:
    st.subheader("Safety disclaimer")
    st.markdown(DEFAULT_DISCLAIMER)
    st.divider()
    st.caption(f"API: `{API_BASE_URL}`")

st.info(
    "If you may be experiencing a medical emergency (e.g., chest pain, trouble breathing, stroke symptoms), "
    "call your local emergency number or go to the nearest emergency department.",
    icon="ℹ️",
)

# Frontend note: the production chat UI lives in the web frontend.
# This Streamlit app is kept as a minimal API smoke-test client.
st.subheader("Chat (API smoke test)")

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg.get("is_final") and msg["role"] == "assistant":
            st.json(msg["content"])
        else:
            st.markdown(msg["content"])

query = st.chat_input("Describe your symptoms (e.g., I've had a sore throat...)")

if query:
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
        
    try:
        with st.spinner("Thinking..."):
            resp = requests.post(
                f"{API_BASE_URL}/chat",
                json={"session_id": st.session_state.session_id, "query": query},
                timeout=(10, 300),  # connect, read
            )
        if resp.ok:
            data = resp.json()
            is_final = data.get("is_final", False)
            
            with st.chat_message("assistant"):
                if is_final:
                    st.json(data)
                    st.session_state.chat_history.append({"role": "assistant", "content": data, "is_final": True})
                else:
                    msg_text = data.get("message", "")
                    st.markdown(msg_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": msg_text, "is_final": False})
                    
        else:
            st.error(f"API error: {resp.status_code} {resp.text}")
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")

