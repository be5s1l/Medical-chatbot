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

tab_chat, tab_images, tab_labs = st.tabs(["Chat", "Image analysis", "Lab reports"])

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
                st.write(data.get("summary", ""))
                causes = data.get("possible_causes") or []
                if isinstance(causes, list) and causes:
                    st.caption("Possible causes (non-diagnostic)")
                    st.markdown("\n".join([f"- {c}" for c in causes]))
                st.caption(f"Urgency: **{data.get('urgency', '—')}**")
                st.write(data.get("advice", ""))
                st.caption(DEFAULT_DISCLAIMER)
            else:
                st.error(f"API error: {resp.status_code} {resp.text}")
        except requests.exceptions.ReadTimeout:
            st.error(
                "The API took too long to respond. This is common on first run while models warm up "
                "(first request may be slower). Try again in ~30–60s."
            )
        except requests.RequestException as exc:
            st.error(f"Request failed: {exc}")

with tab_images:
    st.write("Upload a medical image (X-ray/scan/photo).")
    st.warning(
        "Do not upload real patient identifiers (names, MRNs, addresses). Use de-identified samples for demos."
    )
    img = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "webp"])
    if st.button("Analyze image", disabled=img is None):
        if img is not None:
            with st.spinner("Analyzing..."):
                resp = requests.post(
                    f"{API_BASE_URL}/analyze-image",
                    files={"file": (img.name, img.getvalue(), img.type)},
                    timeout=180,
                )
            if resp.ok:
                st.json(resp.json())
            else:
                st.error(f"API error: {resp.status_code} {resp.text}")

with tab_labs:
    st.write("Analyze lab reports (image OCR or PDF text extraction).")
    st.warning(
        "Do not upload real patient identifiers (names, MRNs, addresses). Use de-identified samples for demos."
    )
    lab_img = st.file_uploader("Lab report image", type=["png", "jpg", "jpeg", "webp"], key="lab_img")
    if st.button("Analyze lab image", disabled=lab_img is None):
        if lab_img is not None:
            with st.spinner("OCR + simplifying..."):
                resp = requests.post(
                    f"{API_BASE_URL}/analyze-lab-image",
                    files={"file": (lab_img.name, lab_img.getvalue(), lab_img.type)},
                    timeout=240,
                )
            if resp.ok:
                st.json(resp.json())
            else:
                st.error(f"API error: {resp.status_code} {resp.text}")

    lab_pdf = st.file_uploader("Lab report PDF", type=["pdf"], key="lab_pdf")
    if st.button("Analyze lab PDF", disabled=lab_pdf is None):
        if lab_pdf is not None:
            with st.spinner("Extracting + simplifying..."):
                resp = requests.post(
                    f"{API_BASE_URL}/analyze-lab-pdf",
                    files={"file": (lab_pdf.name, lab_pdf.getvalue(), lab_pdf.type)},
                    timeout=240,
                )
            if resp.ok:
                st.json(resp.json())
            else:
                st.error(f"API error: {resp.status_code} {resp.text}")

