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

tab_chat, tab_vitals, tab_uploads = st.tabs(["Symptom chat", "Vitals", "Uploads"])

with tab_chat:
    query = st.text_area("Describe your symptoms", placeholder="Example: I've had a sore throat and mild cough for 2 days.")
    if st.button("Send", type="primary", disabled=not query.strip()):
        try:
            with st.spinner("Thinking... (first run can take a minute)"):
                resp = requests.post(
                    f"{API_BASE_URL}/chat",
                    json={"query": query},
                    timeout=(10, 300),  # connect, read
                )
            if resp.ok:
                data = resp.json()
                st.subheader("Response")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Triage level (1=emergency)", data.get("triage_level", "—"))
                with c2:
                    st.caption("Conditions (extracted)")
                    conditions = data.get("conditions") or []
                    if isinstance(conditions, list) and conditions:
                        st.markdown("\n".join([f"- {c}" for c in conditions]))
                    else:
                        st.caption("None detected")
                st.write(data.get("response", ""))
                st.caption(data.get("disclaimer", ""))
            else:
                st.error(f"API error: {resp.status_code} {resp.text}")
        except requests.exceptions.ReadTimeout:
            st.error(
                "The API took too long to respond. This is common on first run while models warm up "
                "(Chroma embeddings download / Ollama model load). Try again in ~30–60s."
            )
        except requests.RequestException as exc:
            st.error(f"Request failed: {exc}")

with tab_vitals:
    st.write("Enter any vitals you have. Leave fields blank if unknown.")
    bp = st.text_input("Blood pressure", placeholder="120/80")
    hr = st.number_input("Heart rate", min_value=0, max_value=250, value=0)
    glucose = st.number_input("Glucose level", min_value=0.0, max_value=1000.0, value=0.0)
    temp = st.number_input("Temperature (°C)", min_value=0.0, max_value=50.0, value=0.0)

    if st.button("Analyze vitals"):
        payload = {
            "blood_pressure": bp or None,
            "heart_rate": int(hr) if hr else None,
            "glucose_level": float(glucose) if glucose else None,
            "temperature": float(temp) if temp else None,
        }
        with st.spinner("Analyzing..."):
            resp = requests.post(f"{API_BASE_URL}/upload/vitals", json=payload, timeout=60)
        if resp.ok:
            data = resp.json()
            st.subheader("Vitals result")
            st.json(data)
        else:
            st.error(f"API error: {resp.status_code} {resp.text}")

with tab_uploads:
    st.write("Upload a lab report PDF or a medical image (X-ray/scan).")
    st.warning(
        "Do not upload real patient identifiers (names, MRNs, addresses). Use de-identified samples for demos."
    )
    file = st.file_uploader("Choose a file", type=["pdf", "png", "jpg", "jpeg"])
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Upload document", disabled=file is None):
            if file is not None:
                with st.spinner("Uploading..."):
                    resp = requests.post(
                        f"{API_BASE_URL}/upload/document",
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=120,
                    )
                if resp.ok:
                    st.json(resp.json())
                else:
                    st.error(f"API error: {resp.status_code} {resp.text}")
    with col2:
        if st.button("Upload image", disabled=file is None):
            if file is not None:
                with st.spinner("Uploading..."):
                    resp = requests.post(
                        f"{API_BASE_URL}/upload/image",
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=120,
                    )
                if resp.ok:
                    st.json(resp.json())
                else:
                    st.error(f"API error: {resp.status_code} {resp.text}")

