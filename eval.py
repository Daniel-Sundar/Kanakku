"""Score ProofPilot on the benchmark.  Owner: B.
Usage:  python eval.py            -> prints a table and writes EVAL.md

Reads data/benchmark.csv (C's questions). For each row it asks the engine,
then decides PASS / FAIL. Fill in the 2 TODOs. Don't change the other parts.
"""
import time

import pandas as pd

from engine import run_question
from loader import load_folder
from profiler import profile_all


def judge(row, result) -> str:
    """Return "PASS" or "FAIL" for one benchmark row.

    Rules:
      expected_behaviour == "answer"      -> PASS if status is "answered" and value equals gold_value (2 decimals)
      expected_behaviour == "conditional" -> PASS if status is "answered" and both numbers in gold_value
                                             (written "1788.00|2814.00") are in the result's value
      expected_behaviour == "refuse"      -> PASS if status is "abstained"
    """
    # TODO (B4)
    return "FAIL"


def write_report(rows: list[dict]) -> None:
    """Write EVAL.md: a Markdown table (id, question, expected, got, verdict, seconds)
    and a summary line like "Score: 6/7 · correct refusals: 4/4 · answers: 2/3"."""
    # TODO (B4)
    pass


def main():
    bench = pd.read_csv("data/benchmark.csv", dtype=str).fillna("")
    cache = {}
    rows = []
    for _, row in bench.iterrows():
        if row["dataset"] not in cache:
            tables = load_folder(f"data/{row['dataset']}")
            cache[row["dataset"]] = (tables, profile_all(tables))
        tables, flags = cache[row["dataset"]]
        t = time.time()
        result = run_question(row["question"], tables, flags)
        verdict = judge(row, result)
        rows.append({"id": row["id"], "question": row["question"], "expected": row["expected_behaviour"],
                     "got": result["status"], "value": result["value"], "verdict": verdict,
                     "seconds": round(time.time() - t, 2)})
        print(f"{verdict:4}  {row['id']:5} {row['question']}")
    write_report(rows)


if __name__ == "__main__":
    main()
