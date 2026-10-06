"""Fake engine with the SAME functions as engine.py, returning canned answers.  Owner: Daniel.
A builds the screen against this until the real engine is ready. Never call an AI from here."""
import time

Q1_PROOF = "proofs/example/q1_jan_usd_revenue.py"
Q2_PROOF = "proofs/example/q2_march_revenue_usd_both_readings.py"


def _result(**kw):
    base = {"status": "answered", "answer": "", "value": None, "unit": "", "assumptions": [],
            "code": "", "proof_path": "", "rerun_match": False, "reason": "", "needed": "",
            "llm_mode": "replay", "seconds": 0.0}
    base.update(kw)
    return base


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return "# proof file not found"


def run_question(question: str, tables: dict, flags: list) -> dict:
    t = time.time()
    q = question.lower()
    if "why" in q or "profit" in q or "q1" in q or "quarter" in q:
        r = _result(status="abstained",
                    answer="I can't determine this reliably.",
                    reason="Order 1004 has no amount, and there is no EUR to USD rate for February.",
                    needed="The amount for order 1004 and the February EUR rate.")
    elif "march" in q:
        r = _result(answer="$1,788.00 if dates are DD/MM, $2,814.00 if MM/DD.",
                    value={"if_DD/MM": 1788.0, "if_MM/DD": 2814.0}, unit="USD",
                    assumptions=["Duplicate order 1002 counted once",
                                 "Order 1003 (03/02/2024) is ambiguous, so both readings are shown"],
                    code=_read(Q2_PROOF), proof_path=Q2_PROOF, rerun_match=True)
    elif "error" in q:
        r = _result(status="error", reason="The generated code crashed twice (mock error).")
    else:
        r = _result(answer="$2,000.00", value=2000.0, unit="USD",
                    assumptions=["Duplicate order 1002 counted once"],
                    code=_read(Q1_PROOF), proof_path=Q1_PROOF, rerun_match=True)
    r["seconds"] = round(time.time() - t + 1.2, 2)
    return r


def rerun_proof(proof_path: str) -> dict:
    values = {Q1_PROOF: 2000.0, Q2_PROOF: {"if_DD/MM": 1788.0, "if_MM/DD": 2814.0}}
    return {"value": values.get(proof_path), "match": proof_path in values}
