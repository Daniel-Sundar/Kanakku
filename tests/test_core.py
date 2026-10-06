"""Daniel's tests for loader, profiler, mock engine and proofs."""
import subprocess
import sys

import engine_mock
from profiler import detect_contradictions, detect_missing_months

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_loader_reads_all_tables(example):
    assert set(example) == {"orders", "fx_rates", "customers_billing", "customers_crm"}
    assert example["orders"]["amount"].dtype.kind == "f"
    assert example["orders"]["order_date"].iloc[3] == "03/02/2024"


def test_missing_month(example):
    flags = detect_missing_months(example["fx_rates"], "fx_rates")
    assert len(flags) == 1 and "2024-02" in flags[0]["message"]


def test_contradiction(example):
    flags = detect_contradictions(example)
    assert len(flags) == 1 and "C3" in flags[0]["message"] and flags[0]["column"] == "region"


def test_mock_contract(example):
    keys = {"status", "answer", "value", "unit", "assumptions", "code", "proof_path",
            "rerun_match", "reason", "needed", "llm_mode", "seconds"}
    for q, status in [("January USD revenue?", "answered"), ("Q1 revenue?", "abstained"),
                      ("force an error", "error"), ("March revenue?", "answered")]:
        r = engine_mock.run_question(q, example, [])
        assert set(r) == keys and r["status"] == status


def test_verify_all_passes():
    out = subprocess.run([sys.executable, "verify_all.py"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
