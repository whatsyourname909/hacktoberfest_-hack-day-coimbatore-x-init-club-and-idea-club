import json
import os
import html
from pathlib import Path

import pandas as pd
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
st.set_page_config(page_title="Argue With My Data | Enterprise Analysis", layout="wide")

FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
st.markdown(f"""
<link href="{FONT_URL}" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<style>
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    .material-symbols-outlined {{
        font-family: 'Material Symbols Outlined' !important;
    }}
    /* Layout */
    .block-container {{max-width: 1200px; padding-top: 2rem;}}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: rgba(15,23,42,0.6);
        border: 1px solid rgba(148,163,184,0.15);
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }}
    [data-testid="stMetric"] label {{font-weight: 500; color: #94a3b8; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em;}}
    [data-testid="stMetric"] [data-testid="stMetricValue"] {{font-weight: 600; color: #f8fafc;}}

    /* Expander styling */
    [data-testid="stExpander"] {{
        border: 1px solid rgba(148,163,184,0.15);
        border-radius: 8px;
        background: rgba(15,23,42,0.4);
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 500;
        color: #e2e8f0;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: #0f172a;
        border-right: 1px solid rgba(148,163,184,0.1);
    }}
    section[data-testid="stSidebar"] [data-testid="stMetric"] {{
        background: rgba(30,41,59,0.5);
        border: 1px solid rgba(148,163,184,0.1);
        padding: 12px 16px;
        border-radius: 6px;
        box-shadow: none;
    }}

    /* Button */
    .stButton > button[kind="primary"] {{
        background: #4f46e5;
        border: 1px solid #4338ca;
        color: white;
        font-weight: 600;
        padding: 0.6rem 2.5rem;
        border-radius: 6px;
        transition: all 0.2s ease;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: #4338ca;
        border-color: #3730a3;
    }}

    /* Secondary Button */
    .stButton > button[kind="secondary"] {{
        background: rgba(30,41,59,0.7);
        border: 1px solid rgba(148,163,184,0.2);
        color: #e2e8f0;
        font-weight: 500;
        border-radius: 6px;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: rgba(51,65,85,0.8);
        border-color: rgba(148,163,184,0.3);
        color: white;
    }}

    /* Dataframe */
    [data-testid="stDataFrame"] {{
        border-radius: 6px;
        border: 1px solid rgba(148,163,184,0.15);
    }}

    /* Divider */
    hr {{opacity: 0.1; margin: 2rem 0; border-color: #94a3b8;}}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Text Inputs */
    .stTextInput input {{
        background-color: rgba(15,23,42,0.6);
        border: 1px solid rgba(148,163,184,0.2);
        color: #f8fafc;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }}
    .stTextInput input:focus {{
        border-color: #4f46e5;
        box-shadow: 0 0 0 1px #4f46e5;
    }}
</style>
""", unsafe_allow_html=True)

# Load datasets metadata
try:
    with open(ROOT / "data" / "datasets.json", "r") as f:
        datasets_meta = json.load(f)["datasets"]
except Exception as e:
    datasets_meta = []


def _icon(name: str, color: str = "#e2e8f0", size: int = 24) -> str:
    return f'<span class="material-symbols-outlined" style="font-size:{size}px;color:{color};vertical-align:middle;margin-right:8px;">{name}</span>'


# --- Header ---
st.markdown(
    f'<h1 style="margin-bottom:0.2rem; font-weight: 700; letter-spacing: -0.02em; color: #f8fafc;">'
    f'{_icon("analytics", "#4f46e5", 36)}Argue With My Data</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem; margin-top: 0;">'
    'Enterprise Data Validation & Root Cause Analysis Platform</p>',
    unsafe_allow_html=True
)

