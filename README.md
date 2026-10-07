# ProofPilot

### Numbers you can check, not just trust.

> **HackNex 2026 · HNX26PSI08 Proof-Carrying Data Analyst**
> Team: Daniel · Ajay · Aaron · Gladys

Every AI analyst gives you an answer. **ProofPilot gives you the answer and the receipt.**

Ask a plain-English question about messy business spreadsheets. ProofPilot returns the number **plus a standalone Python script that re-computes it from the raw files**. Run the script yourself, on any laptop, and you get the same number. If the data can't honestly support an answer, ProofPilot **refuses, names the exact rows that break it, and tells you what it needs**.

> "Boss, idhu kanakku-la varala." *(Boss, this doesn't add up.)* That's what a good accountant says before signing off on a bad total. ProofPilot says it too.

---

## Why it matters

Real company data is messy. The same order is entered twice, dollars sit next to euros, `03/02/2024` could mean 3 February or 2 March, and the CRM and the billing system disagree about a customer's region. A normal chatbot adds it all up and hands you a confident, wrong number.

ProofPilot is built on three promises:

| Promise | How it's kept |
|---|---|
| **Every number is provable** | Each answer ships with `proofs/q_<n>.py`. The script reads the CSVs itself and prints one `RESULT=` line, which is re-run in a fresh process and must match. |
| **The AI never types a number** | The AI only writes a small JSON plan. The arithmetic is done by audited proof code, and the answer text is copied from the proof's output. |
| **It refuses rather than guesses** | Blank values in scope, missing exchange rates, conflicting tables, concepts with no column (profit with no cost data), and "why" questions get a clear refusal with the reason and the fix. |

---

## How it works

```
 Your files ─▶ Trap Radar ─▶ AI plan (JSON) ─▶ Proof script ─▶ Run ─▶ Re-run ─▶ Answer or refuse
               (no AI yet)   (Gemini / Qwen    (safety-checked)   (fresh     (must     (number copied
                              / rule parser)                      process)   match)     from RESULT)
```

1. **Load.** Pick a demo dataset, or upload your own CSV, Excel, PDF or Word files. Tables inside PDF and Word files are extracted to CSV so proofs can re-read them.
2. **Trap Radar.** Before any AI runs, deterministic checks flag six traps: duplicate rows, blank values, mixed currencies, ambiguous dates, missing exchange-rate months, and tables that contradict each other.
3. **Plan.** The AI (Google Gemini in the cloud, or `qwen2.5-coder:7b` running offline through Ollama) turns the question into a JSON plan: period, currency, filters, and sum, count, average or list. If no AI is reachable, a rule parser builds the same plan, so the app never goes dark.
4. **Prove.** The plan is filled into a proof template that handles every trap with a stated rule. An AST check allows only pandas, numpy, json, math, datetime, pathlib and re, and blocks `exec`, `eval` and `open`.
5. **Verify.** The proof runs in a sandboxed subprocess with a timeout, then again in a second fresh process. Both must agree to two decimals. A proof that never reads the data, for example one that only prints a constant, is rejected. A data fingerprint means any edit to the CSVs is caught on re-run.
6. **Answer, branch or refuse.**
   - Safe-to-fix traps are fixed and stated as assumptions: duplicates counted once, currencies converted at that month's rate.
   - When there are two plausible readings, such as DD/MM vs MM/DD, both are proven and the answer is conditional.
   - Anything unfixable is refused, naming the rows and what's missing.

---

## What you can ask

| Kind | Example |
|---|---|
| Totals, counts, averages | "Total USD revenue in March 2024", "How many orders in February?", "Average order value in May 2026" |
| Any period | months, "January to March", Q1–Q4, H1/H2, a whole year, "the 5th month", exact dates "2024-01-02 to 2024-02-06", and no year at all (filled in from the data, and said so) |
| Filters | region, city, state, a customer or shop by ID ("customer C5") or name ("Aroma Traders") |
| Currency | "in USD" converts at each month's rate, while "USD orders" keeps USD rows only |
| Lists and lookups | "List the dealers in Coimbatore", "How many buyers in Kerala?", "Which state is Aroma Traders in?" |
| Honest refusals | "What's the profit?" with no cost column, "Why did sales drop?", rankings, and names not in the data |

---

## Sample input / output

Dataset `data/example` (orders, customers_billing, customers_crm, fx_rates):

| Question | ProofPilot says |
|---|---|
| What was revenue from USD orders in January 2024? | **$2,000.00**. Duplicate order 1002 counted once. Proof: `proofs/example/q1_jan_usd_revenue.py` |
| Total revenue in March 2024 in USD? | **$1,788.00 if dates are DD/MM, $2,814.00 if MM/DD**. Order 1003's date `03/02/2024` is ambiguous, so both are proven. EUR is converted at the March rate. |
| Revenue from North-region customers in January 2024 (USD)? | **$1,200.00** |
| What was total Q1 2024 revenue in USD? | **Refused**: amount is blank for order 1004, inside the question's scope. *Needed:* the amount for order 1004. |
| Revenue from North-region customers in March 2024 (USD)? | **Refused**: customer C3 is North in customers_billing but South in customers_crm. |
| Which month had the highest profit? | **Refused**: there is no profit, cost or margin column. |
| Why did revenue drop in February? | **Refused**: data shows *what* changed, not *why*. |

A proof script's output looks like this:
```text
$ python proofs/example/q1_jan_usd_revenue.py
RESULT={"value": 2000.0, "unit": "USD", "rows_used": [1001, 1002]}
```

---

## Install

```bash
git clone https://github.com/Daniel-Sundar/ProofPilot.git
cd ProofPilot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Optional AI backends:
- **Cloud:** put `GEMINI_API_KEY=...` in a `.env` file, which is git-ignored and must never be committed.
- **Offline:** install [Ollama](https://ollama.com), then run `ollama pull qwen2.5-coder:7b`. It fits a 6–8 GB laptop GPU.

## Run

```bash
streamlit run app.py                    # best available AI, falls back automatically
LLM_MODE=local streamlit run app.py     # offline AI (Ollama, Qwen 7B)
LLM_MODE=rules streamlit run app.py     # no AI at all, rule planner only
```
`LLM_MODE` can be `cloud`, `local`, `replay` (cached real AI replies in `replay_cache/`, for fully offline demos) or `rules`. If the first choice fails, the next one is used automatically.

## Reproduce our numbers

```bash
python verify_all.py                              # re-run every saved proof in a fresh process
python proofs/example/q1_jan_usd_revenue.py       # run any single proof yourself
LLM_MODE=rules python -m pytest -q                # 119 tests, incl. an 87-case judge suite with independent oracles
python eval.py                                    # benchmark score -> EVAL.md
```
The judge suite (`tests/test_judge_suite.py`) checks every answer against a separate pandas calculation written independently of the engine, and checks that every trap question is refused.

---

## Demo datasets (synthetic, made by our team)

| Folder | What's in it | Planted traps |
|---|---|---|
| `data/nimbus_retail` | 300 orders, Jan–Jun 2024, two customer tables, EUR→USD rates | 25 duplicates, EUR from March, no February rate, ambiguous dates, blank June amounts, customer C17's region conflicts |
| `data/canteen` | 50 campus canteen sales, 4 stalls | 2 duplicates, 1 blank amount |
| `data/example` | the 7-order trap set used by tests and `data/benchmark.csv` | every trap type in miniature |

Rebuild them with `python scripts/make_demo_data.py`.

## Scope note

**Built:**
- Inputs: CSV, XLSX, and tables inside PDF and Word files.
- Questions: totals, counts, averages and lists, filtered by any period, currency, attribute, ID or name.
- Trap handling: six trap detectors, monthly FX conversion, and conditional answers for ambiguous dates.
- Refusals with reasons and fixes.
- Proof export, fresh-process re-run, data fingerprinting and `verify_all.py`.
- Cloud, local, replay and rule planners with automatic fallback.
- A multipage Streamlit app (Home, Datasets, Ask, History, Settings, Help) with light and dark themes.

**Deliberately not done:**
- Rankings and comparisons are refused today. Users ask for each number separately, so each one stays provable.
- No causal ("why") answers.
- No charts.
- No scanned-image PDFs.

## Declared resources

- **APIs and models:** Google Gemini API (free tier, `gemini-flash-latest`); Ollama `qwen2.5-coder:7b` (Apache-2.0, runs locally). The app also runs with no model at all.
- **Datasets:** all data in `data/` is synthetic, created by our team for this event. No external or hidden test data is used.
- **Libraries:** pandas, numpy, Streamlit, pytest, requests, openpyxl, pdfplumber, python-docx.
- **AI coding tools used to build it:** Claude Code, Google AntiGravity, ChatGPT/Codex. The team reviewed and can explain all code.

## Team

| Member | Role |
|---|---|
| **Daniel** | Lead; engine (planner, proof template, executor, verifier, LLM client) |
| **Ajay** | Streamlit UI (`app.py`), demo laptop |
| **Aaron** | Trap Radar detectors (`profiler_checks.py`), evaluation (`eval.py`) |
| **Gladys** | Datasets, gold answers, testing, pitch deck |

---

<p align="center"><b>ProofPilot</b>: every answer comes with its proof.</p>
