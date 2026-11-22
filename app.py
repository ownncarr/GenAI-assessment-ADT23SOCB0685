import hashlib
import json
import os
import time

from dotenv import load_dotenv
import streamlit as st

from llm_service import GenerationError, available_models, generate_questions, to_text
from pdf_utils import extract_report, prepare_report
from prompts import LEVELS

load_dotenv()


@st.cache_data(ttl=20, show_spinner=False)
def discover_models(url: str) -> list[str]:
    return available_models(url)


def main() -> None:
    st.set_page_config(page_title="AI Viva Question Generator", page_icon="🎓", layout="wide")
    st.markdown("""<style>
    .block-container {max-width:1100px;padding-top:2.6rem;padding-bottom:3rem}
    h1 {letter-spacing:-.04em} h2,h3 {letter-spacing:-.02em}
    [data-testid="stMetric"] {background:#f1f5f9;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px}
    [data-testid="stSidebar"] {border-right:1px solid #e2e8f0}
    .eyebrow {color:#4f46e5;font-size:.78rem;letter-spacing:.15em;font-weight:700;margin-bottom:12px}
    .stDownloadButton button {width:100%}
    </style>""", unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">PS28 · PROJECT VIVA PREPARATION</div>', unsafe_allow_html=True)
    st.title("AI Viva Question Generator")
    st.markdown("Upload your project report and prepare for your viva with AI-generated questions.")
    st.caption("15 questions · 3 difficulty levels · Answers based on your report")

    with st.sidebar:
        st.header("Model settings")
        provider = st.radio("LLM provider", ["Ollama", "Groq"])
        api_key = ""
        base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        if provider == "Ollama":
            base_url = st.text_input("Ollama server", value=base_url)
            models = discover_models(base_url)
            configured = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            choices = list(dict.fromkeys([configured, *models]))
            selection = st.selectbox("Local model", choices + ["Other model…"])
            model = st.text_input("Model name", value="llama3.2:3b") if selection == "Other model…" else selection
            if models:
                st.success(f"Ollama connected · {len(models)} text model(s)")
                if model not in models:
                    st.warning(f"Model not installed. Run: ollama pull {model}")
            else:
                st.info("Start Ollama, then refresh models. Download a model with: ollama pull qwen2.5:7b")
            if st.button("Refresh models"):
                discover_models.clear()
                st.rerun()
            st.caption("Local mode sends the extracted report to your configured Ollama server.")
        else:
            model = st.text_input("Groq model", value=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
            api_key = st.text_input("Groq API key", value=os.getenv("GROQ_API_KEY", ""), type="password")
            st.caption("Groq mode sends extracted report text to Groq. Your key is used only for requests and is not written to disk.")
        st.divider()
        st.markdown("**How it works**")
        st.markdown("1. Upload a text-based PDF.\n2. Generate 15 viva questions.\n3. Review answers and download.")
        st.caption("No account or database required. Scanned documents need OCR before upload.")

    st.subheader("Your project report")
    uploaded = st.file_uploader("Upload a PDF project report", type=["pdf"], help="Text-based PDF · up to 20 MB and 200 pages")
    data = uploaded.getvalue() if uploaded is not None else b""
    identity = hashlib.sha256(data + json.dumps([provider, model, base_url, api_key]).encode()).hexdigest()
    if st.session_state.get("source_id") != identity:
        for key in ("questions", "generation_seconds", "result_model", "result_provider"):
            st.session_state.pop(key, None)
        st.session_state["source_id"] = identity
    if uploaded is None:
        st.info("Upload a report to get started, or try the sample project report below.")
        sample = os.path.join(os.path.dirname(__file__), "samples", "sample_project_report.pdf")
        with open(sample, "rb") as handle:
            st.download_button("Download sample PDF", handle.read(), "sample_project_report.pdf", "application/pdf")
        st.button("Generate Viva Questions", type="primary", disabled=True)
        st.divider()
        cols = st.columns(3)
        for col, heading, body in zip(cols, ("Easy · Understand", "Medium · Explain", "Hard · Defend"),
                                      ("Objectives, concepts and technologies.", "Architecture, methods and implementation.", "Trade-offs, limitations and evaluation.")):
            with col:
                st.markdown(f"**{heading}**")
                st.caption(body)
        return
    try:
        report = extract_report(data)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption(f"Document: {uploaded.name}")
    cols = st.columns(3)
    cols[0].metric("Pages", report.page_count)
    cols[1].metric("Extracted words", f"{report.word_count:,}")
    cols[2].metric("Questions to generate", "15")
    if report.empty_pages:
        st.warning(f"{report.empty_pages} page(s) have no extractable text. Their images or scanned content cannot be used.")
    text, sampled = prepare_report(report.text)
    if sampled:
        st.warning("This report exceeds the input budget. Excerpts sampled throughout the report will be used; some details will be omitted. Upload a shorter report for full coverage.")
    with st.expander("Preview text sent to the model"):
        st.text_area("Extracted report text", text, height=220, disabled=True)
    if st.button("Generate Viva Questions", type="primary"):
        st.session_state.pop("questions", None)
        start = time.monotonic()
        with st.spinner("Reading your report and preparing 15 questions… Local generation may take a few minutes."):
            try:
                questions = generate_questions(text, provider, model, api_key, base_url)
            except GenerationError as exc:
                st.error(str(exc))
                return
        st.session_state.update(questions=questions, generation_seconds=time.monotonic() - start,
                                result_model=model, result_provider=provider)
    questions = st.session_state.get("questions")
    if not questions:
        return
    st.divider()
    st.subheader("Your viva preparation set")
    st.success(f"15 questions ready · {st.session_state['result_provider']} / {st.session_state['result_model']} · {st.session_state['generation_seconds']:.1f}s")
    tabs = st.tabs([f"{level.title()} · 5 questions" for level in LEVELS])
    for tab, level in zip(tabs, LEVELS):
        with tab:
            for index, item in enumerate(questions[level], 1):
                with st.expander(f"Q{index}. {item['question']}"):
                    st.write(item["answer"])
    st.caption("Answers are based on your report; missing details should be marked explicitly.")
    st.caption("AI-generated answers can contain errors. Check them against the report before your viva.")
    st.markdown("**Take your questions with you**")
    left, right = st.columns(2)
    with left:
        st.download_button("Download TXT", to_text(questions), "viva_questions.txt", "text/plain; charset=utf-8")
    with right:
        st.download_button("Download JSON", json.dumps(questions, ensure_ascii=False, indent=2), "viva_questions.json", "application/json")


if __name__ == "__main__":
    main()
