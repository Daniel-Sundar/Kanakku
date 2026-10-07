"""Run proof code safely.  Owner: Daniel.

check_code(code)  -> list of problems (empty = safe)   AST allowlist, no exec/eval/os/network
run_file(path)    -> {"ok", "result", "stdout", "error"}   fresh subprocess + timeout, parses RESULT=
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALLOWED_IMPORTS = {"pandas", "numpy", "json", "math", "datetime", "pathlib", "re", "hashlib"}
BANNED_CALLS = {"exec", "eval", "compile", "__import__", "open", "input", "globals", "locals"}


def check_code(code: str) -> list[str]:
    """Static safety check. Returns a list of problems; an empty list means the code may run."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error: {e}"]
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[0]]
        else:
            names = []
        problems += [f"import not allowed: {n}" for n in names if n not in ALLOWED_IMPORTS]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            problems.append(f"call not allowed: {node.func.id}()")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr != "__file__":
            problems.append(f"dunder access not allowed: {node.attr}")
    return problems


def parse_result(stdout: str):
    """Return the JSON after the last RESULT= line, or None."""
    lines = [l for l in stdout.splitlines() if l.startswith("RESULT=")]
    return json.loads(lines[-1][len("RESULT="):]) if lines else None


def run_file(path, timeout: int = 20) -> dict:
    """Run a proof file in a brand-new Python process from the repo root."""
    try:
        out = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                             timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "result": None, "stdout": "", "error": f"timed out after {timeout}s"}
    try:
        result = parse_result(out.stdout)
    except json.JSONDecodeError as e:
        return {"ok": False, "result": None, "stdout": out.stdout, "error": f"bad RESULT json: {e}"}
    if out.returncode != 0 or result is None:
        err = out.stderr.strip().splitlines()
        return {"ok": False, "result": None, "stdout": out.stdout,
                "error": err[-1] if err else "no RESULT= line printed"}
    return {"ok": True, "result": result, "stdout": out.stdout, "error": ""}
