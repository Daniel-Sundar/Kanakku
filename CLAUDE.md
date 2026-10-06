# ProofPilot (HackNex 2026, HNX26PSI08 Proof-Carrying Data Analyst)

An AI data analyst for messy multi-table data. Every number it returns comes with a standalone Python proof script that re-computes it. When the data can't support an answer, it refuses and gives a specific reason.

Planning docs live in `docs/plan/` (kept local, git-ignored so rivals cannot read our strategy in the public repo; read only when needed): `PSI08_Mentor_Guide.md` (requirements, worked examples, refusal rules), `HackNex_Team_Plan_v2_Tools.md` (tickets, contracts), `ProofPilot_Task_Handout.md`.
Tiny trap dataset: `data/example/`; proofs with known outputs in `proofs/example/` (2000.0; 1788.0 / 2814.0). Benchmark: `data/benchmark.csv`.

## File ownership (enforced by `tools/check_owner.py`, see OWNERS.md)
- Daniel: everything not listed below. A: `app.py` only. B: `profiler_checks.py`, `eval.py`, `EVAL.md`, `README.md`.
- When working for Daniel you may edit any file, but don't rewrite A's or B's files unless Daniel asks.

## Hard rules (from the booklet)
- Every number in an answer must have re-runnable code. The verifier runs it and must get the same number, or the score is 0.
- A wrong answer given confidently scores worse than "I can't determine this" with a good reason.
- The repo is public. The README must cover: what it is, the tech, install, run, reproduce, a scope note, sample input/output, and declared APIs/models/datasets.

## Stack
- Python 3.11, pandas, numpy, Streamlit, pytest. No database, no other frameworks.
- `LLM_MODE` env var: `cloud` | `local` (Ollama `qwen2.5-coder:7b`) | `replay` (cached real runs in `replay_cache/`). If the first choice fails, fall back automatically to the next.
- Laptops: RTX 5050 8GB and GTX 1660 Ti 6GB, both with 16GB RAM. Never use a model bigger than 7B.

## Module contracts (frozen: don't change signatures without asking)
```python
# loader.py
load_folder(path: str) -> dict[str, pd.DataFrame]
# profiler_checks.py: each returns list[Flag]
detect_duplicates(df, table); detect_missing(df, table)
detect_mixed_currency(df, table); detect_ambiguous_dates(df, table)
Flag = {"table", "column", "trap", "severity": "high|medium|low", "count", "example_rows", "message"}
# profiler.py
profile_all(tables) -> list[Flag]
# engine.py (engine_mock.py has the same signatures, with canned data)
run_question(question, tables, flags) -> Result
rerun_proof(proof_path) -> {"value", "match"}
Result = {"status": "answered|abstained|error", "answer", "value", "unit", "assumptions",
          "code", "proof_path", "rerun_match", "reason", "needed", "llm_mode", "seconds"}
```

## How the engine must work
1. Before any question, the profiler flags traps: duplicates, blanks, mixed currency, ambiguous dates, missing FX months, and tables that disagree.
2. The LLM writes a JSON plan plus pandas code. The code runs in a subprocess with a timeout. An AST check allows only pandas, numpy, json, math, datetime and pathlib imports.
3. The proof is saved as `proofs/q_<n>.py`. It reads the CSVs by relative path and prints one line, `RESULT=<json>`.
4. The proof is re-run in a fresh process. The values must match (rounded to 2 decimals). Reject any proof that doesn't read the data, for example one that only prints a literal.
5. Abstain gate: refuse when a flag touches the rows or columns the answer needs and can't be fixed by a stated rule. Also refuse when a concept has no column (such as profit) or the question asks "why". When there are 2 plausible readings, prove both and answer conditionally.
6. The number in the answer text is always copied from `RESULT`. The LLM never types it.

## Commands
- Run the app: `streamlit run app.py`
- Tests: `pytest -q`
- Verify all proofs: `python verify_all.py`
- Benchmark: `python eval.py` (writes `EVAL.md`)

## Working style
- Small steps. After every change, run `pytest -q`. Don't commit red tests.
- Commit messages start with the ticket ID, e.g. `[D6] planner + executor`.
- Never invent gold answers. They come from C's BENCHMARK sheet (`data/benchmark.csv`).