# --- Sidebar: data source ---
with st.sidebar:
    st.markdown(f'<h3 style="color:#f8fafc;">{_icon("folder_open", "#94a3b8", 20)}Data Source</h3>', unsafe_allow_html=True)

    source_type = st.radio(
        "Source Type",
        ["Select Demo Dataset", "Upload Custom File"],
        label_visibility="collapsed",
    )

    frame = None
    examples = []

    if source_type == "Select Demo Dataset":
        if datasets_meta:
            dataset_options = {d["name"]: d for d in datasets_meta}
            selected_name = st.selectbox("Choose a dataset", list(dataset_options.keys()), label_visibility="collapsed")
            selected_meta = dataset_options[selected_name]

            st.markdown(
                f'<div style="background: rgba(30,41,59,0.5); padding: 12px; border-radius: 6px; margin-top: 8px; border: 1px solid rgba(148,163,184,0.1);">'
                f'<p style="font-size: 0.9em; color: #cbd5e1; margin: 0;">{selected_meta["description"]}</p></div>',
                unsafe_allow_html=True
            )

            try:
                frame = pd.read_csv(ROOT / "data" / selected_meta["file"])
                examples = selected_meta["suggested_questions"]
            except Exception as exc:
                st.error(f"Error loading {selected_meta['file']}: {exc}")
        else:
            st.error("Demo datasets metadata not found.")

    else:
        uploaded = st.file_uploader(
            "Upload a data file",
            type=["csv", "tsv", "xlsx", "xls"],
            label_visibility="collapsed",
            help="Supported formats: CSV, TSV, Excel (.xlsx, .xls)",
        )
        if uploaded:
            try:
                frame = read_uploaded_file(uploaded)
                examples = [
                    "What drove the change in revenue between Q1 and Q2?",
                    "Why did sales drop last month?",
                    "Which category contributed most to the increase?"
                ]
            except Exception as exc:
                st.error(f"Could not read this file: {exc}")

    st.markdown("<br>", unsafe_allow_html=True)

    if frame is not None:
        try:
            # We must set dataset_info in state later, but we need it here for UI
            _, summary = profile_data(frame)
            render_profile(summary)
            # Store summary to avoid recalculating
            st.session_state["current_dataset_info"] = summary
        except Exception as exc:
            st.error(f"This file cannot be profiled: {exc}")

    # API status
    st.markdown("<br><hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
    st.markdown(f'<h4 style="color:#cbd5e1;font-size:0.9rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px;">System Status</h4>', unsafe_allow_html=True)
    api_key = os.getenv("GEMMA_API_KEY")
    if api_key:
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:8px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:#10b981;margin-right:8px;"></div>'
            f'<span style="color:#cbd5e1;font-size:0.9rem;font-weight:500;">Gemma API key set</span></div>',
            unsafe_allow_html=True
        )
        model_name = os.getenv('GEMMA_MODEL', 'gemma-4-26b-a4b-it')
        st.markdown(f'<div style="color:#64748b;font-size:0.8rem;margin-left:16px;">Model: {model_name}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:8px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:#ef4444;margin-right:8px;"></div>'
            f'<span style="color:#cbd5e1;font-size:0.9rem;font-weight:500;">Gemma API Not Configured</span></div>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div style="color:#64748b;font-size:0.8rem;margin-left:16px;">Running in deterministic local mode.</div>', unsafe_allow_html=True)

