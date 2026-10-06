# Kanakku - The PA: numbers you can check, not just trust
> HackNex 2026 · HNX26PSI08 Proof-Carrying Data Analyst · Team: TODO (names)

<!-- Owner: B (ticket B5). Fill every TODO. Keep each section short. -->

Kanakku - The PA is the friend every team needs: the one who actually checks the bill before splitting it.

Ask it anything about your messy spreadsheets: "How much did we sell in March?" or "Which region earned the most?" Kanakku gives you the answer and the working, like the topper in class who writes every step on the board. Every number comes with a tiny Python script you can re-run yourself. Same data, same number, every time.

And when the data is fishy (the same order written twice, dollars mixed with euros, a date that could be 3 February or 2 March), Kanakku doesn't bluff. It points at the exact rows and says, "Boss, idhu kanakku-la varala." (Boss, this doesn't add up.) Then it tells you what it needs to get it right.

No guesswork. No fake confidence. Just clean kanakku.

## What it is
TODO: 3 sentences. An AI data analyst for messy multi-table data. Every number comes with a Python proof script anyone can re-run. When the data can't support an answer, it refuses and says exactly why.

## How it works
TODO: the 6 steps (load → Trap Radar → AI writes pandas code → run in a safe sandbox → re-run in a fresh process → answer or refuse). Add a screenshot from `docs/screens/`.

## Tech
TODO: Python 3.11, pandas, Streamlit, LLM (which cloud model / Ollama qwen2.5-coder:7b), replay mode.

## Install
```bash
git clone TODO
cd kanakku
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py                 # mock engine (default)
ENGINE=real LLM_MODE=replay streamlit run app.py   # TODO: confirm with Daniel
```

## Reproduce our numbers
```bash
python verify_all.py     # re-runs every proof script
python eval.py           # benchmark score -> EVAL.md
```

## Sample input / output
TODO: one answered question, one refused question (copy from the app).

## Scope note
TODO: what is built (MVP) vs what is stretch / not done.

## Declared resources
TODO: every API, model and dataset used (our datasets are synthetic, made by the team).

## Team
TODO: name: role, for all 4.
