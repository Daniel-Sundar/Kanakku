"""ProofPilot screen.   Run:  streamlit run app.py

Calls only the frozen contract:
  load_folder(path) -> tables        profile_all(tables) -> flags
  run_question(question, tables, flags) -> result        rerun_proof(proof_path) -> {"value", "match"}
"""
import datetime as dt
import html
import uuid
from pathlib import Path

import streamlit as st

from engine import rerun_proof, run_question
from ingest import save_uploads
from loader import load_folder
from profiler import profile_all

ROOT = Path(__file__).resolve().parent
REPO_URL = "https://github.com/Daniel-Sundar/Kanakku"
DEMO_LABELS = {"nimbus_retail": "Nimbus Retail (300 orders, 4 tables)",
               "example": "Tiny example (7 orders)", "canteen": "Campus canteen (50 sales)"}
EXAMPLES = {
    "nimbus_retail": ["What was revenue from USD orders in January 2024?",
                      "Total revenue in April 2024 in USD?",
                      "Total revenue in June 2024 in USD?",
                      "Why did revenue drop in February?"],
    "example": ["What was revenue from USD orders in January 2024?",
                "Total revenue in March 2024 in USD?",
                "Revenue from North-region customers in March 2024 (USD)?",
                "Which month had the highest profit?"],
    "canteen": ["How many sales did Dosa Corner make in September 2024?",
                "Total sales from Hostel Block in September 2024",
                "Total sales in September 2024"],
}
GENERIC = ["What was the total amount in 2024?", "How many rows are there in 2024?"]
TRAP_ICON = {"duplicate_rows": "🔁", "missing_values": "🕳️", "mixed_currency": "💱",
             "ambiguous_date": "📅", "missing_period": "📆", "contradiction": "⚔️"}
TRAP_NAME = {"duplicate_rows": "Duplicate rows", "missing_values": "Blank values",
             "mixed_currency": "Mixed currencies", "ambiguous_date": "Ambiguous dates",
             "missing_period": "Missing month", "contradiction": "Tables disagree"}

st.set_page_config(page_title="ProofPilot · Numbers you can check", page_icon=str(ROOT / "assets" / "favicon.png"),
                   layout="wide", initial_sidebar_state="auto",
                   menu_items={"About": "ProofPilot: every number comes with a Python proof you can re-run. "
                                        "HackNex 2026 · HNX26PSI08."})

st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], .main { overflow-x: hidden !important; max-width: 100vw; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1150px; }
:root { --brand: #0f5c4a; --gold: #f2b705; --ink: #1f2330; --muted: #64748b; --line: #e2e8f0; }
.pp-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 16px; }
.pp-logo { display: flex; align-items: center; gap: 12px; text-decoration: none !important; }
.pp-mark { width: 44px; height: 44px; border-radius: 12px; background: var(--brand); color: var(--gold);
  display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 900; flex: none; }
.pp-name { color: var(--brand); font-size: 1.7rem; font-weight: 800; line-height: 1.1; }
.pp-tag { color: var(--muted); font-size: .95rem; }
.pp-pill { background: #ecfdf5; color: var(--brand); border: 1px solid #a7f3d0; border-radius: 999px;
  padding: 4px 12px; font-size: .8rem; font-weight: 700; white-space: nowrap; }
.pp-card { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
  margin-bottom: 10px; box-shadow: 0 1px 3px rgba(15,23,42,.06); overflow-wrap: anywhere; color: var(--ink); }
