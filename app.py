"""ProofPilot screen.   Run:  streamlit run app.py

Pages: Home · Datasets · Ask · History · Settings · Help
Calls only the frozen contract:
  load_folder(path) -> tables        profile_all(tables) -> flags
  run_question(question, tables, flags) -> result        rerun_proof(proof_path) -> {"value", "match"}
"""
import datetime as dt
import html
import json
import os
import shutil
import socket
import uuid
from pathlib import Path

import streamlit as st

from engine import rerun_proof, run_question
from ingest import save_uploads
from loader import load_folder
from profiler import profile_all

ROOT = Path(__file__).resolve().parent
VERSION = "1.0.0"
REPO_URL = "https://github.com/Daniel-Sundar/Kanakku"
SUPPORT_URL = REPO_URL + "/issues"
DEMOS = {
    "nimbus_retail": ("Nimbus Retail", "300 orders across 4 tables: orders, two customer lists, exchange rates. "
                                       "Has every trap: duplicates, € and $, ambiguous dates, blanks, tables that disagree."),
    "canteen": ("Campus canteen", "50 sales from 4 food stalls. A different layout, to show nothing is hard-coded."),
    "example": ("Tiny example", "7 orders. Small enough to check every answer by hand."),
}
EXAMPLES = {
    "nimbus_retail": ["What was revenue from USD orders in January 2024?",
                      "Total revenue in April 2024 in USD?",
                      "Total revenue in June 2024 in USD?",
                      "Total USD revenue for West customers in March 2024",
                      "Total revenue in 2019 in USD",
                      "Which month had the highest profit?",
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
TRAP_NAME = {"duplicate_rows": "Duplicate rows", "missing_values": "Blank values",
             "mixed_currency": "Mixed currencies", "ambiguous_date": "Ambiguous dates",
             "missing_period": "Missing month", "contradiction": "Tables disagree"}
PLANNERS = {"cloud": "Cloud AI first (Gemini), then local, then cache",
            "local": "Local AI first (Ollama on this laptop), then cloud, then cache",
            "replay": "Cached AI replies only (no internet needed)",
            "rules": "No AI: built-in rule planner (fully offline)"}

st.set_page_config(page_title="ProofPilot · Numbers you can check", page_icon=str(ROOT / "assets" / "favicon.png"),
                   layout="wide", initial_sidebar_state="auto",
                   menu_items={"About": f"ProofPilot {VERSION}: every number comes with a Python proof you can "
                                        "re-run. HackNex 2026 · HNX26PSI08.",
                               "Report a bug": SUPPORT_URL, "Get help": REPO_URL + "#readme"})

# ---- Design system: 1 font, 1 primary, 1 accent, 2 backgrounds, radius 8, spacing 4/8/12/16/24/32 ----
st.markdown("""
<style>
:root { --primary: #0f5c4a; --accent: #b7791f; --bg: #ffffff; --bg2: #f6f8f7; --ink: #1c2421;
  --muted: #5f6b66; --line: #dfe5e2; --ok: #157347; --bad: #b42318; --r: 8px; }
html, body, [data-testid="stAppViewContainer"], .main { overflow-x: hidden !important; max-width: 100vw; }
html, body, [class*="css"], .stMarkdown, button, input { font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }
.block-container { padding-top: 24px; padding-bottom: 32px; max-width: 1080px; }
h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.01em; }
h1 { font-size: 1.75rem !important; } h2 { font-size: 1.35rem !important; } h3 { font-size: 1.1rem !important; }
.pp-card { background: var(--bg); border: 1px solid var(--line); border-radius: var(--r); padding: 16px;
  margin-bottom: 12px; color: var(--ink); overflow-wrap: anywhere; box-sizing: border-box; max-width: 100%; }
.pp-muted { color: var(--muted); font-size: .9rem; }
.pp-label { color: var(--muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }
.pp-trap { border-left: 4px solid var(--line); }
.pp-trap.high { border-left-color: var(--bad); } .pp-trap.medium { border-left-color: var(--accent); }
.pp-answer { border-left: 4px solid var(--ok); } .pp-refuse { border-left: 4px solid var(--bad); }
.pp-error { border-left: 4px solid var(--muted); }
.pp-big { font-size: clamp(1.4rem, 5vw, 2rem); font-weight: 700; line-height: 1.25; margin: 4px 0 8px; }
.pp-hero { text-align: center; padding: 48px 16px 32px; }
.pp-hero .name { font-size: clamp(2.2rem, 8vw, 3.2rem); font-weight: 700; color: var(--primary); line-height: 1.1; }
.pp-hero .tag { font-size: 1.1rem; color: var(--muted); margin-top: 12px; }
.pp-badge { display: inline-block; border: 1px solid var(--line); border-radius: var(--r); padding: 4px 8px;
  font-size: .8rem; color: var(--muted); background: var(--bg2); }
.pp-steps { counter-reset: s; list-style: none; padding: 0; margin: 0; }
.pp-steps li { counter-increment: s; padding: 8px 0 8px 32px; position: relative; border-bottom: 1px solid var(--line); }
.pp-steps li:before { content: counter(s); position: absolute; left: 0; top: 8px; width: 20px; height: 20px;
  border-radius: 50%; background: var(--primary); color: #fff; font-size: .75rem; text-align: center; line-height: 20px; }
.pp-footer { border-top: 1px solid var(--line); margin-top: 32px; padding-top: 12px; color: var(--muted);
  font-size: .85rem; display: flex; gap: 16px; flex-wrap: wrap; justify-content: space-between; }
.pp-footer a, .pp-card a { color: var(--primary); }
.stButton button, .stDownloadButton button, .stFormSubmitButton button { border-radius: var(--r); }
pre, code { white-space: pre-wrap !important; overflow-wrap: anywhere; }
[data-testid="column"], [data-testid="stColumn"] { min-width: 0 !important; }
.pp-brand { position: fixed; top: 14px; right: 64px; z-index: 999991; font-weight: 700; font-size: 1.1rem;
  color: var(--primary) !important; text-decoration: none !important; }
.pp-side-name { font-size: 1.3rem; font-weight: 700; color: var(--primary); }
.st-key-theme_toggle { position: fixed; bottom: 16px; right: 16px; z-index: 999990; width: auto !important; }
.st-key-theme_toggle button { border-radius: 999px !important; padding: 6px 6px 6px 18px !important; min-height: 48px;
  background: #eef1f0 !important; color: #3a4440 !important; border: 1px solid #dfe5e2 !important;
  box-shadow: 0 2px 6px rgba(0,0,0,.12), inset 0 1px 0 #fff; font-weight: 700; letter-spacing: .06em; }
.st-key-theme_toggle button > div > span { display: flex !important; flex-direction: row-reverse !important;
  align-items: center; gap: 12px; }
.st-key-theme_toggle button p { font-size: .85rem !important; text-transform: uppercase; line-height: 1.05; margin: 0;
  max-width: 3.4em; text-align: center; white-space: normal; }
.st-key-theme_toggle button [data-testid="stIconMaterial"] { width: 38px !important; height: 38px !important; border-radius: 50%; font-size: 24px !important; flex: none;
  display: flex; align-items: center; justify-content: center; background: #fff; color: #3a4440;
  box-shadow: 0 1px 4px rgba(0,0,0,.2); }
@media (max-width: 640px) {
  .block-container { padding-left: 12px; padding-right: 12px; padding-top: 16px; }
  .pp-hero { padding: 32px 8px 24px; }
  .stButton button, .stFormSubmitButton button { width: 100%; }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
  [data-testid="stColumn"], [data-testid="column"] { flex: 1 1 100% !important; width: 100% !important; }
}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("dataset", None)              # {"kind": "demo"|"upload", "key", "label", "folder"}
ss.setdefault("upload_dir", f"data/uploads/{uuid.uuid4().hex[:8]}")
ss.setdefault("theme", "light")
if ss["theme"] == "dark":
    st.markdown("""<style>:root { --primary: #5ec4a5; --bg: #1b2320; --bg2: #232d29; --ink: #e6ece9; --muted: #9fb0a9;
  --line: #34413c; --ok: #4fbf84; --bad: #f0786b; }
.stApp, [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: #111816 !important; color: #e6ece9; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background: #18211e !important; }
.stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp summary,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] { color: #e6ece9 !important; }
[data-testid="stExpander"] details, [data-testid="stChatMessage"], [data-testid="stForm"],
[data-testid="stFileUploaderDropzone"] { background: #1b2320 !important; border-color: #34413c !important; }
.stApp input, .stApp textarea, [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div, [data-testid="stChatInput"] > div { background: #232d29 !important; color: #e6ece9 !important; border-color: #34413c !important; }
.stButton button[kind="secondary"], .stDownloadButton button { background: #232d29 !important; color: #e6ece9 !important; border-color: #34413c !important; }
.st-key-theme_toggle button { background: #2b3230 !important; color: #f2f5f4 !important; border-color: #3d4643 !important;
  padding: 6px 18px 6px 6px !important; box-shadow: 0 2px 6px rgba(0,0,0,.4); }
.st-key-theme_toggle button > div > span { flex-direction: row !important; }
.st-key-theme_toggle button [data-testid="stIconMaterial"] { background: #3d4643 !important; color: #f2f5f4 !important; }
.stApp pre, .stApp code, [data-testid="stCode"] > div { background: #1b2320 !important; color: #e6ece9 !important; }
[data-testid="stSidebarNavLink"][aria-current="page"], [data-testid="stSidebarNavLink"]:hover { background: #232d29 !important; }
.stTabs [data-baseweb="tab-list"] { border-color: #34413c; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] details > div { background: #1b2320 !important; color: #e6ece9 !important; }
[data-testid="stElementToolbar"], [data-testid="stElementToolbar"] button { background: #232d29 !important; color: #e6ece9 !important; }
.stApp ::placeholder { color: #9fb0a9 !important; opacity: 1; }
[data-testid="stChatMessageAvatarCustom"], [data-testid^="stChatMessageAvatar"] { background: #232d29 !important; color: #e6ece9 !important; border-color: #34413c !important; }
</style>""", unsafe_allow_html=True)
ss.setdefault("user_name", "")
ss.setdefault("planner", os.getenv("LLM_MODE", "cloud"))
os.environ["LLM_MODE"] = ss["planner"]


def esc(x) -> str:
    return html.escape(str(x))


def online() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=0.8).close()
        return True
    except OSError:
        return False


@st.cache_data(show_spinner=False)
def load(folder: str, stamp: float):
    tables = load_folder(folder)
    return tables, profile_all(tables)


def current_data():
    """(tables, flags, error) for the active dataset."""
    d = ss["dataset"]
    if not d:
        return None, None, None
    try:
        stamp = max((p.stat().st_mtime for p in (ROOT / d["folder"]).glob("*.csv")), default=0)
        tables, flags = load(d["folder"], stamp)
        if not tables:
            return None, None, "The dataset has no tables."
        return tables, flags, None
    except Exception as e:  # noqa: BLE001
        return None, None, f"Couldn't load the data: {e}"


def go(page_key: str):
    st.switch_page(PAGES[page_key])


def dataset_bar():
    d = ss["dataset"]
    c1, c2 = st.columns([3, 1])
    if d:
        c1.markdown(f'<div class="pp-label">Active dataset</div><b>{esc(d["label"])}</b>', unsafe_allow_html=True)
        if c2.button("Change dataset", use_container_width=True):
            go("datasets")
    else:
        c1.markdown('<div class="pp-label">Active dataset</div>None selected', unsafe_allow_html=True)
        if c2.button("Choose a dataset", type="primary", use_container_width=True):
            go("datasets")


def trap_cards(flags):
    if not flags:
        st.success("No traps found. This data looks clean.")
        return
    cols = st.columns(3)
    for i, f in enumerate(flags):
        where = f"{f['table']}.{f['column']}" if f["column"] != "*" else f["table"]
        rows = f" · rows {', '.join(map(str, f['example_rows']))}" if f["example_rows"] else ""
        cols[i % 3].markdown(
            f'<div class="pp-card pp-trap {esc(f["severity"])}"><b>{esc(TRAP_NAME.get(f["trap"], f["trap"]))}</b>'
            f'<div>{esc(f["message"])}</div><div class="pp-muted">{esc(where)}{esc(rows)} · {esc(f["severity"])} severity'
            f'</div></div>', unsafe_allow_html=True)


# ============================== Pages ======================================
def page_home():
    st.markdown("""
<div class="pp-hero">
  <div class="name">ProofPilot</div>
  <div class="tag">Numbers you can check, not just trust.</div>
</div>""", unsafe_allow_html=True)
    c = st.columns([1, 2, 2, 1])
    if c[1].button("Choose a dataset", type="primary", use_container_width=True):
        go("datasets")
    if c[2].button("Ask a question", use_container_width=True, disabled=not ss["dataset"],
                   help=None if ss["dataset"] else "Choose a dataset first"):
        go("ask")

    st.write("")
    greet = f", {ss['user_name']}" if ss["user_name"] else ""
    hour = dt.datetime.now().hour
    st.markdown(f"### Good {'morning' if hour < 12 else 'afternoon' if hour < 17 else 'evening'}{greet}")
    h = ss["history"]
    m = st.columns(4)
    m[0].metric("Questions asked", len(h))
    m[1].metric("Answered with proof", sum(x["status"] == "answered" for x in h))
    m[2].metric("Refused with reason", sum(x["status"] == "abstained" for x in h))
    m[3].metric("Active dataset", ss["dataset"]["label"] if ss["dataset"] else "None")
    st.divider()

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### How it works")
        st.markdown("""<ol class="pp-steps">
<li>Pick a demo dataset or upload your own CSV, Excel, PDF or Word tables.</li>
<li>Trap Radar checks the data first: duplicates, mixed currencies, ambiguous dates, blanks, tables that disagree.</li>
<li>Ask in plain English. A plan becomes a small Python proof script.</li>
<li>The proof runs, then runs again in a fresh process. Both results must match.</li>
<li>You get the number with its proof, or a refusal that names the exact rows at fault.</li>
</ol>""", unsafe_allow_html=True)
    with right:
        st.markdown("#### Recent activity")
        if not h:
            st.markdown('<div class="pp-card pp-muted">No questions yet. Your last questions will show here.</div>',
                        unsafe_allow_html=True)
        for x in h[:5]:
            st.markdown(f'<div class="pp-card"><b>{esc(x["status"].title())}</b> · {esc(x["q"])}'
                        f'<div class="pp-muted">{esc(x["time"])} · {esc(x["dataset"])}</div></div>',
                        unsafe_allow_html=True)


def page_datasets():
    st.title("Datasets")
    st.caption("Pick the data ProofPilot should answer from. Demo datasets and your own files are kept separate.")
    tab_demo, tab_up = st.tabs(["Sample datasets", "Upload your files"])
    with tab_demo:
        for key, (label, desc) in DEMOS.items():
            if not (ROOT / "data" / key).is_dir():
                continue
            active = bool(ss["dataset"] and ss["dataset"]["folder"] == f"data/{key}")
            c1, c2 = st.columns([4, 1])
            c1.markdown(f'<div class="pp-card"><b>{esc(label)}</b>{" · <span class=pp-badge>In use</span>" if active else ""}'
                        f'<div class="pp-muted">{esc(desc)}</div></div>', unsafe_allow_html=True)
            if c2.button("In use" if active else "Use this", key=f"use_{key}", disabled=active,
                         use_container_width=True, type="secondary" if active else "primary"):
                ss["dataset"] = {"kind": "demo", "key": key, "label": label, "folder": f"data/{key}"}
                ss.pop("result", None)
                st.toast(f"{label} selected")
                st.rerun()
    with tab_up:
        st.markdown("**Files** <span class='pp-muted'>(required)</span>", unsafe_allow_html=True)
        files = st.file_uploader("Files", type=["csv", "xlsx", "xls", "pdf", "docx"], accept_multiple_files=True,
                                 label_visibility="collapsed",
                                 help="CSV, Excel (one table per sheet), PDF or Word (tables inside are read). "
                                      "Upload related tables together, e.g. orders + customers + exchange rates.")
        st.caption("Accepted: CSV, XLSX, XLS, PDF, DOCX. Tables in PDF and Word files are read; plain paragraphs are not.")
        name = st.text_input("Dataset name (optional)", placeholder="e.g. Q1 sales export",
                             help="A short name so you can recognise this data in History.", max_chars=40)
        if st.button("Load files", type="primary", disabled=not files):
            with st.status("Reading your files…", expanded=True) as status:
                written, errors = save_uploads([(f.name, f.getvalue()) for f in files], ROOT / ss["upload_dir"])
                for e in errors:
                    st.error(e)
                if written:
                    ss["dataset"] = {"kind": "upload", "key": None, "label": name.strip() or "My upload",
                                     "folder": ss["upload_dir"]}
                    ss.pop("result", None)
                    status.update(label=f"Loaded {len(written)} table(s): {', '.join(written)}", state="complete")
                else:
                    status.update(label="No tables could be read from these files", state="error")
        if not files:
            st.info("No files chosen yet. Drag files into the box above or click Browse files.")

    tables, flags, err = current_data()
    if err:
        st.error(err)
    if tables:
        st.divider()
        st.subheader(ss["dataset"]["label"])
        m = st.columns(3)
        m[0].metric("Tables", len(tables))
        m[1].metric("Rows", f"{sum(len(t) for t in tables.values()):,}")
        m[2].metric("Traps found", len(flags))
        st.markdown("#### Trap Radar")
        trap_cards(flags)
        with st.expander("Preview the tables"):
            tname = st.selectbox("Table", list(tables), key=f"preview_{ss['dataset']['folder']}")
            st.dataframe(tables[tname].head(100), use_container_width=True)
        if st.button("Ask a question about this data", type="primary"):
            go("ask")


def ask_now(q, tables, flags):
    with st.chat_message("assistant", avatar=":material/fact_check:"):
        with st.status("Checking the data and building the proof…", expanded=False) as status:
            try:
                r = run_question(q, tables, flags)
            except Exception as e:  # noqa: BLE001
                r = {"status": "error", "reason": f"Something went wrong: {e}", "answer": "", "value": None,
                     "unit": "", "assumptions": [], "code": "", "proof_path": "", "rerun_match": False,
                     "needed": "", "llm_mode": "error", "seconds": 0}
            status.update(state="error" if r["status"] == "error" else "complete")
    r["question"] = q
    r["folder"] = ss["dataset"]["folder"]
    ss["chat"].append(r)
    ss["history"].insert(0, {"q": q, "status": r["status"], "answer": r["answer"], "reason": r["reason"],
                             "proof": r["proof_path"], "dataset": ss["dataset"]["label"],
                             "time": dt.datetime.now().strftime("%H:%M")})
    st.rerun()


def page_ask():
    ss.setdefault("chat", [])
    ss.setdefault("reruns", {})
    st.title("Ask")
    dataset_bar()
    tables, flags, err = current_data()
    if err:
        st.error(err)
        return
    if not tables:
        st.markdown('<div class="pp-card"><b>No dataset selected</b><div class="pp-muted">Choose a sample dataset '
                    'or upload your files, then come back here to ask.</div></div>', unsafe_allow_html=True)
        return
    if flags:
        st.caption(f"Trap Radar found {len(flags)} issue(s) in this data. ProofPilot handles them or refuses.")
    chat = [r for r in ss["chat"] if r.get("folder") == ss["dataset"]["folder"]]
    if not chat:
        st.markdown('<div class="pp-label">Try one of these</div>', unsafe_allow_html=True)
        examples = EXAMPLES.get(ss["dataset"]["key"], GENERIC)
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
                ss["pending"] = ex
                st.rerun()
    else:
        c1, c2 = st.columns([4, 1])
        c1.caption("Answers appear above the question box. Every number has a proof you can re-run.")
        if c2.button("Clear chat", use_container_width=True):
            ss["chat"] = [r for r in ss["chat"] if r.get("folder") != ss["dataset"]["folder"]]
            st.rerun()
    for i, r in enumerate(chat):
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(esc(r["question"]))
        with st.chat_message("assistant", avatar=":material/fact_check:"):
            show_result(r, i)

    q = st.chat_input("Ask a total, count, average or list, e.g. Total revenue from 2024-01-02 to 2024-02-06 in USD", max_chars=300)
    q = ss.pop("pending", None) or q
    if q is not None:
        q = q.strip()
        if len(q) < 8 or len(q.split()) < 2:
            st.error("That's too short to answer. Ask a full question, e.g. \"Total sales in May 2024\".")
        else:
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(esc(q))
            ask_now(q, tables, flags)


def show_result(r, i=0):
    if r["status"] == "answered":
        if isinstance(r["value"], dict):
            st.markdown('<div class="pp-card pp-answer"><div class="pp-label">Answer · two readings</div>'
                        '<div class="pp-big">It depends on the date format</div><div class="pp-muted">Some dates can '
                        'be read two ways, so both answers are proven.</div></div>', unsafe_allow_html=True)
            mcols = st.columns(len(r["value"]))
            for c, (k, v) in zip(mcols, r["value"].items()):
                shown = f"{v:,.2f} {r['unit']}".strip() if isinstance(v, float) else f"{v:,}"
                c.metric("If dates are " + k.replace("if_", ""), shown)
        elif r.get("unit") == "list":
            items = "".join(f"<li>{esc(x)}</li>" for x in r["value"])
            st.markdown(f'<div class="pp-card pp-answer"><div class="pp-label">Answer</div>'
                        f'<div class="pp-big">{esc(r["answer"].split(":")[0])}</div><ul>{items}</ul>'
                        f'<div class="pp-muted">Verified: the proof ran twice in fresh processes and gave the same '
                        f'list · {r["seconds"]}s</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="pp-card pp-answer"><div class="pp-label">Answer</div>'
                        f'<div class="pp-big">{esc(r["answer"])}</div><div class="pp-muted">Verified: the proof ran '
                        f'twice in fresh processes and gave the same result · {r["seconds"]}s · planner: '
                        f'{esc(r["llm_mode"])}</div></div>', unsafe_allow_html=True)
        with st.expander("How it was worked out"):
            for a in r["assumptions"] or ["No traps touched this answer."]:
                st.markdown(f"- {a}")
        with st.expander("Proof code"):
            st.code(r["code"], language="python")
            b1, b2 = st.columns(2)
            if b1.button("Re-run proof", key=f"rerun_{i}", use_container_width=True):
                with st.spinner("Re-running in a fresh process…"):
                    try:
                        ss["reruns"][r["proof_path"]] = rerun_proof(r["proof_path"])
                    except Exception as e:  # noqa: BLE001
                        ss["reruns"][r["proof_path"]] = {"match": False, "value": str(e)}
            p = ROOT / r["proof_path"] if r["proof_path"] else None
            if p and p.exists():
                b2.download_button("Download proof (.py)", p.read_text(), file_name=p.name, key=f"dl_{i}",
                                   mime="text/x-python", use_container_width=True)
            done = ss.get("reruns", {}).get(r["proof_path"])
            if done:
                if done["match"]:
                    st.success(f"Re-ran in a fresh process: same answer ({done['value']}).")
                else:
                    st.error(f"Re-run did not match: {done['value']}")
            st.caption(f"Run it yourself:  python {r['proof_path']}")
    elif r["status"] == "abstained":
        st.markdown(f'<div class="pp-card pp-refuse"><div class="pp-label">Refused</div>'
                    f'<div class="pp-big">I can\'t answer this reliably</div>'
                    f'<p><b>Why:</b> {esc(r["reason"])}</p><p><b>What would fix it:</b> {esc(r["needed"])}</p>'
                    f'</div>', unsafe_allow_html=True)
        if r.get("code"):
            with st.expander("The proof that found the problem"):
                st.code(r["code"], language="python")
    else:
        st.markdown(f'<div class="pp-card pp-error"><div class="pp-label">Error</div>'
                    f'<div class="pp-big">Something went wrong</div><p>{esc(r["reason"])}</p>'
                    f'<p class="pp-muted">{esc(r.get("needed") or "Try rephrasing, e.g. include a month and a currency.")}</p></div>',
                    unsafe_allow_html=True)


def page_history():
    st.title("History")
    h = ss["history"]
    if not h:
        st.markdown('<div class="pp-card"><b>No questions yet</b><div class="pp-muted">Questions you ask on the Ask '
                    'page show up here with their answer and proof file.</div></div>', unsafe_allow_html=True)
        if st.button("Ask a question", type="primary"):
            go("ask")
        return
    search = st.text_input("Search", placeholder="e.g. January", help="Filters by question text.")
    status = st.radio("Show", ["All", "Answered", "Refused", "Errors"], horizontal=True)
    want = {"Answered": "answered", "Refused": "abstained", "Errors": "error"}.get(status)
    rows = [x for x in h if (not want or x["status"] == want) and search.lower() in x["q"].lower()]
    st.caption(f"{len(rows)} of {len(h)} question(s)")
    if not rows:
        st.info("Nothing matches this filter.")
    for x in rows:
        cls = {"answered": "pp-answer", "abstained": "pp-refuse"}.get(x["status"], "pp-error")
        body = esc(x["answer"]) if x["status"] == "answered" else esc(x["reason"])
        st.markdown(f'<div class="pp-card {cls}"><b>{esc(x["q"])}</b><div>{body}</div><div class="pp-muted">'
                    f'{esc(x["time"])} · {esc(x["dataset"])}{" · " + esc(x["proof"]) if x["proof"] else ""}</div></div>',
                    unsafe_allow_html=True)


def reset_session():
    shutil.rmtree(ROOT / ss["upload_dir"], ignore_errors=True)
    for k in list(ss.keys()):
        del ss[k]


def page_settings():
    st.title("Settings")
    t_acc, t_ai, t_app, t_data, t_priv, t_about = st.tabs(["Account", "AI planner", "Appearance", "Data",
                                                           "Privacy & security", "About"])
    with t_acc:
        st.markdown("ProofPilot runs on this computer and has no sign-in, so there is no password or account to "
                    "manage. Your name is only used for the greeting on Home.")
        with st.form("account"):
            n = st.text_input("Display name (optional)", value=ss["user_name"], max_chars=30, placeholder="e.g. Daniel")
            if st.form_submit_button("Save", type="primary"):
                ss["user_name"] = n.strip()
                st.success("Saved.")
        if st.button("End session", help="Clears your name, dataset choice, history and uploads from this browser tab."):
            reset_session()
            st.success("Session ended. Everything from this tab was cleared.")
    with t_ai:
        net = online()
        st.markdown(f"Internet: **{'connected' if net else 'offline'}**")
        if not net:
            st.warning("You're offline. Cloud AI won't work; ProofPilot falls back to local AI, cached replies, "
                       "then the rule planner, so answers still work.")
        modes = list(PLANNERS)
        choice = st.radio("Planner order", modes, format_func=PLANNERS.get,
                          index=modes.index(ss.get("planner")) if ss.get("planner") in modes else 0)
        if choice != ss.get("planner"):
            ss["planner"] = os.environ["LLM_MODE"] = choice
            st.success(f"Planner set: {PLANNERS[choice]}.")
        st.caption("Whichever planner is used, the number always comes from running the proof, never from the AI. "
                   "If the AI's plan is invalid, the rule planner takes over.")
    with t_app:
        st.markdown("Light and dark mode follow your system. To switch, open the ⋮ menu (top right), then "
                    "Settings, then Theme.")
    with t_data:
        st.markdown("**Export**")
        st.download_button("Export history (JSON)", json.dumps(ss.get("history", []), indent=2),
                           file_name="proofpilot_history.json", mime="application/json",
                           disabled=not ss.get("history"))
        st.markdown("**Import**")
        st.caption("Import data on the Datasets page (CSV, Excel, PDF or Word).")
        if st.button("Go to Datasets"):
            go("datasets")
        st.markdown("**Clear**")
        c1, c2 = st.columns(2)
        if c1.button("Clear history", disabled=not ss.get("history"), use_container_width=True):
            ss["history"].clear()
            ss.pop("result", None)
            st.success("History cleared.")
        if c2.button("Delete my uploaded files", use_container_width=True):
            shutil.rmtree(ROOT / ss["upload_dir"], ignore_errors=True)
            if ss["dataset"] and ss["dataset"]["kind"] == "upload":
                ss["dataset"] = None
            st.success("Uploaded files deleted from this computer.")
    with t_priv:
        st.markdown("""
- **Your data stays here.** Uploaded files are saved only on this computer, in `data/uploads/`.
- **With the rule planner or local AI, nothing leaves the laptop.** With cloud AI, only column names, 3 sample rows and your question are sent to build the plan.
- **Proof code is sandboxed.** Before it runs, a safety check allows only pandas, numpy, json, math, datetime, pathlib, re and hashlib, and blocks calls like `eval`, `exec` and `open`. It runs in a separate process with a 20-second limit.
- **Tampering is caught.** Each proof stores a fingerprint of the data; a re-run on edited files fails the check.""")
    with t_about:
        st.markdown(f"""
**ProofPilot {VERSION}** · HackNex 2026 · HNX26PSI08 Proof-Carrying Data Analyst
Team: Daniel, Ajay, Aaron, Gladys

- Source code and README: [{REPO_URL}]({REPO_URL})
- Terms, scope note and declared resources: [README]({REPO_URL}#readme)
- Contact support: [open an issue]({SUPPORT_URL})""")


def page_help():
    st.title("Help")
    st.markdown("#### Quick start")
    st.markdown("""<ol class="pp-steps">
<li>Open <b>Datasets</b> and press <b>Use this</b> on Nimbus Retail (or upload your files).</li>
<li>Read the Trap Radar: the problems found in the data before any question is asked.</li>
<li>Open <b>Ask</b>, type a question or press an example.</li>
<li>Open <b>Proof code</b> and press <b>Re-run proof</b>, or download it and run <code>python proofs/q_1.py</code>.</li>
</ol>""", unsafe_allow_html=True)
    st.markdown("#### Common questions")
    faq = {
        "Why did it refuse my question?": "It refuses when the answer would be a guess: a blank value inside the "
            "rows you asked about, two tables that disagree, a missing exchange rate, a period or name that isn't in "
            "the data, a concept with no column (like profit), or a \"why\" question. The refusal says what would fix it.",
        "Why did I get two answers?": "Some dates like 03/04/2024 can mean 3 April or 4 March. If that changes the "
            "answer, both readings are computed and proven.",
        "What does \"proof\" mean here?": "A standalone Python file that reads the original CSV files and prints "
            "RESULT=... . Anyone can run it and get the same number. The answer text is copied from that output.",
        "Which files can I upload?": "CSV, Excel (each sheet becomes a table), and PDF or Word files that contain "
            "tables. Upload related tables together so they can be joined, e.g. on customer_id.",
        "Does it need the internet?": "No. Without internet it uses local AI if installed, else the built-in rule "
            "planner. Answers and proofs work the same.",
    }
    for q, a in faq.items():
        with st.expander(q):
            st.write(a)
    st.markdown(f"#### Support\nSomething broken? [Open an issue]({SUPPORT_URL}) or read the "
                f"[README]({REPO_URL}#readme).")


PAGES = {
    "home": st.Page(page_home, title="Home", url_path="home", default=True),
    "datasets": st.Page(page_datasets, title="Datasets", url_path="datasets"),
    "ask": st.Page(page_ask, title="Ask", url_path="ask"),
    "history": st.Page(page_history, title="History", url_path="history"),
    "settings": st.Page(page_settings, title="Settings", url_path="settings"),
    "help": st.Page(page_help, title="Help", url_path="help"),
}
st.markdown('<a class="pp-brand" href="./home" target="_self">ProofPilot</a>', unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="pp-side-name">ProofPilot</div><div class="pp-muted">Numbers you can check</div>',
                unsafe_allow_html=True)
with st.container(key="theme_toggle"):
    dark = ss["theme"] == "dark"
    if st.button("Dark mode" if dark else "Light mode", icon=":material/dark_mode:" if dark else ":material/light_mode:",
                 help="Switch to light mode" if dark else "Switch to dark mode"):
        ss["theme"] = "light" if dark else "dark"
        st.rerun()
st.navigation(list(PAGES.values()), position="sidebar").run()

st.markdown(f"""
<div class="pp-footer">
  <span>© {dt.date.today().year} ProofPilot · HackNex 2026 · HNX26PSI08 · v{VERSION}</span>
  <span><a href="{REPO_URL}" target="_blank" rel="noopener">Source code</a> ·
  <a href="{REPO_URL}#readme" target="_blank" rel="noopener">How to reproduce</a> ·
  <a href="{SUPPORT_URL}" target="_blank" rel="noopener">Report a problem</a></span>
</div>""", unsafe_allow_html=True)
