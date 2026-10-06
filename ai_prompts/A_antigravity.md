# A: prompts for AntiGravity

## 1. Paste this ONCE at the start of every new AntiGravity chat
```
You are helping me (teammate A) on ProofPilot, a Streamlit app for a hackathon.
STRICT RULES:
- You may edit ONLY the file app.py. Do not create, edit, rename or delete any other file.
- Do not touch tests/, engine.py, engine_mock.py, loader.py, profiler.py, profiler_checks.py, tools/ or .github/.
- Do not change how app.py imports or calls these functions:
    load_folder(path) -> dict of DataFrames
    profile_all(tables) -> list of flags, each {table, column, trap, severity, count, example_rows, message}
    run_question(question, tables, flags) -> result {status: answered|abstained|error, answer, value, unit,
        assumptions, code, proof_path, rerun_match, reason, needed, llm_mode, seconds}
    rerun_proof(proof_path) -> {value, match}
- Use plain Streamlit only. No new packages.
- If something needs a change outside app.py, STOP and tell me: "Ask Daniel to change <X> in <file>".
- Make small changes, then tell me to run: streamlit run app.py
Reply "OK, app.py only" if you understand.
```

## 2. Task prompts (one at a time, after the rules above)
**A3: Data Health cards**
```
In app.py, replace the "⚠ message" lines in the Data Health section with cards:
one st.container(border=True) per flag, showing an icon, the message in bold, and the trap name
and count in small text. Show them in 2 columns. Use red for severity "high", orange for "medium",
grey for "low". Keep everything else in app.py the same.
```
**A4: Result cards**
```
In app.py, in the result section, show:
- status "answered": a green box (st.success) with the answer in big text, the assumptions as bullets,
  st.code(result["code"]) inside an expander called "Proof code", a "Re-run proof" button that calls
  rerun_proof(result["proof_path"]) and shows "✔ matched" or "✖ did not match", and an
  st.download_button that downloads the proof file.
- status "abstained": a red box (st.error) with "I can't determine this reliably", then "Why:" reason
  and "What I'd need:" needed.
- status "error": a grey box (st.info) with the reason.
- At the top right, a small badge showing result["llm_mode"] (cloud / local / replay) and result["seconds"].
Only edit app.py.
```

## 3. If AntiGravity edits another file by mistake
```bash
git status                      # see what changed
git restore <wrong-file>        # throw away the change to that file
```
Then tell it: "You edited <file>. Undo that. Only app.py is allowed."
