"""The real engine.  Owner: Daniel.

Everyone else imports from here:   from engine import run_question, rerun_proof
ENGINE=mock gives engine_mock's canned answers instead (for UI work without data or AI).

run_question: refusal gates -> JSON plan (AI, else rules) -> proof script -> safety check
              -> run in a fresh process -> re-run again -> answer text copied from RESULT
"""
import os
import time
from pathlib import Path

if os.getenv("ENGINE", "real") == "mock":
    from engine_mock import rerun_proof, run_question  # noqa: F401
else:
    import executor
    import planner
    import verifier

    ROOT = Path(__file__).resolve().parent
    PROOFS = ROOT / "proofs"

    def _result(**kw):
        base = {"status": "answered", "answer": "", "value": None, "unit": "", "assumptions": [],
                "code": "", "proof_path": "", "rerun_match": False, "reason": "", "needed": "",
                "llm_mode": "rules", "seconds": 0.0}
        base.update(kw)
        return base

    def _money(v, unit):
        if isinstance(v, int) or unit == "rows":
            return f"{v:,}"
        sym = {"USD": "$", "EUR": "€", "INR": "₹"}.get(unit, "")
        return f"{sym}{v:,.2f}" + ("" if sym or not unit else f" {unit}")

    def _data_dir(tables: dict) -> str:
        src = next(iter(tables.values())).attrs.get("source_dir", "data/example")
        p = Path(src).resolve()
        try:
            return p.relative_to(ROOT).as_posix()
        except ValueError:
            return Path(src).as_posix()

    def _next_proof() -> str:
        PROOFS.mkdir(exist_ok=True)
        n = 1 + max([int(p.stem[2:]) for p in PROOFS.glob("q_*.py") if p.stem[2:].isdigit()] or [0])
        return f"proofs/q_{n}.py"

    def run_question(question: str, tables: dict, flags: list) -> dict:
        t0 = time.time()

        def done(**kw):
            return _result(seconds=round(time.time() - t0, 2), **kw)

        if not tables:
            return done(status="error", reason="No tables loaded.")
        s = planner.schema(tables)
        # Gate 1: "why" questions ask for causes; data alone can only show what happened.
        if verifier.asks_why(question):
            return done(status="abstained", answer="I can't determine this reliably.",
                        reason="This asks *why*. The data can show what changed, not what caused it.",
                        needed="Ask what changed instead (e.g. 'revenue by month'), or give data about causes.")
        # Gate 2: a concept with no column behind it.
        miss = planner.missing_concept(question, s)
        if miss:
            return done(status="abstained", answer="I can't determine this reliably.",
                        reason=f"There is no column for {miss[0]} in any table "
                               f"(looked for: {', '.join(miss[1])}).",
                        needed=f"A column with {' or '.join(dict.fromkeys(miss[1]))} for each row.")
        # Gate 3: a name the question depends on that is nowhere in the data (a trick or a typo).
        unknown = planner.unknown_names(question, tables, s)
        if unknown:
            return done(status="abstained", answer="I can't determine this reliably.",
                        reason=f"{', '.join(unknown)} doesn't appear anywhere in the data, so any number would be a guess.",
                        needed="Check the spelling, or use a name that is in the data.")
        # Listing or counting things (buyers, customers, stalls) rather than adding up money.
        lp = planner.lookup_plan(question, tables, s)
        if lp:
            return _run_lookup(question, lp, tables, done)
        if not s["value_col"] or not s["date_col"]:
            return done(status="error", reason="Couldn't find a date column and a numeric amount column.")

        plan, mode = planner.llm_plan(question, s, tables)
        if plan is None:
            plan, mode = planner.rule_plan(question, s), "rules"

        proof_path = _next_proof()
        code = planner.make_proof(question, plan, s, _data_dir(tables), proof_path)
        problems = executor.check_code(code)
        if problems or verifier.is_literal_proof(code):
            return done(status="error", reason="Proof failed the safety check: " + "; ".join(problems or ["reads no data"]),
                        code=code, llm_mode=mode)
        (ROOT / proof_path).write_text(code)

        first = executor.run_file(ROOT / proof_path)
        if not first["ok"]:
            return done(status="error", reason=f"The proof crashed: {first['error']}", code=code,
                        proof_path=proof_path, llm_mode=mode)
        res = first["result"]
        verifier.remember(proof_path, res)
        again = verifier.rerun(proof_path)      # fresh process, must give the same answer

        fp = res.get("data_fingerprint")
        if "abstain" in res:
            return done(status="abstained", answer="I can't determine this reliably.", reason=res["abstain"],
                        needed=res["needed"], code=code, proof_path=proof_path,
                        rerun_match=again["match"], llm_mode=mode)
        if not again["match"]:
            return done(status="error", reason="The proof gave a different number when re-run.", code=code,
                        proof_path=proof_path, llm_mode=mode)

        value, unit = res["value"], res.get("unit", "")
        if isinstance(value, dict):
            parts = [f"{_money(v, unit)} if dates are {k[3:]}" for k, v in value.items()]
            answer = ", ".join(parts) + "."
        else:
            answer = _money(value, unit)
        scope = []
        if plan.get("days"):
            scope.append(f"dates {plan['days'][0]} to {plan['days'][1]} (inclusive)")
        elif plan["months"]:
            scope.append(f"months {plan['months'][0]} to {plan['months'][-1]}" if len(plan["months"]) > 1
                         else f"month {plan['months'][0]}")
        if plan["currency_mode"] == "filter":
            scope.append(f"only {plan['currency']} rows")
        elif plan["currency_mode"] == "convert":
            scope.append(f"other currencies converted to {plan['currency']} with that month's rate")
        scope += [f"{k} = {v}" for k, v in plan["filters"].items()]
        return done(answer=answer, value=value, unit=unit,
                    assumptions=(["Scope: " + ", ".join(scope)] if scope else []) + res.get("assumptions", [])
                    + ([f"Data fingerprint {fp}: re-runs check it, so any edit to the CSVs is caught"] if fp else []),
                    code=code, proof_path=proof_path, rerun_match=True, llm_mode=mode)

    def _run_lookup(question, lp, tables, done):
        proof_path = _next_proof()
        code = planner.make_lookup_proof(question, lp, _data_dir(tables), proof_path)
        problems = executor.check_code(code)
        if problems or verifier.is_literal_proof(code):
            return done(status="error", reason="Proof failed the safety check: " + "; ".join(problems or ["reads no data"]),
                        code=code)
        (ROOT / proof_path).write_text(code)
        first = executor.run_file(ROOT / proof_path)
        if not first["ok"]:
            return done(status="error", reason=f"The proof crashed: {first['error']}", code=code, proof_path=proof_path)
        res = first["result"]
        verifier.remember(proof_path, res)
        again = verifier.rerun(proof_path)
        if "abstain" in res:
            return done(status="abstained", answer="I can't determine this reliably.", reason=res["abstain"],
                        needed=res["needed"], code=code, proof_path=proof_path, rerun_match=again["match"])
        if not again["match"]:
            return done(status="error", reason="The proof gave a different result when re-run.", code=code,
                        proof_path=proof_path)
        v = res["value"]
        where = " and ".join(f"{c} = {x}" for c, x in lp["filters"].items())
        if lp["count"]:
            answer = f"{v} {lp['entity']}" + (f" with {where}" if where else "")
        elif not v:
            answer = f"No {lp['entity']}" + (f" with {where}" if where else "") + "."
        else:
            answer = f"{len(v)} {lp['entity']}" + (f" with {where}" if where else "") + ": " + ", ".join(v)
        fp = res.get("data_fingerprint")
        return done(answer=answer, value=v, unit=res["unit"], code=code, proof_path=proof_path, rerun_match=True,
                    assumptions=["Scope: " + ", ".join(res.get("assumptions", []))]
                    + ([f"Data fingerprint {fp}: re-runs check it, so any edit to the CSVs is caught"] if fp else []))

    def rerun_proof(proof_path: str) -> dict:
        out = verifier.rerun(proof_path)
        return {"value": out["value"], "match": out["match"]}
