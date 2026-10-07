"""Kanakku - The PA.  Owner: A.   Run: streamlit run app.py

A polished Streamlit interface for Proof-Carrying Data Analysis:
- Injected CSS styling (deep green brand, gold accents, soft shadow cards)
- Dataset selection, "How Kanakku works" workflow, and session history in sidebar
- High-level metrics row (Tables, Total rows, Traps found)
- Trap Radar grid with colored cards and trap-type icons
- Question analysis with example queries, proof code viewer, and re-run verification
"""
import html
import os
from pathlib import Path

import streamlit as st

from engine import rerun_proof, run_question
from loader import load_folder
from profiler import profile_all

st.set_page_config(page_title="Kanakku - The PA", layout="wide")

# ---- CSS Injection -------------------------------------------------------
st.markdown(
    """<style>
/* Light theme */
:root {
    --brand-green: #0f5c4a;
    --brand-gold: #f2b705;
}

.stApp {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Headings */
h1, h2, h3, h4, .stHeading {
    color: #0f5c4a !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

h1 {
    font-size: 2.3rem !important;
    margin: 0 !important;
}

h2 {
    font-size: 1.6rem !important;
    margin-top: 1.75rem !important;
    margin-bottom: 0.75rem !important;
}

h3 {
    font-size: 1.25rem !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.5rem !important;
}

/* Spacing */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1200px;
}

/* White cards with 12px rounded corners and soft shadow */
[data-testid="stMetric"], div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 4px 12px rgba(15, 92, 74, 0.05), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(15, 92, 74, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04) !important;
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

[data-testid="stMetricValue"] {
    color: #0f5c4a !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}

/* AI Mode pill */
.ai-mode-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: #e6f4ea;
    color: #0f5c4a;
    border: 1px solid #b7e1cd;
    border-radius: 9999px;
    padding: 5px 14px;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: lowercase;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.ai-mode-pill::before {
    content: "●";
    color: #0f5c4a;
    font-size: 0.75rem;
}

/* Trap Radar cards */
.trap-card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    border-left-width: 5px !important;
    border-left-style: solid !important;
    padding: 16px 18px;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.trap-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.07);
}

.trap-card-high {
    border-left-color: #dc3545 !important;
}

.trap-card-medium {
    border-left-color: #fd7e14 !important;
}

.trap-card-low {
    border-left-color: #6c757d !important;
}

.trap-card-clean {
    border-left-color: #0f5c4a !important;
    background-color: #f0fdf4 !important;
}

.trap-card-msg {
    font-weight: 700;
    color: #1e293b;
    font-size: 0.95rem;
    line-height: 1.4;
    margin-bottom: 8px;
}

.trap-card-meta {
    color: #64748b;
    font-size: 0.82rem;
    font-weight: 500;
}

/* Buttons with deep green & gold accent */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #0f5c4a !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid #0f5c4a !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
}

button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
    background-color: #0c4a3b !important;
    border-color: #f2b705 !important;
    box-shadow: 0 0 0 2px #f2b705 !important;
    color: #ffffff !important;
}

/* Result cards with top borders */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-top-green) {
    border-top: 5px solid #0f5c4a !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-top-red) {
    border-top: 5px solid #dc3545 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-top-grey) {
    border-top: 5px solid #64748b !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
</style>""",
    unsafe_allow_html=True,
)

# ---- Helper functions ----------------------------------------------------
def _trap_icon(flag: dict) -> str:
    trap = str(flag.get("trap", "")).lower()
    msg = str(flag.get("message", "")).lower()
    col = str(flag.get("column", "")).lower()

    if "month" in trap or "period" in trap or "month" in msg or "month" in col:
        return "📆"
    if "dup" in trap or "duplicate" in msg:
        return "🔁"
    if "curr" in trap or "currency" in msg or "currency" in col:
        return "💱"
    if "date" in trap or "date" in msg or "date" in col:
        return "📅"
    if "contradiction" in trap or "differ" in msg or "contradict" in msg:
        return "⚔"
    if "missing" in trap or "missing" in msg or "blank" in msg:
        return "🕳"
    return "⚠"


SEVERITY_CLASS = {
    "high": "trap-card-high",
    "medium": "trap-card-medium",
    "low": "trap-card-low",
}

def _set_question(q: str):
    st.session_state["question_input"] = q