# --- Main area: question & investigation ---
if frame is None:
    st.markdown(
        f'<div style="text-align:center; padding: 4rem 2rem; background: rgba(15,23,42,0.3); border: 1px dashed rgba(148,163,184,0.2); border-radius: 12px;">'
        f'{_icon("data_exploration", "#4f46e5", 48)}<br>'
        f'<h3 style="color:#e2e8f0;margin-top:1rem;margin-bottom:0.5rem;">No Dataset Selected</h3>'
        f'<p style="color:#94a3b8;font-size:1.1rem;max-width:500px;margin:0 auto;">'
        f'Please select a demo dataset or upload your own file from the sidebar to begin analysis.</p></div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(f'<h3 style="color:#f8fafc; font-weight:600; margin-bottom:1rem;">{_icon("search", "#e2e8f0", 24)}Define Investigation</h3>', unsafe_allow_html=True)

    # Example prompts
    if examples:
        st.markdown('<p style="color:#94a3b8; font-size:0.9rem; margin-bottom:8px;">Suggested Queries:</p>', unsafe_allow_html=True)
        example_cols = st.columns(len(examples))
        for i, example in enumerate(examples):
            if example_cols[i].button(f"{example}", key=f"example_{i}", use_container_width=True):
                st.session_state["question_input"] = example

    question = st.text_input(
        "Business question",
        value=st.session_state.get("question_input", ""),
        placeholder="e.g. Why did revenue fall in March?",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        run = st.button("Execute Analysis", type="primary", disabled=not question.strip(), use_container_width=True)

    current_signature = None
    if frame is not None:
        current_signature = (question.strip(), frame.shape, tuple(map(str, frame.columns)),
                            int(pd.util.hash_pandas_object(frame, index=True).sum()))

    if run:
        try:
            st.markdown("<br>", unsafe_allow_html=True)
            # Progress tracking
            progress_bar = st.progress(0, text="Initializing investigation engine...")
            stages = [
                (0.10, "Validating query relevance..."),
                (0.20, "Profiling dataset structure..."),
                (0.35, "Parsing semantic parameters..."),
                (0.45, "Computing deterministic baseline..."),
                (0.60, "Generating competing hypotheses..."),
                (0.75, "Executing falsification tests..."),
                (0.85, "Verifying mathematical consistency..."),
                (0.95, "Synthesizing evidence-backed conclusions..."),
            ]
            for pct, label in stages[:2]:
                progress_bar.progress(pct, text=label)

            progress_bar.progress(0.25, text="Running full analysis pipeline...")

            # We need to inject the dataset_info into the initial state for the question validator
            dataset_info = st.session_state.get("current_dataset_info", {})
            initial_state = {
                "dataset": frame,
                "question": question.strip(),
                "dataset_info": dataset_info
            }

            result = investigation_graph.invoke(
                initial_state,
                config={"recursion_limit": 20}
            )
            st.session_state["investigation_result"] = result
            st.session_state["investigation_signature"] = current_signature
            progress_bar.progress(1.0, text="Analysis Complete")
            progress_bar.empty()
            st.rerun()
        except Exception as exc:
            st.session_state.pop("investigation_result", None)
            st.error(f"Investigation execution failed: {exc}")

    result = st.session_state.get("investigation_result") if st.session_state.get("investigation_signature") == current_signature else None
    if result:
        st.markdown("<hr style='margin: 2rem 0 1rem 0;'>", unsafe_allow_html=True)

        if result.get("error"):
            st.markdown(
                f'<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); '
                f'border-left:4px solid #ef4444; padding:16px 20px; border-radius:6px; margin-bottom:20px;">'
                f'<div style="display:flex;align-items:center;">'
                f'{_icon("error", "#ef4444", 24)}'
                f'<span style="color:#f8fafc;font-weight:600;font-size:1.05rem;">Analysis Halted</span></div>'
                f'<p style="color:#cbd5e1;margin-top:8px;margin-bottom:0;font-size:0.95rem;">{html.escape(result["error"])}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            if question.strip():
                st.markdown(
                    f'<div style="background:rgba(15,23,42,0.6); padding:16px 20px; '
                    f'border-radius:8px; margin-bottom:24px; border:1px solid rgba(148,163,184,0.15); '
                    f'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
                    f'<div style="color:#94a3b8;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">'
                    f'Active Investigation</div>'
                    f'<div style="color:#f8fafc;font-size:1.15rem;font-weight:500;">"{html.escape(question.strip())}"</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            render_investigation(result)
            if result.get("warning"):
                st.markdown(
                    f'<div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); '
                    f'border-left:4px solid #f59e0b; padding:12px 16px; border-radius:6px; margin-top:20px;">'
                    f'<div style="display:flex;align-items:flex-start;">'
                    f'{_icon("warning", "#f59e0b", 20)}'
                    f'<span style="color:#cbd5e1;font-size:0.95rem;">{html.escape(result["warning"])}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Offer next step
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f'<h4 style="color:#e2e8f0;">{_icon("refresh", "#94a3b8", 20)}Continue Investigation</h4>', unsafe_allow_html=True)
        st.markdown('<p style="color:#94a3b8;">Refine your query or select a different dataset to run a new analysis.</p>', unsafe_allow_html=True)
    elif not run:
        st.markdown(
            f'<div style="margin-top:2rem; padding:1.5rem; background: rgba(30,41,59,0.3); '
            f'border-radius:8px; border: 1px solid rgba(148,163,184,0.1);">'
            f'<div style="display:flex; align-items:center;">'
            f'{_icon("info", "#94a3b8", 24)}'
            f'<span style="color:#cbd5e1;">Enter a business query and click <strong>Execute Analysis</strong> to begin.</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )
