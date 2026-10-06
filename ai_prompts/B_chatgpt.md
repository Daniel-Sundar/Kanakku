# B: prompts for ChatGPT Go

ChatGPT can't see the repo, so you copy code in and out. Copy back only the function it wrote. Never paste a whole new file over an existing one.

## 1. Paste this ONCE at the start of every new chat
```
You are helping me (teammate B) on a hackathon project in Python + pandas.
STRICT RULES:
- I will give you ONE function at a time, with its docstring and its tests.
- Return ONLY that one function, complete, with the SAME name and arguments. Don't rename anything.
- Don't write other functions, imports or files, and don't change make_flag().
- Use only pandas and the Python standard library.
- Keep it short (under 30 lines) with a comment on each step so I can explain it to judges.
- After the code, explain each line in one simple sentence.
Reply "OK" if you understand.
```

## 2. Task prompt (one per function, ticket B3)
```
Fill in this function. It must make these tests pass.

<paste the whole function from profiler_checks.py, including its docstring>

Tests:
<paste only the tests for this function from tests/test_profiler_checks.py>

Note: the table is loaded from this CSV (row numbers start at 0):
<paste data/example/orders.csv>
```
Then replace ONLY the `# TODO (B3)` + `return []` lines of that function with the new body, save, and run:
```bash
pytest tests/test_profiler_checks.py -q
```

## 3. When a test fails
```
The test failed. Here is the exact error:
<paste the pytest output>
Here is my current function:
<paste it>
Fix ONLY this function. Same name and arguments.
```
Tried twice and still red, or stuck for 20 minutes? Post `[B3] BLOCKED: <test name>` in the team chat.

## 4. Other tickets
- **B4 (eval.py):** same pattern. Give ChatGPT the `judge()` function with its docstring, then `write_report()`. Run `python eval.py`.
- **B5 (README.md):** paste the README and say: "Fill every TODO using these facts: <paste from the HQ doc>. Keep the headings exactly the same. Return the whole README."
- You may edit ONLY: `profiler_checks.py`, `eval.py`, `EVAL.md`, `README.md`.
