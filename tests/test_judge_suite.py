"""Judge suite: 80+ questions over the three demo datasets, plus safety checks.

Answered numbers are checked against an independent plain-pandas oracle written here
(not against the engine's own output), and every proof is re-run in a fresh process.
Gold values for the tiny example dataset come from data/benchmark.csv.
"""
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

os.environ["LLM_MODE"] = "rules"

import engine  # noqa: E402
import executor  # noqa: E402
import verifier  # noqa: E402
from loader import load_folder  # noqa: E402
from profiler import profile_all  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = {n: load_folder(str(ROOT / "data" / n)) for n in ("example", "nimbus_retail", "canteen")}
FLAGS = {n: profile_all(t) for n, t in DATA.items()}


@pytest.fixture(scope="module", autouse=True)
def _clean_proofs():
    before = set((ROOT / "proofs").glob("q_*.py"))
    exp = ROOT / "proofs" / "expected.json"
    saved = exp.read_text() if exp.exists() else None
    yield
    for p in set((ROOT / "proofs").glob("q_*.py")) - before:
        p.unlink()
    if saved is not None:
        exp.write_text(saved)


def ask(ds, q):
    return engine.run_question(q, DATA[ds], FLAGS[ds])


# ---------- independent oracle (plain pandas, ISO-dated months only) ----------
def nimbus_oracle(month, mode, agg="sum", region=None):
    """Returns ("answered", value) or ("abstained", None) for the clean months Jan, Feb, May."""
    o = pd.read_csv(ROOT / "data/nimbus_retail/orders.csv", dtype=str).drop_duplicates()
    fx = pd.read_csv(ROOT / "data/nimbus_retail/fx_rates.csv", dtype=str)
    o = o[o.order_date.str[:7] == month].copy()
    o["amount"] = pd.to_numeric(o.amount)
    if region:
        b = pd.read_csv(ROOT / "data/nimbus_retail/customers_billing.csv", dtype=str)
        c = pd.read_csv(ROOT / "data/nimbus_retail/customers_crm.csv", dtype=str)
        rb, rc = dict(zip(b.customer_id, b.region)), dict(zip(c.customer_id, c.region))
        if any(rb.get(k) != rc.get(k) and region in (rb.get(k), rc.get(k))
               for k in o.customer_id.unique() if k in rb and k in rc):
            return "abstained", None
        o = o[o.customer_id.map(rb) == region]
    if agg == "count":
        return "answered", len(o)
    if mode == "filter":
        o = o[o.currency == "USD"]
    else:
        rate = fx[fx.month == month].eur_to_usd
        if (o.currency == "EUR").any():
            if rate.empty:
                return "abstained", None
            o.loc[o.currency == "EUR", "amount"] *= float(rate.iloc[0])
    if o.amount.isna().any():
        return "abstained", None
    if len(o) == 0:
        return "answered", 0.0
    return "answered", round(float(o.amount.mean() if agg == "mean" else o.amount.sum()), 2)


def canteen_oracle(agg, stall=None, block=None):
    s = pd.read_csv(ROOT / "data/canteen/sales.csv", dtype=str).drop_duplicates()
    st = pd.read_csv(ROOT / "data/canteen/stalls.csv", dtype=str)
    if stall:
        s = s[s.stall_id.map(dict(zip(st.stall_id, st.stall_name))) == stall]
    if block:
        s = s[s.stall_id.map(dict(zip(st.stall_id, st.block))) == block]
    if agg == "count":
        return "answered", len(s)
    a = pd.to_numeric(s.amount)
    if a.isna().any():
        return "abstained", None
    return "answered", round(float(a.mean() if agg == "mean" else a.sum()), 2)


def check_answer(r, expected_status, expected_value=None):
    assert r["status"] == expected_status, (r["status"], r["answer"], r["reason"])
    if expected_status == "answered":
        assert verifier.same(r["value"], expected_value), (r["value"], expected_value)
        assert r["rerun_match"] is True
        assert engine.rerun_proof(r["proof_path"])["match"] is True
        assert not verifier.is_literal_proof(r["code"])
    if expected_status == "abstained":
        assert r["reason"] and r["needed"]


# ---------- 1. Benchmark gold answers (data/benchmark.csv) : 7 ----------
BENCH = pd.read_csv(ROOT / "data/benchmark.csv", dtype=str).fillna("")


