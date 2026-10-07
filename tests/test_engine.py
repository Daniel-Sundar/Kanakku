"""Real engine on the 7 example questions (no AI needed: LLM_MODE=rules)."""
import csv
import json
import os
from pathlib import Path

import pytest

os.environ["LLM_MODE"] = "rules"
os.environ["ENGINE"] = "real"

import engine  # noqa: E402
import executor  # noqa: E402
import verifier  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BENCH = list(csv.DictReader(open(ROOT / "data" / "benchmark.csv")))


@pytest.fixture(autouse=True)
def keep_proofs_clean():
    before = set((ROOT / "proofs").glob("q_*.py"))
    saved = (ROOT / "proofs" / "expected.json").read_text()
    yield
    for p in set((ROOT / "proofs").glob("q_*.py")) - before:
        p.unlink()
    (ROOT / "proofs" / "expected.json").write_text(saved)


@pytest.mark.parametrize("row", BENCH, ids=[r["id"] for r in BENCH])
def test_benchmark(row, example):
    r = engine.run_question(row["question"], example, [])
    if row["expected_behaviour"] == "refuse":
        assert r["status"] == "abstained" and r["reason"]
    elif row["expected_behaviour"] == "conditional":
        a, b = (float(x) for x in row["gold_value"].split("|"))
        assert r["status"] == "answered" and sorted(r["value"].values()) == [a, b]
    else:
        assert r["status"] == "answered" and r["value"] == float(row["gold_value"])
    if r["proof_path"]:
        assert engine.rerun_proof(r["proof_path"])["match"]


def test_unsafe_code_blocked():
    assert executor.check_code("import os\nos.system('rm -rf /')")
    assert executor.check_code("eval('1+1')")
    assert executor.check_code("import pandas as pd\nprint(1)") == []


def test_literal_proof_rejected():
    assert verifier.is_literal_proof('print("RESULT=" + "{\\"value\\": 2000}")')
    assert not verifier.is_literal_proof("import pandas as pd\npd.read_csv('x.csv')")


def test_timeout(tmp_path):
    f = tmp_path / "loop.py"
    f.write_text("while True:\n    pass\n")
    assert "timed out" in executor.run_file(f, timeout=2)["error"]
