# Rules for any AI coding assistant working in this repo

1. Ask the person which teammate they are (A, B or Daniel) if you don't know.
2. Edit ONLY that person's files (see OWNERS.md):
   - A: `app.py`
   - B: `profiler_checks.py`, `eval.py`, `EVAL.md`, `README.md`
   - Daniel: everything else
3. Never rename, delete, move or create files outside that list. Never edit `tests/`, `engine*.py`, `loader.py`, `profiler.py`, `tools/` or `.github/` unless the person is Daniel.
4. Never change a function's name or arguments. The contracts in CLAUDE.md are frozen.
5. If the task needs a change in someone else's file, STOP and say: "This needs <change> in <file>, owned by <owner>. Ask them in the team chat."
6. Use only pandas, numpy, streamlit and the Python standard library. Don't add packages.
7. After changing code, tell the person which command to run to check it (`pytest -q` or `streamlit run app.py`).
A git hook blocks commits that break rule 2, so following these rules saves time.
