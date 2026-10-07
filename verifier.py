"""Check proofs and decide when to refuse.  Owner: Daniel."""
import ast
import json
import re
from pathlib import Path

import executor

ROOT = Path(__file__).resolve().parent
EXPECTED = ROOT / "proofs" / "expected.json"
WHY = re.compile(r"^\s*why\b|\bwhy (did|do|does|is|are|was|were)\b|\breason\b|\bcaused?\b", re.I)


def is_literal_proof(code: str) -> bool:
    """True when the script never reads a data file (it could only be printing a typed-in number)."""
    tree = ast.parse(code)
    reads = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in ("read_csv", "read_excel")]
    return not reads


def asks_why(question: str) -> bool:
    return bool(WHY.search(question))


def _rounded(v):
    if isinstance(v, dict):
        return {k: _rounded(x) for k, x in sorted(v.items())}
    return round(float(v), 2) if isinstance(v, (int, float)) else v


def same(a, b) -> bool:
    return json.dumps(_rounded(a), sort_keys=True) == json.dumps(_rounded(b), sort_keys=True)


def remember(proof_path: str, result: dict):
    """Store the answer so verify_all.py and the Re-run button can check the proof later."""
    data = json.loads(EXPECTED.read_text()) if EXPECTED.exists() else {}
    data[proof_path] = result.get("value") if "value" in result else {"abstain": result.get("abstain")}
    EXPECTED.write_text(json.dumps(data, indent=2) + "\n")


def rerun(proof_path: str) -> dict:
    """Fresh-process re-run. Returns {"value", "match"}."""
    expected = json.loads(EXPECTED.read_text()).get(proof_path) if EXPECTED.exists() else None
    out = executor.run_file(ROOT / proof_path)
    if not out["ok"]:
        return {"value": None, "match": False, "error": out["error"]}
    got = out["result"]
    value = got.get("value") if "value" in got else {"abstain": got.get("abstain")}
    if isinstance(value, dict) and all(isinstance(x, dict) and "value" in x for x in value.values()):
        value = {k: x["value"] for k, x in value.items()}   # older two-reading format
    if isinstance(got, dict) and "value" not in got and "abstain" not in got:
        value = {k: x["value"] for k, x in got.items() if isinstance(x, dict) and "value" in x}
    return {"value": value, "match": expected is not None and same(value, expected)}
