"""The real engine.  Owner: Daniel.

Everyone else imports from here:   from engine import run_question, rerun_proof
While ENGINE=mock (the default), this hands back engine_mock's canned answers,
so the app works before the real engine exists. Set ENGINE=real to use the real one.
"""
import os

if os.getenv("ENGINE", "mock") == "mock":
    from engine_mock import rerun_proof, run_question  # noqa: F401
else:
    def run_question(question: str, tables: dict, flags: list) -> dict:
        # TODO (D6/D7): planner -> executor -> save proof -> fresh re-run -> abstain gate
        raise NotImplementedError("Real engine not built yet (ticket D6)")

    def rerun_proof(proof_path: str) -> dict:
        # TODO (D7): run the proof in a fresh process, parse RESULT=, compare
        raise NotImplementedError("Real engine not built yet (ticket D7)")
