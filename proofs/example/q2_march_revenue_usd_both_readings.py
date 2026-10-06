"""Q2: Total March 2024 revenue in USD. Order 1003 has an ambiguous date (03/02/2024),
so the script computes BOTH readings and reports them separately instead of guessing."""
from pathlib import Path
import json
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "example"
orders = pd.read_csv(DATA / "orders.csv", dtype={"order_date": str}).drop_duplicates()
fx = pd.read_csv(DATA / "fx_rates.csv").set_index("month")["eur_to_usd"]

def month_of(s, slash_format):
    if "-" in s:
        return pd.to_datetime(s, format="%Y-%m-%d").strftime("%Y-%m")
    return pd.to_datetime(s, format=slash_format).strftime("%Y-%m")

def march_total(slash_format):
    df = orders.copy()
    df["month"] = df["order_date"].apply(lambda s: month_of(s, slash_format))
    m = df[df["month"] == "2024-03"].copy()
    assert m["amount"].notna().all(), "missing amount inside the answer scope"
    m["usd"] = m.apply(lambda r: r["amount"] * fx[r["month"]] if r["currency"] == "EUR" else r["amount"], axis=1)
    return round(float(m["usd"].sum()), 2), m["order_id"].tolist()

dd_mm, rows_dd = march_total("%d/%m/%Y")   # 03/02/2024 -> 3 Feb (outside March)
mm_dd, rows_mm = march_total("%m/%d/%Y")   # 03/02/2024 -> 2 Mar (inside March)
print("RESULT=" + json.dumps({"if_DD/MM": {"value": dd_mm, "rows": rows_dd},
                              "if_MM/DD": {"value": mm_dd, "rows": rows_mm}, "unit": "USD"}))
