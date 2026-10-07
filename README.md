# ProofPilot: numbers you can check, not just trust
> HackNex 2026 · HNX26PSI08 Proof-Carrying Data Analyst · Team: Daniel, Ajay, Aaron, Gladys

ProofPilot is the friend every team needs: the one who actually checks the bill before splitting it.

Ask it anything about your messy spreadsheets: "How much did we sell in March?" or "Which region earned the most?" ProofPilot gives you the answer and the working, like the topper in class who writes every step on the board. Every number comes with a tiny Python script you can re-run yourself. Same data, same number, every time.

And when the data is fishy (the same order written twice, dollars mixed with euros, a date that could be 3 February or 2 March), ProofPilot doesn't bluff. It points at the exact rows and says, "Boss, idhu kanakku-la varala." (Boss, this doesn't add up.) Then it tells you what it needs to get it right.

No guesswork. No fake confidence. Just clean numbers. (Kanakku, as we say in Tamil.)

## What it is
An AI data analyst for messy multi-table CSV data. Every number it returns ships with a standalone Python proof script (`proofs/q_<n>.py`) that re-reads the CSVs and re-computes it. When the data can't support an answer, it refuses and says exactly which rows or values are the problem and what it would need.

## How it works
1. **Load** a demo dataset, or upload your own CSV, Excel, PDF or Word files (`ingest.py` pulls every table out of PDFs and Word files and saves it as CSV, so proofs can re-read it).
2. **Trap Radar** (`profiler.py`, `profiler_checks.py`) flags problems before any AI runs: duplicate rows, blank values, mixed currencies, ambiguous dates (03/02/2024), missing exchange-rate months, and tables that disagree (customer C3 is North in one table, South in another).
3. **Plan.** The AI (Gemini in the cloud, or Ollama `qwen2.5-coder:7b` offline) turns the question into a small JSON plan: months, currency, filters, sum/count/average. It never types a number. If no AI is reachable, a rule parser makes the same plan.
4. **Proof.** The plan is written into a Python proof script (`proof_template.py`) that handles every trap with a stated rule. An AST check (`executor.py`) allows only pandas, numpy, json, math, datetime, pathlib and re, and blocks exec/eval/open.
5. **Run twice.** The proof runs in a fresh subprocess with a timeout, then again in another fresh process (`verifier.py`). The two results must match to 2 decimals, and a proof that never reads a data file is rejected.
6. **Answer or refuse.** The answer text is copied from the proof's `RESULT=` line. If the data can't support the answer, the proof itself refuses. Two plausible readings (DD/MM vs MM/DD) produce a conditional answer with both numbers.

## Tech
Python 3.11+, pandas, numpy, Streamlit, pytest, requests, openpyxl (Excel), pdfplumber (PDF tables), python-docx (Word tables). LLM: Google Gemini API (`gemini-flash-latest`, free tier) or Ollama `qwen2.5-coder:7b` (local, offline). `LLM_MODE=cloud|local|replay|rules`, falling back automatically; every AI reply is cached in `replay_cache/` so the demo works offline.

## Install
```bash
git clone https://github.com/Daniel-Sundar/Kanakku.git
cd Kanakku
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional, for the cloud AI: put GEMINI_API_KEY=... in a file called .env (never commit it)
# optional, for the offline AI: install Ollama, then  ollama pull qwen2.5-coder:7b
```

## Run
```bash
streamlit run app.py                         # AI if reachable, otherwise the rule planner
LLM_MODE=local streamlit run app.py          # offline AI with Ollama
LLM_MODE=rules streamlit run app.py          # no AI at all
ENGINE=mock streamlit run app.py             # canned answers, for UI work
```

## Reproduce our numbers
```bash
python verify_all.py            # re-runs every saved proof in a fresh process
python proofs/example/q1_jan_usd_revenue.py     # any single proof: prints RESULT={...}
pytest -q                       # unit tests, incl. the 7 benchmark questions (tests/test_engine.py)
python eval.py                  # benchmark score -> EVAL.md
```

## Demo datasets (synthetic, made by us)
- `data/nimbus_retail`: 300 orders over Jan-Jun 2024 plus two customer tables and EUR to USD rates. Planted traps: 25 duplicate orders, EUR orders from March, no February rate, ambiguous dates like 03/04/2024, blank amounts in June, customer C17's region differs between tables. Rebuild with `python scripts/make_demo_data.py`.
- `data/canteen`: 50 campus canteen sales and 4 stalls (2 duplicates, 1 blank amount).
- `data/example`: the 7-order trap set used by the tests and `data/benchmark.csv`.

## Sample input / output
Dataset `data/example` (orders, customers_billing, customers_crm, fx_rates).

| Question | ProofPilot says |
|---|---|
| What was revenue from USD orders in January 2024? | **$2,000.00**. Duplicate order 1002 counted once. Proof: `proofs/q_1.py` |
| Total revenue in March 2024 in USD? | **$1,788.00 if dates are DD/MM, $2,814.00 if MM/DD**. Order 1003's date 03/02/2024 is ambiguous; EUR converted with the March rate. |
| Revenue from North-region customers in January 2024 (USD)? | **$1,200.00** |
| What was total Q1 2024 revenue in USD? | **Refused**: amount is blank for order 1004, which is inside the question's scope. |
| Revenue from North-region customers in March 2024 (USD)? | **Refused**: customer C3 is North in customers_billing but South in customers_crm. |
| Which month had the highest profit? | **Refused**: there is no profit, cost or margin column. |
| Why did revenue drop in February? | **Refused**: a "why" question needs causes, and the data only shows what happened. |

## Scope note
**Built (MVP):** CSV/XLSX folders; totals, counts and averages filtered by month, quarter, year, currency and any customer attribute (e.g. region); six trap detectors; currency conversion with monthly rates; conditional answers for ambiguous dates; refusals for blanks in scope, contradictions, missing rates, missing concepts and "why" questions; proof export, fresh-process re-run and `verify_all.py`; cloud, local and replay AI modes.
**Not yet (stretch):** group-by/ranking questions ("which month had the highest revenue"), joins beyond one fact table plus lookup tables, charts, scanned PDFs (only real tables inside PDFs/Word files are read).

## Declared resources
- **APIs/models:** Google Gemini API (free tier, `gemini-flash-latest`); Ollama `qwen2.5-coder:7b` (Apache-2.0, runs locally).
- **Datasets:** all data in `data/` is synthetic, made by our team for this event. No external or hidden test data is used.
- **AI coding tools used to build it:** Claude Code, Google AntiGravity, ChatGPT/Codex. The team reviewed and can explain all code.

## Team
- Daniel: lead, engine (planner, proof template, executor, verifier, LLM client)
- Ajay: Streamlit UI (`app.py`), demo laptop
- Aaron: Trap Radar detectors (`profiler_checks.py`), evaluation (`eval.py`)
- Gladys: datasets, gold answers, testing, deck
