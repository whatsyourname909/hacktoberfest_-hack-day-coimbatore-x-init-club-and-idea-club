import os
from pathlib import Path

import pandas as pd
import html
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from analysis.profiling import profile_data
from graph.graph import investigation_graph
from ui.components import render_investigation, render_profile


def read_uploaded_file(uploaded) -> pd.DataFrame:
    """Read an uploaded file (CSV, TSV, XLSX, XLS) into a DataFrame.

    CSV/TSV text encodings are tried in order: UTF-8 (with or without a BOM),
    chardet's guess when it is reasonably confident, Windows-1252 (the usual
    encoding of CSVs exported from Excel on Windows), then Latin-1, which
    decodes any byte sequence and so always succeeds.
    """
    from io import BytesIO

    name = uploaded.name.lower()

    # Excel files
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded, engine="openpyxl")
    if name.endswith(".xls"):
        return pd.read_excel(uploaded, engine="xlrd")

    # CSV / TSV
    sep = "\t" if name.endswith(".tsv") else ","
    raw_bytes = uploaded.getvalue()

    encodings = ["utf-8-sig"]
    try:
        import chardet

        detected = chardet.detect(raw_bytes[:100_000])
        if detected.get("encoding") and (detected.get("confidence") or 0) >= 0.5:
            encodings.append(detected["encoding"])
    except ImportError:
        pass
    encodings += ["cp1252", "latin-1"]

    for encoding in dict.fromkeys(encoding.lower() for encoding in encodings):
        try:
            return pd.read_csv(BytesIO(raw_bytes), sep=sep, encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue  # wrong encoding; try the next one. Other CSV errors are raised to the caller.
    raise ValueError("Could not decode this file's text encoding.")

# --- Page config & theming ---
st.set_page_config(page_title="Argue With My Data", page_icon="🧪", layout="wide")
st.markdown("""
<style>
    /* Layout */
    .block-container {max-width: 1100px; padding-top: 1.5rem;}

    /* Metric cards */
    [data-testid="stMetric"] {
        background: rgba(99,102,241,0.06);
        border: 1px solid rgba(99,102,241,0.15);
        padding: 14px 18px;
        border-radius: 12px;
    }
    [data-testid="stMetric"] label {font-weight: 500;}

    /* Expander styling */
    [data-testid="stExpander"] {
        border: 1px solid rgba(148,163,184,0.15);
        border-radius: 10px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(15,23,42,0.3);
    }
    section[data-testid="stSidebar"] [data-testid="stMetric"] {
        background: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.12);
        padding: 10px 14px;
        border-radius: 10px;
    }

    /* Button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border: none;
        font-weight: 600;
        padding: 0.5rem 2rem;
        border-radius: 8px;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {border-radius: 8px;}

    /* Divider */
    hr {opacity: 0.15;}

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(
    '<h1 style="margin-bottom:0;">🧪 Argue With My Data</h1>',
    unsafe_allow_html=True,
)
st.caption("LLM proposes · Code tests · Critic challenges · Evidence decides")

# --- Sidebar: data source ---
with st.sidebar:
    st.markdown("### 📁 Your data")
    source = st.radio(
        "Dataset",
        ["Try the demo dataset", "Upload a file"],
        label_visibility="collapsed",
    )
    uploaded = None
    if source == "Upload a file":
        uploaded = st.file_uploader(
            "Upload a data file",
            type=["csv", "tsv", "xlsx", "xls"],
            label_visibility="collapsed",
            help="Supported formats: CSV, TSV, Excel (.xlsx, .xls)",
        )

    frame = None
    if source == "Try the demo dataset":
        frame = pd.read_csv(ROOT / "data" / "demo_sales.csv")
        st.caption("📦 Built-in adversarial sales example")
    elif uploaded:
        try:
            frame = read_uploaded_file(uploaded)
        except Exception as exc:
            st.error(f"Could not read this file: {exc}")

    if frame is not None:
        try:
            _, summary = profile_data(frame)
            render_profile(summary)
        except Exception as exc:
            st.error(f"This file cannot be profiled: {exc}")

    # API status
    st.divider()
    api_key = os.getenv("GEMMA_API_KEY")
    if api_key:
        st.caption("🔑 **Gemma API key** set")
        st.caption(f"Model: `{os.getenv('GEMMA_MODEL', 'gemma-4-26b-a4b-it')}`")
        st.caption("Whether Gemma actually answered is shown, step by step, with each investigation's results.")
    else:
        st.caption("🔴 **Gemma API** not configured")
        st.caption("Set `GEMMA_API_KEY` in `.env` for AI-powered parsing. The app works without it using local fallbacks.")

# --- Main area: question & investigation ---
if frame is None:
    st.info("👈 Choose a dataset in the sidebar to get started.")
else:
    st.markdown("### ❓ Ask a business question")

    # Example prompts
    examples = [
        "Why did revenue fall in March?",
        "What explains the change in revenue between February and March?",
        "Which products drove the revenue decline?",
    ]
    example_cols = st.columns(len(examples))
    for i, example in enumerate(examples):
        if example_cols[i].button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
            st.session_state["question_input"] = example

    question = st.text_input(
        "Business question",
        value=st.session_state.get("question_input", ""),
        placeholder="e.g. Why did revenue fall in March?",
        label_visibility="collapsed",
    )

    run = st.button("🔍 Investigate", type="primary", disabled=not question.strip())

    current_signature = None
    if frame is not None:
        current_signature = (question.strip(), frame.shape, tuple(map(str, frame.columns)),
                            int(pd.util.hash_pandas_object(frame, index=True).sum()))

    if run:
        try:
            # Progress tracking
            progress_bar = st.progress(0, text="Starting investigation…")
            stages = [
                (0.10, "Profiling data…"),
                (0.20, "Parsing question…"),
                (0.35, "Computing baseline…"),
                (0.50, "Generating hypotheses…"),
                (0.65, "Running analysis tests…"),
                (0.80, "Verifying calculations…"),
                (0.90, "Critic reviewing evidence…"),
                (1.00, "Composing final answer…"),
            ]
            # Show initial progress, then run the graph
            for pct, label in stages[:2]:
                progress_bar.progress(pct, text=label)

            progress_bar.progress(0.30, text="Running full investigation pipeline…")
            st.session_state["investigation_result"] = investigation_graph.invoke(
                {"dataset": frame, "question": question.strip()}, config={"recursion_limit": 20}
            )
            st.session_state["investigation_signature"] = current_signature
            progress_bar.progress(1.0, text="Investigation complete ✅")
            progress_bar.empty()
            st.rerun()
        except Exception as exc:
            st.session_state.pop("investigation_result", None)
            st.error(f"Investigation could not run: {exc}")

    result = st.session_state.get("investigation_result") if st.session_state.get("investigation_signature") == current_signature else None
    if result:
        if result.get("error"):
            st.error(f"⚠️ {result['error']}")
        else:
            if question.strip():
                st.markdown(
                    f'<div style="background:rgba(99,102,241,0.08); padding:10px 16px; '
                    f'border-radius:8px; margin-bottom:16px;">'
                    f'<span style="color:#94a3b8;">Investigating:</span> '
                    f'<strong style="color:#e2e8f0;">{html.escape(question.strip())}</strong></div>',
                    unsafe_allow_html=True,
                )
            render_investigation(result)
            if result.get("warning"):
                st.warning(result["warning"])

        # Offer next step
        st.divider()
        st.markdown("##### 🔄 What's next?")
        st.caption("Refine your question above or try a different angle to investigate further.")
    elif not run:
        st.caption("Enter a question and click **Investigate** to start the analysis pipeline.")
