# Team setup: GitHub + rules (read once)

## Daniel: put the repo on GitHub (one time, about 15 minutes)
1. On github.com click **New repository**, name it `proofpilot`, choose **Public** (the booklet requires it), and don't add a README.
2. On your laptop, inside this folder:
   ```bash
   git init -b main
   git add . && git commit -m "[D3] starter pack"
   git remote add origin https://github.com/<you>/proofpilot.git
   git push -u origin main
   bash tools/install_hook.sh daniel
   ```
3. **Settings → Collaborators → Add people**: add A and B. C doesn't need access.
4. **Settings → Branches → Add branch ruleset** (or "branch protection rule") for `main`:
   - ✅ Require a pull request before merging (approvals: 0 is fine, you merge)
   - ✅ Require status checks to pass → pick **ownership** (it appears after the first pull request runs)
   - Don't make **tests** required: B's tests are red on purpose until B finishes.
5. Paste each teammate their message: `ai_prompts/A_antigravity.md` to A, `ai_prompts/B_chatgpt.md` to B, `ai_prompts/C_no_code.md` to C.

## A and B: first time
```bash
git clone https://github.com/<daniel>/proofpilot.git
cd proofpilot
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
bash tools/install_hook.sh a        # B types: b
git checkout -b a/work              # B types: b/work   (your branch must start with your letter)
streamlit run app.py                # A: you should see the app with fake answers
pytest tests/test_profiler_checks.py -q   # B: 5 tests fail, which is expected
```

## A and B: every time you finish a piece
```bash
git add <your file>                 # e.g. git add app.py   (never "git add ." )
git commit -m "[A3] health cards"   # the hook blocks it if you touched someone else's file
git push -u origin a/work
```
Then on GitHub click **Compare & pull request → Create**. Post `[A3] PR ready` in the chat, and Daniel merges it.
To get everyone else's latest work: `git pull origin main`.

## The 3 locks that protect each person's work
1. **AI rules:** each person's AI prompt (in `ai_prompts/`) and `AGENTS.md` tell the AI to edit only that person's files.
2. **Git hook on your laptop:** `git commit` is refused if you changed a file you don't own.
3. **GitHub check:** every pull request runs the same check, so it can't be merged into `main` if it touches someone else's file. Only Daniel merges.