.pp-trap { border-left: 5px solid #94a3b8; }
.pp-trap.high { border-left-color: #dc2626; } .pp-trap.medium { border-left-color: #f59e0b; }
.pp-trap b { display: block; margin-bottom: 2px; }
.pp-small { color: var(--muted); font-size: .82rem; }
.pp-answer { border-top: 5px solid #16a34a; } .pp-refuse { border-top: 5px solid #dc2626; }
.pp-error { border-top: 5px solid #94a3b8; }
.pp-big { font-size: clamp(1.4rem, 5vw, 2.3rem); font-weight: 800; color: var(--ink); line-height: 1.2; }
.pp-step { display: inline-block; width: 22px; height: 22px; border-radius: 50%; background: var(--brand);
  color: #fff; text-align: center; font-size: .75rem; line-height: 22px; margin-right: 6px; }
.pp-footer { border-top: 1px solid var(--line); margin-top: 28px; padding-top: 12px; color: var(--muted);
  font-size: .85rem; display: flex; gap: 14px; flex-wrap: wrap; justify-content: space-between; }
.pp-footer a { color: var(--brand); }
pre, code { white-space: pre-wrap !important; overflow-wrap: anywhere; }
[data-testid="stDataFrame"] { max-width: 100%; }
[data-testid="column"], [data-testid="stColumn"] { min-width: 0 !important; }
.pp-card, .pp-header { box-sizing: border-box; max-width: 100%; }
@media (max-width: 640px) {
  .block-container { padding-left: .8rem; padding-right: .8rem; }
  .pp-name { font-size: 1.35rem; } .pp-tag { font-size: .85rem; }
  .stButton button { width: 100%; }
}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("upload_dir", f"data/uploads/{uuid.uuid4().hex[:8]}")


def esc(x) -> str:
    return html.escape(str(x))


# ---- Sidebar (on phones this collapses into the menu button) ---------------
with st.sidebar:
    st.markdown("### Data")
    source = st.radio("Where is your data?", ["Demo datasets", "Upload my files"], label_visibility="collapsed")
    folder, dataset_key = None, None
    if source == "Demo datasets":
        demos = [d for d in DEMO_LABELS if (ROOT / "data" / d).is_dir()]
        dataset_key = st.selectbox("Dataset", demos, format_func=lambda d: DEMO_LABELS[d])
        folder = f"data/{dataset_key}"
    else:
        files = st.file_uploader("CSV, Excel, PDF or Word (tables are read from PDF/Word)",
                                 type=["csv", "xlsx", "xls", "pdf", "docx"], accept_multiple_files=True)
        if files:
            sig = tuple((f.name, f.size) for f in files)
            if ss.get("upload_sig") != sig:
                written, errors = save_uploads([(f.name, f.getvalue()) for f in files], ROOT / ss["upload_dir"])
                ss["upload_sig"], ss["upload_msgs"] = sig, (written, errors)
                ss.pop("result", None)
            written, errors = ss["upload_msgs"]
            for e in errors:
                st.error(e)
            if written:
                st.success(f"Loaded {len(written)} table(s): {', '.join(written)}")
                folder = ss["upload_dir"]
        else:
            st.info("Upload one or more files. Put related tables together (e.g. orders + customers + exchange rates).")
    st.markdown("---")
    st.markdown("### How ProofPilot works")
    for i, s in enumerate(["Load your tables", "Trap Radar checks the data", "AI turns your question into a plan",
                           "A Python proof runs in a sandbox", "The proof is re-run in a fresh process",
                           "Answer with proof, or refuse with the reason"], 1):
        st.markdown(f'<span class="pp-step">{i}</span>{s}', unsafe_allow_html=True)
    if ss["history"]:
        st.markdown("---")
        st.markdown("### History")
        for h in ss["history"][:8]:
            dot = {"answered": "🟢", "abstained": "🔴"}.get(h["status"], "⚪")
            st.markdown(f"{dot} {esc(h['q'])}", unsafe_allow_html=True)

# ---- Header ----------------------------------------------------------------
mode = ss["result"]["llm_mode"] if ss.get("result") else "ready"
st.markdown(f"""
<div class="pp-header">
  <a class="pp-logo" href="./" target="_self" title="ProofPilot home">
    <div class="pp-mark">✓</div>
    <div><div class="pp-name">ProofPilot</div><div class="pp-tag">Numbers you can check, not just trust.</div></div>
  </a>
  <span class="pp-pill" title="Which planner answered the last question">AI mode: {esc(mode)}</span>
</div>""", unsafe_allow_html=True)

tables = {}
if not folder:
    st.info("Pick a demo dataset or upload your files in the menu to start.")
else:
    try:
        tables = load_folder(folder)
    except Exception as e:  # noqa: BLE001
        st.error(f"Couldn't load the data: {e}")

if tables:
    flags = profile_all(tables)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tables", len(tables))
    c2.metric("Rows", f"{sum(len(t) for t in tables.values()):,}")
    c3.metric("Traps found", len(flags))

    with st.expander("Preview the data", expanded=False):
        name = st.selectbox("Table", list(tables), key=f"preview_{folder}")
        st.dataframe(tables[name].head(50), use_container_width=True)

    st.subheader("🛰️ Trap Radar")
    if not flags:
        st.success("No traps found. This data looks clean.")
    else:
        cols = st.columns(3)
        for i, f in enumerate(flags):
            where = f"{f['table']}.{f['column']}" if f["column"] != "*" else f["table"]
            rows = f" · rows {', '.join(map(str, f['example_rows']))}" if f["example_rows"] else ""
            cols[i % 3].markdown(
                f'<div class="pp-card pp-trap {esc(f["severity"])}">'
                f'<b>{TRAP_ICON.get(f["trap"], "⚠️")} {esc(TRAP_NAME.get(f["trap"], f["trap"]))}</b>'
                f'{esc(f["message"])}<div class="pp-small">{esc(where)}{esc(rows)}</div></div>',
                unsafe_allow_html=True)

    # ---- Ask ---------------------------------------------------------------
    st.subheader("💬 Ask a question")
    examples = EXAMPLES.get(dataset_key, GENERIC)
    ex_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if ex_cols[i].button(ex, key=f"ex_{dataset_key}_{i}", use_container_width=True):
            ss["question"] = ex
            ss["run_now"] = True
    with st.form("ask", border=False):
        st.text_input("Your question", key="question", label_visibility="collapsed",
                      placeholder="e.g. What was revenue from USD orders in January 2024?")
        submitted = st.form_submit_button("Ask ProofPilot", type="primary", use_container_width=True)
    if submitted or ss.pop("run_now", False):
        question = ss.get("question", "").strip()
        if not question:
            st.warning("Type a question first.")
        else:
            with st.spinner("Checking the data and building the proof…"):
                try:
                    r = run_question(question, tables, flags)
                except Exception as e:  # noqa: BLE001
                    r = {"status": "error", "reason": f"Something went wrong: {e}", "answer": "", "value": None,
                         "unit": "", "assumptions": [], "code": "", "proof_path": "", "rerun_match": False,
                         "needed": "", "llm_mode": "error", "seconds": 0}
            r["question"] = question
            ss["result"] = r
            ss.pop("rerun", None)
            ss["history"].insert(0, {"q": question, "status": r["status"]})
            st.rerun()

    # ---- Result ------------------------------------------------------------
    r = ss.get("result")
    if r:
        st.markdown(f"**Q:** {esc(r.get('question', ''))}")
        if r["status"] == "answered":
            if isinstance(r["value"], dict):
                st.markdown('<div class="pp-card pp-answer"><div class="pp-big">Two possible answers</div>'
                            '<div class="pp-small">A date in the data can be read two ways, so both are proven'
                            '</div></div>', unsafe_allow_html=True)
                mcols = st.columns(len(r["value"]))
                for c, (k, v) in zip(mcols, r["value"].items()):
                    shown = f"{v:,.2f} {r['unit']}".strip() if isinstance(v, float) else f"{v:,}"
                    c.metric("If dates are " + k.replace("if_", ""), shown)
            else:
                st.markdown(f'<div class="pp-card pp-answer"><div class="pp-big">{esc(r["answer"])}</div>'
                            f'<div class="pp-small">Verified ✔ re-run in a fresh process · {r["seconds"]}s · '
                            f'planner: {esc(r["llm_mode"])}</div></div>', unsafe_allow_html=True)
            st.success("Answer verified: the proof ran twice in fresh processes and gave the same result.")
            tab1, tab2 = st.tabs(["🧾 How it was worked out", "🐍 Proof code"])
            with tab1:
                for a in r["assumptions"] or ["No traps touched this answer."]:
                    st.markdown(f"- {a}")
            with tab2:
                st.code(r["code"], language="python")
                b1, b2 = st.columns(2)
                if b1.button("🔁 Re-run proof", use_container_width=True):
                    try:
                        ss["rerun"] = rerun_proof(r["proof_path"])
                    except Exception as e:  # noqa: BLE001
                        ss["rerun"] = {"match": False, "value": str(e)}
                p = ROOT / r["proof_path"] if r["proof_path"] else None
                if p and p.exists():
                    b2.download_button("⬇️ Download proof", p.read_text(), file_name=p.name,
                                       mime="text/x-python", use_container_width=True)
                if "rerun" in ss:
                    if ss["rerun"]["match"]:
                        st.success(f"Re-ran in a fresh process: same answer ({ss['rerun']['value']}) ✔")
                    else:
                        st.error(f"Re-run did NOT match: {ss['rerun']['value']}")
                st.caption(f"Run it yourself:  python {r['proof_path']}")
        elif r["status"] == "abstained":
            st.markdown(f'<div class="pp-card pp-refuse"><div class="pp-big">I can\'t answer this reliably</div>'
                        f'<p><b>Why:</b> {esc(r["reason"])}</p><p><b>What I\'d need:</b> {esc(r["needed"])}</p>'
                        f'</div>', unsafe_allow_html=True)
            st.info("Refusing is on purpose: a confident wrong number is worse than an honest \"I can't tell\".")
            if r.get("code"):
                with st.expander("🐍 The proof that found the problem"):
                    st.code(r["code"], language="python")
        else:
            st.markdown(f'<div class="pp-card pp-error"><div class="pp-big">Something went wrong</div>'
                        f'<p>{esc(r["reason"])}</p></div>', unsafe_allow_html=True)
            st.error("Try rephrasing the question, e.g. include a month and a currency.")

# ---- Footer ----------------------------------------------------------------
st.markdown(f"""
<div class="pp-footer">
  <span>© {dt.date.today().year} ProofPilot · HackNex 2026 · HNX26PSI08</span>
  <span><a href="{REPO_URL}" target="_blank" rel="noopener">Source code</a> ·
  <a href="{REPO_URL}#readme" target="_blank" rel="noopener">How to reproduce</a> ·
  <a href="{REPO_URL}/issues" target="_blank" rel="noopener">Report a problem</a></span>
</div>""", unsafe_allow_html=True)