@pytest.mark.parametrize("row", BENCH.to_dict("records"), ids=list(BENCH.id))
def test_benchmark_gold(row):
    r = ask(row["dataset"], row["question"])
    if row["expected_behaviour"] == "refuse":
        assert r["status"] == "abstained", r
    elif row["expected_behaviour"] == "conditional":
        assert isinstance(r["value"], dict)
        assert sorted(round(v, 2) for v in r["value"].values()) == sorted(float(x) for x in row["gold_value"].split("|"))
        assert engine.rerun_proof(r["proof_path"])["match"]
    else:
        check_answer(r, "answered", float(row["gold_value"]))


# ---------- 2. Nimbus clean months vs the oracle : 12 ----------
MONTH_NAMES = {"2024-01": "January 2024", "2024-02": "February 2024", "2024-05": "May 2024"}
NIMBUS_CASES = []
for m, name in MONTH_NAMES.items():
    NIMBUS_CASES += [
        (f"What was revenue from USD orders in {name}?", m, "filter", "sum"),
        (f"Total revenue in {name} in USD", m, "convert", "sum"),
        (f"How many orders were placed in {name}?", m, "none", "count"),
        (f"Average USD order value in {name}", m, "filter", "mean"),
    ]


@pytest.mark.parametrize("q,month,mode,agg", NIMBUS_CASES)
def test_nimbus_clean_months(q, month, mode, agg):
    status, value = nimbus_oracle(month, mode, agg)
    check_answer(ask("nimbus_retail", q), status, value)


# ---------- 3. Nimbus region filters vs the oracle (C17 contradiction) : 12 ----------
REGION_CASES = [(reg, m, name) for m, name in MONTH_NAMES.items() for reg in ("North", "South", "East", "West")]


@pytest.mark.parametrize("region,month,name", REGION_CASES)
def test_nimbus_regions(region, month, name):
    status, value = nimbus_oracle(month, "filter", "sum", region)
    r = ask("nimbus_retail", f"Total USD sales from {region} customers in {name}")
    check_answer(r, status, value)
    if status == "abstained":
        assert "C17" in r["reason"]


# ---------- 4. Ambiguous dates: two readings, both proven : 6 ----------
@pytest.mark.parametrize("q", [
    "Total revenue in March 2024 in USD", "Total revenue in April 2024 in USD",
    "What was revenue from USD orders in March 2024?", "What was revenue from USD orders in April 2024?",
    "How many orders were placed in April 2024?", "Total revenue in Q1 2024 in USD",
])
def test_nimbus_two_readings(q):
    r = ask("nimbus_retail", q)
    assert r["status"] == "answered", r["reason"]
    assert isinstance(r["value"], dict) and set(r["value"]) == {"if_DD/MM", "if_MM/DD"}
    assert "if dates are DD/MM" in r["answer"] and "if dates are MM/DD" in r["answer"]
    assert engine.rerun_proof(r["proof_path"])["match"]


# ---------- 5. Refusals on Nimbus : 22 ----------
@pytest.mark.parametrize("q,why", [
    ("Total revenue in June 2024 in USD", "blank"),
    ("What was revenue from USD orders in June 2024?", "blank"),
    ("Average USD order value in June 2024", "blank"),
    ("Total revenue in H1 2024 in USD", "blank"),
    ("Total revenue in 2019 in USD", "no rows"),
    ("Total revenue in 2023 in USD", "no rows"),
    ("What was revenue from USD orders in December 2024?", "no rows"),
    ("Total revenue in January 2025 in USD", "no rows"),
    ("Total USD sales in Antarctica in January 2024", "Antarctica"),
    ("Total revenue in USD for customer C99 in January 2024", "C99"),
    ("Total USD sales in Mumbai in May 2024", "Mumbai"),
    ("How many orders did Amazon place in January 2024?", "Amazon"),
    ("Total revenue in May 2024", "mix currencies"),
    ("Total revenue in February 2024 in EUR", "rate"),
    ("Which month had the highest profit?", "profit"),
    ("What is the profit margin in March 2024?", "profit"),
    ("Total cost of orders in January 2024", "cost"),
    ("What was the total tax in May 2024?", "tax"),
    ("Why did revenue drop in February?", "why"),
    ("Why was May so strong?", "why"),
    ("What caused the dip in sales in March 2024?", "why"),
    ("What is the reason for low revenue in February 2024?", "why"),
])
def test_nimbus_refusals(q, why):
    r = ask("nimbus_retail", q)
    assert r["status"] == "abstained", (r["answer"], r["value"])
    assert why.lower() in (r["reason"] + r["needed"]).lower(), r["reason"]


