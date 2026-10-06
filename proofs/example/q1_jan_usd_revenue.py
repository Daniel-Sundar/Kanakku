"""Q1: Total revenue from USD-denominated orders in January 2024 (exact duplicates removed)."""
from pathlib import Path
import json
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "example"
orders = pd.read_csv(DATA / "orders.csv", dtype={"order_date": str})

orders = orders.drop_duplicates()                       # trap: order 1002 appears twice
iso = orders[orders["order_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")].copy()
iso["order_date"] = pd.to_datetime(iso["order_date"], format="%Y-%m-%d")
jan_usd = iso[(iso["order_date"].dt.strftime("%Y-%m") == "2024-01") & (iso["currency"] == "USD")]

# Safety: no non-ISO (ambiguous) date may fall in scope. 03/02/2024 is Feb 3 or Mar 2, never January.
assert jan_usd["amount"].notna().all(), "missing amount inside the answer scope"
value = round(float(jan_usd["amount"].sum()), 2)
print("RESULT=" + json.dumps({"value": value, "unit": "USD", "rows_used": jan_usd["order_id"].tolist()}))