# ---- Session State Initialization ----------------------------------------
if "question_input" not in st.session_state:
    st.session_state["question_input"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []

# ---- Header --------------------------------------------------------------
ai_mode = os.getenv("LLM_MODE", "replay").lower()
if "result" in st.session_state and st.session_state["result"].get("llm_mode"):
    ai_mode = str(st.session_state["result"]["llm_mode"]).lower()

header_html = f"""<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; padding-bottom: 1.25rem; border-bottom: 1px solid #e2e8f0;">
    <div>
        <h1 style="color: #0f5c4a; font-size: 2.3rem; font-weight: 800; margin: 0; line-height: 1.2;">Kanakku - The PA</h1>
        <div style="color: #64748b; font-size: 1.05rem; margin-top: 0.35rem;">Numbers you can check, not just trust.</div>
    </div>
    <div style="padding-top: 0.35rem;">
        <span class="ai-mode-pill">{ai_mode}</span>
    </div>
</div>"""
st.markdown(header_html, unsafe_allow_html=True)

# ---- Sidebar -------------------------------------------------------------
datasets = sorted(p.name for p in Path("data").iterdir() if p.is_dir() and any(p.glob("*.csv")))
with st.sidebar:
    st.header("Datasets")
    choice = st.selectbox("Dataset", datasets)

    st.markdown("---")
    st.subheader("How Kanakku works")
    st.markdown(
        """1. Load data
2. Trap Radar checks it
3. AI writes pandas code
4. runs in a sandbox
5. proof re-run in a fresh process
6. answer or refuse"""
    )

    st.markdown("---")
    st.subheader("History")
    history_placeholder = st.empty()


def _render_history():
    hist = st.session_state.get("history", [])
    with history_placeholder.container():
        if hist:
            for item in reversed(hist):
                if isinstance(item, dict):
                    q_text = item.get("question", "")
                    status = str(item.get("status", "error")).lower()
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    q_text = str(item[0])
                    status = str(item[1]).lower()
                else:
                    q_text = str(item)
                    status = "error"
                dot = "🟢" if status == "answered" else ("🔴" if status == "abstained" else "⚪")
                st.markdown(f"{dot} {q_text}")
        else:
            st.caption("No questions asked yet.")


_render_history()

tables = load_folder(f"data/{choice}")
flags = profile_all(tables)

# ---- Metrics Row ---------------------------------------------------------
m1, m2, m3 = st.columns(3)
total_tables = len(tables)
total_rows = sum(len(df) for df in tables.values())
traps_found = len(flags)

m1.metric("Tables", total_tables)
m2.metric("Total rows", total_rows)
m3.metric("Traps found", traps_found)

# ---- Trap Radar Section --------------------------------------------------
st.subheader("Trap Radar")

if flags:
    for i in range(0, len(flags), 3):
        chunk = flags[i : i + 3]
        cols = st.columns(3)
        for col, flag in zip(cols, chunk):
            sev = str(flag.get("severity", "low")).lower()
            sev_cls = SEVERITY_CLASS.get(sev, "trap-card-low")
            icon = _trap_icon(flag)
            msg = html.escape(str(flag.get("message", "")))
            tbl = html.escape(str(flag.get("table", "")))
            c_name = html.escape(str(flag.get("column", "")))
            n_rows = flag.get("count", 0)

            card_html = f"""<div class="trap-card {sev_cls}">
                <div class="trap-card-msg"><span>{icon}</span> <strong>{msg}</strong></div>
                <div class="trap-card-meta">{tbl}.{c_name} · {n_rows} rows</div>
            </div>"""
            with col:
                st.markdown(card_html, unsafe_allow_html=True)
else:
    green_card_html = """<div class="trap-card trap-card-clean">
        <div class="trap-card-msg" style="color: #0f5c4a; margin-bottom: 0;">
            <span>✔</span> <strong>No traps found</strong>
        </div>
    </div>"""
    st.markdown(green_card_html, unsafe_allow_html=True)

# ---- Question & Result ---------------------------------------------------
st.subheader("Ask Kanakku")

col_q, col_btn = st.columns([5, 1])
with col_q:
    question = st.text_input(
        "Ask a question about this data",
        placeholder="Ask anything about this data...",
        key="question_input",
        label_visibility="collapsed",
    )
with col_btn:
    ask_clicked = st.button("Ask Kanakku", type="primary", use_container_width=True)

# 3 example buttons that fill the box when clicked
ex1_text = "What was revenue from USD orders in January 2024?"
ex2_text = "Total revenue in March 2024 in USD?"
ex3_text = "Why did sales drop in February?"

col_e1, col_e2, col_e3 = st.columns(3)
with col_e1:
    st.button(ex1_text, on_click=_set_question, args=(ex1_text,), use_container_width=True)
with col_e2:
    st.button(ex2_text, on_click=_set_question, args=(ex2_text,), use_container_width=True)
with col_e3:
    st.button(ex3_text, on_click=_set_question, args=(ex3_text,), use_container_width=True)

if ask_clicked and question:
    with st.spinner("Checking the data..."):
        result = run_question(question, tables, flags)
        st.session_state["result"] = result
        st.session_state["history"].append({
            "question": question,
            "status": result.get("status", "error"),
        })
        _render_history()

result = st.session_state.get("result")
if result:
    status = result.get("status", "error")
    seconds = result.get("seconds", 0)

    if status == "answered":
        with st.container(border=True):
            st.markdown(
                """<div class="result-top-green" style="height: 5px; background-color: #0f5c4a; margin: -1rem -1rem 1rem -1rem; border-top: 5px solid #0f5c4a; border-top-left-radius: 10px; border-top-right-radius: 10px;"></div>""",
                unsafe_allow_html=True,
            )

            is_dict_val = isinstance(result.get("value"), dict)
            if is_dict_val:
                val_dict = result["value"]
                v_dd = val_dict.get("if_DD/MM")
                v_mm = val_dict.get("if_MM/DD")
                unit_prefix = "$" if result.get("unit") == "USD" else ""

                def _fmt(v):
                    if isinstance(v, (int, float)):
                        return f"{unit_prefix}{v:,.2f}"
                    return f"{unit_prefix}{v}" if unit_prefix and not str(v).startswith(unit_prefix) else str(v)

                col_m1, col_m2 = st.columns(2)
                col_m1.metric("If dates are DD/MM", _fmt(v_dd))
                col_m2.metric("If dates are MM/DD", _fmt(v_mm))
                st.markdown(
                    f"""<div style="font-size: 0.85rem; color: #64748b; margin-top: 4px; margin-bottom: 12px;">
                        <span style="color: #0f5c4a; font-weight: 600;">Verified ✔</span> · {seconds}s
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                ans_text = html.escape(str(result.get("answer", "")))
                st.markdown(
                    f"""<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px;">
                        <div style="font-size: 2.2rem; font-weight: 800; color: #0f5c4a; line-height: 1.1;">{ans_text}</div>
                        <div style="font-size: 0.85rem; color: #64748b;">
                            <span style="color: #0f5c4a; font-weight: 600;">Verified ✔</span> · {seconds}s
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            tab_answer, tab_code, tab_assumptions = st.tabs(["Answer", "Proof code", "Assumptions"])

            with tab_answer:
                st.write(result.get("answer", ""))

            with tab_code:
                st.code(result.get("code", ""), language="python")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("Re-run proof"):
                        rerun_res = rerun_proof(result["proof_path"])
                        if rerun_res.get("match"):
                            st.success("Re-ran in a fresh process: same number ✔")
                        else:
                            st.error("did not match")
                with col_btn2:
                    proof_path = result.get("proof_path", "")
                    proof_data = ""
                    file_name = "proof.py"
                    if proof_path and Path(proof_path).exists():
                        try:
                            with open(proof_path, "r", encoding="utf-8") as f:
                                proof_data = f.read()
                            file_name = Path(proof_path).name
                        except Exception:
                            proof_data = result.get("code", "")
                    else:
                        proof_data = result.get("code", "")
                        if proof_path:
                            file_name = Path(proof_path).name

                    st.download_button(
                        "Download proof",
                        data=proof_data,
                        file_name=file_name,
                        mime="text/x-python",
                    )

            with tab_assumptions:
                assumptions = result.get("assumptions", [])
                if assumptions:
                    if isinstance(assumptions, list):
                        for asm in assumptions:
                            st.markdown(f"- {asm}")
                    elif isinstance(assumptions, dict):
                        for k, v in assumptions.items():
                            st.markdown(f"- **{k}**: {v}")
                    else:
                        st.markdown(f"- {assumptions}")
                else:
                    st.write("No assumptions made.")

    elif status == "abstained":
        with st.container(border=True):
            st.markdown(
                """<div class="result-top-red" style="height: 5px; background-color: #dc3545; margin: -1rem -1rem 1rem -1rem; border-top: 5px solid #dc3545; border-top-left-radius: 10px; border-top-right-radius: 10px;"></div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                """<div style="font-size: 1.35rem; font-weight: 700; color: #dc3545; margin-bottom: 12px;">I can't answer this reliably</div>""",
                unsafe_allow_html=True,
            )
            reason = result.get("reason", "")
            needed = result.get("needed", "")
            st.markdown(f"**Why:** {reason}")
            st.markdown(f"**What I'd need:** {needed}")

    else:
        with st.container(border=True):
            st.markdown(
                """<div class="result-top-grey" style="height: 5px; background-color: #64748b; margin: -1rem -1rem 1rem -1rem; border-top: 5px solid #64748b; border-top-left-radius: 10px; border-top-right-radius: 10px;"></div>""",
                unsafe_allow_html=True,
            )
            reason = result.get("reason", "") or result.get("answer", "") or "An unexpected error occurred."
            st.markdown(
                f"""<div style="font-size: 1.1rem; font-weight: 600; color: #1e293b; margin-top: 4px;">{html.escape(str(reason))}</div>""",
                unsafe_allow_html=True,
            )
