import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from analysis.profiling import profile_data
from graph.graph import investigation_graph
from ui.components import render_investigation, render_profile

st.set_page_config(page_title="Argue With My Data", page_icon="🧪", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2rem;}
[data-testid="stMetric"] {background: #f4f7f6; border: 1px solid #e5ece9; padding: 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)
st.title("Argue With My Data")
st.caption("LLM proposes. Code tests. Critic challenges. Evidence decides.")

with st.sidebar:
    st.markdown("### Your data")
    source = st.radio("Dataset", ["Upload a CSV", "Try the demo dataset"], label_visibility="collapsed")
    uploaded = st.file_uploader("Upload a CSV", type=["csv"], max_upload_size=50) if source == "Upload a CSV" else None
    frame = None
    if source == "Try the demo dataset":
        frame = pd.read_csv(ROOT / "data" / "demo_sales.csv")
        st.caption("Built-in adversarial sales example")
    elif uploaded:
        try:
            frame = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not read this CSV: {exc}")
    if frame is not None:
        try:
            _, summary = profile_data(frame)
            render_profile(summary)
            with st.expander("Columns and data quality"):
                st.write(summary["data_types"])
                st.write({name: f"{value:.1%} missing" for name, value in summary["missingness"].items()})
        except Exception as exc:
            st.error(f"This file cannot be profiled: {exc}")

st.markdown("### Ask a business question")
question = st.text_input("Business question", placeholder="Why did revenue fall in March?", label_visibility="collapsed")
run = st.button("Investigate", type="primary", disabled=frame is None or not question.strip())
current_signature = None
if frame is not None:
    current_signature = (question.strip(), frame.shape, tuple(map(str, frame.columns)),
                        int(pd.util.hash_pandas_object(frame, index=True).sum()))

if run:
    try:
        with st.spinner("Testing competing explanations against the data…"):
            st.session_state["investigation_result"] = investigation_graph.invoke(
                {"dataset": frame, "question": question.strip()}, config={"recursion_limit": 20}
            )
            st.session_state["investigation_signature"] = current_signature
    except Exception as exc:
        st.session_state.pop("investigation_result", None)
        st.error(f"Investigation could not run: {exc}")

result = st.session_state.get("investigation_result") if st.session_state.get("investigation_signature") == current_signature else None
if result:
    if result.get("error"):
        st.error(result["error"])
    else:
        if question.strip():
            st.caption("Question: “" + question.strip() + "”")
        render_investigation(result)
        if result.get("warning"):
            st.warning(result["warning"])
        if not os.getenv("GEMMA_API_KEY"):
            st.info("Gemma is configured through GEMMA_API_KEY. Without a key, question parsing and investigation use the schema-safe local fallback.")
else:
    st.info("Upload a CSV or choose the built-in demo, enter a question, and start the investigation.")
