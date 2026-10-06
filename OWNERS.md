# Who owns which file

Only edit the files you own. If you need a change in someone else's file, post in the team chat: `[ticket] NEED: <what> in <file>`.

| Owner | Files |
|---|---|
| **Daniel** (lead) | `loader.py`, `profiler.py`, `engine.py`, `engine_mock.py`, `llm_client.py`, `planner.py`, `executor.py`, `verifier.py`, `verify_all.py`, `tests/`, `tools/`, `.github/`, `CLAUDE.md`, `OWNERS.md`, `requirements.txt`, `replay_cache/`, `proofs/` |
| **A** (UI) | `app.py`, `assets/` |
| **B** (checks, eval, docs) | `profiler_checks.py`, `eval.py`, `EVAL.md`, `README.md` |
| **C** (data, no code) | Google Sheet only. Daniel exports it into `data/nimbus/` and `data/benchmark.csv` |

The contracts in `CLAUDE.md` are frozen. Only Daniel changes a function signature, and he logs it in the HQ doc.