# ---------- 6. Canteen (second dataset, different schema) vs the oracle : 14 ----------
@pytest.mark.parametrize("q,agg,stall,block", [
    ("How many sales did Dosa Corner make in September 2024?", "count", "Dosa Corner", None),
    ("How many sales did Juice Point make in September 2024?", "count", "Juice Point", None),
    ("How many sales did Chai Adda make in September 2024?", "count", "Chai Adda", None),
    ("How many sales did Biryani Hub make in September 2024?", "count", "Biryani Hub", None),
    ("How many sales were made in September 2024?", "count", None, None),
    ("Total sales from Juice Point in September 2024", "sum", "Juice Point", None),
    ("Total sales from Chai Adda in September 2024", "sum", "Chai Adda", None),
    ("Total sales from Biryani Hub in September 2024", "sum", "Biryani Hub", None),
    ("Total sales from Dosa Corner in September 2024", "sum", "Dosa Corner", None),
    ("Total sales from Hostel Block in September 2024", "sum", None, "Hostel Block"),
    ("Total sales from Main Block in September 2024", "sum", None, "Main Block"),
    ("Total sales in September 2024", "sum", None, None),
    ("Average sale at Juice Point in September 2024", "mean", "Juice Point", None),
    ("Average sale at Hostel Block in September 2024", "mean", None, "Hostel Block"),
])
def test_canteen(q, agg, stall, block):
    status, value = canteen_oracle(agg, stall, block)
    check_answer(ask("canteen", q), status, value)


@pytest.mark.parametrize("q", [
    "Total sales from Pizza Palace in September 2024",
    "Total sales in September 2023",
    "Which stall made the most profit?",
    "Why did Chai Adda sell less?",
])
def test_canteen_refusals(q):
    assert ask("canteen", q)["status"] == "abstained"


# ---------- 7. Safety: the AST gate blocks dangerous proof code : 7 ----------
@pytest.mark.parametrize("code", [
    "import os\nos.system('rm -rf /')",
    "import subprocess\nsubprocess.run(['ls'])",
    "import socket\nsocket.socket()",
    "eval('1+1')",
    "exec('print(1)')",
    "open('/etc/passwd').read()",
    "x = ().__class__.__bases__",
])
def test_unsafe_code_blocked(code):
    assert executor.check_code(code)


# ---------- 8. Proof integrity : 3 ----------
def test_literal_proof_rejected():
    assert verifier.is_literal_proof('print("RESULT=" + \'{"value": 2000}\')')


def test_proof_is_standalone_python():
    r = ask("example", "What was revenue from USD orders in January 2024?")
    out = executor.run_file(ROOT / r["proof_path"])
    assert out["ok"] and out["stdout"].strip().startswith("RESULT=")
    assert out["result"]["value"] == 2000.0 and out["result"]["data_fingerprint"]


def test_tampered_data_is_caught(tmp_path):
    shutil.copytree(ROOT / "data/example", ROOT / "data/_tamper")
    try:
        t = load_folder(str(ROOT / "data/_tamper"))
        r = engine.run_question("What was revenue from USD orders in January 2024?", t, profile_all(t))
        assert r["value"] == 2000.0 and engine.rerun_proof(r["proof_path"])["match"]
        p = ROOT / "data/_tamper/orders.csv"
        p.write_text(p.read_text().replace("1200.00", "9200.00"))
        assert engine.rerun_proof(r["proof_path"])["match"] is False
    finally:
        shutil.rmtree(ROOT / "data/_tamper")


# ---------- 9. Exact date ranges vs the oracle : 3 ----------
@pytest.mark.parametrize("q,lo,hi", [
    ("total revenue from 2024-1-2 to 2024-2-6 here is in the format of year/month/date", "2024-01-02", "2024-02-06"),
    ("What was revenue from USD orders from 2024-02-10 to 2024-02-20?", "2024-02-10", "2024-02-20"),
    ("Total USD revenue from 2024/05/01 to 2024/05/31", "2024-05-01", "2024-05-31"),
])
def test_nimbus_date_ranges(q, lo, hi):
    o = pd.read_csv(ROOT / "data/nimbus_retail/orders.csv", dtype=str).drop_duplicates()
    o = o[~o.order_date.str.contains("/") & (o.order_date >= lo) & (o.order_date <= hi)]
    if "orders" in q:
        o = o[o.currency == "USD"]
    assert (o.currency == "USD").all() or "USD revenue" in q
    fx = pd.read_csv(ROOT / "data/nimbus_retail/fx_rates.csv", dtype=str)
    rate = o.order_date.str[:7].map(dict(zip(fx.month, fx.eur_to_usd.astype(float))))
    amt = pd.to_numeric(o.amount) * rate.where(o.currency == "EUR", 1.0)
    check_answer(ask("nimbus_retail", q), "answered", round(float(amt.sum()), 2))
