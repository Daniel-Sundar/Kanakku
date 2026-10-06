"""ProofPilot screen.  Owner: A.   Run:  streamlit run app.py

This skeleton already works with the mock engine. Your tickets turn each TODO into a nice UI:
  A3: dataset picker + Data Health cards
  A4: answer card (green), refusal card (red), error card (grey), code viewer,
      Re-run button, Download proof button, AI-mode badge
Only call these functions (they are the contract, see CLAUDE.md):
  load_folder(path) -> tables        profile_all(tables) -> flags
  run_question(question, tables, flags) -> result        rerun_proof(proof_path) -> {"value", "match"}
"""
from pathlib import Path

import streamlit as st

from engine import rerun_proof, run_question
from loader import load_folder
from profiler import profile_all

st.set_page_config(page_title="Kanakku - The PA", layout="wide")
st.title("Kanakku - The PA")
st.caption("Answers you can verify.")

# ---- A3: dataset picker -------------------------------------------------
datasets = sorted(p.name for p in Path("data").iterdir() if p.is_dir() and any(p.glob("*.csv")))
choice = st.selectbox("Dataset", datasets)
tables = load_folder(f"data/{choice}")
flags = profile_all(tables)

# ---- A3: Data Health report (TODO: turn into coloured cards) ------------
st.subheader(f"Data Health: {len(flags)} trap(s) found")
for f in flags:
    st.write(f"⚠ {f['message']}")

# ---- A4: question + result ------------------------------------------------
question = st.text_input("Ask a question about this data")
if st.button("Ask") and question:
    result = run_question(question, tables, flags)
    st.session_state["result"] = result

result = st.session_state.get("result")
if result:
    # TODO (A4): green / red / grey card depending on result["status"], plus the AI-mode badge
    st.write(result["status"].upper(), "·", result["llm_mode"])
    if result["status"] == "answered":
        st.write(result["answer"])
        st.write("Assumptions:", result["assumptions"])
        st.code(result["code"], language="python")
        # TODO (A4): Re-run button -> rerun_proof(result["proof_path"]); Download proof button
    else:
        st.write(result["answer"] or "Something went wrong.")
        st.write("Why:", result["reason"])
        st.write("Needed:", result["needed"])
