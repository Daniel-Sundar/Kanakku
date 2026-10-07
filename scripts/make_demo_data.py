"""Build the synthetic demo datasets with planted traps.  Owner: Daniel.
Usage: python scripts/make_demo_data.py      (seeded, so it always writes the same files)

data/nimbus_retail: orders, customers_billing, customers_crm, fx_rates (Jan-Jun 2024)
  traps: 25 duplicate orders, EUR orders from March, no FX row for February,
         ambiguous dates like 04/05/2024, 3 blank amounts in June, customer C17's region differs.
data/canteen: sales + stalls (INR), traps: 2 duplicate rows, 1 blank amount.
"""
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(2026)


def nimbus():
    out = ROOT / "data" / "nimbus_retail"
    out.mkdir(parents=True, exist_ok=True)
    regions = ["North", "South", "East", "West"]
    names = ["Asha", "Bharat", "Coastal", "Deccan", "Everest", "Fortune", "Ganga", "Himalaya", "Indus",
             "Jaya", "Kaveri", "Lotus", "Malabar", "Nilgiri", "Orchid", "Pearl", "Quilon", "Ruby",
             "Saffron", "Teak", "Udaya", "Vaigai", "Western", "Yamuna", "Zenith", "Amber", "Banyan",
             "Cedar", "Delta", "Emerald", "Falcon", "Garnet", "Harbor", "Ivory", "Jasmine", "Kestrel",
             "Lagoon", "Monsoon", "Neem", "Opal"]
    kinds = ["Traders", "Mart", "Foods", "Stores", "Retail"]
    cust = [{"customer_id": f"C{i + 1}", "name": f"{n} {rng.choice(kinds)}", "region": rng.choice(regions)}
            for i, n in enumerate(names)]
    billing = pd.DataFrame(cust)
    crm = billing.copy()
    crm.loc[crm["customer_id"] == "C17", "region"] = "East" if billing.loc[16, "region"] != "East" else "West"
    rows, oid = [], 5001
    days = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30}
    for month in range(1, 7):
        for _ in range(45):
            c = rng.choice(cust)["customer_id"]
            day = rng.randint(1, days[month])
            cur = "EUR" if month >= 3 and rng.random() < 0.3 else "USD"
            rows.append({"order_id": oid, "order_date": f"2024-{month:02d}-{day:02d}", "customer_id": c,
                         "amount": f"{rng.randint(80, 2400)}.{rng.choice(['00', '50', '25', '75'])}",
                         "currency": cur})
            oid += 1
    orders = pd.DataFrame(rows)
    # ambiguous dates in April/May only (day <= 12, day != month)
    amb = orders[(orders["order_date"].str[5:7].isin(["04", "05"])) &
                 (orders["order_date"].str[8:10].astype(int) <= 12) &
                 (orders["order_date"].str[8:10].astype(int) != orders["order_date"].str[5:7].astype(int))].index[:4]
    for i in amb:
        y, m, d = orders.loc[i, "order_date"].split("-")
        orders.loc[i, "order_date"] = f"{d}/{m}/{y}"          # written DD/MM, but nobody can tell
    june = orders[orders["order_date"].str.startswith("2024-06")].index[:3]
    orders.loc[june, "amount"] = ""
    dupes = orders[orders["order_date"].str.startswith("2024-01") == False].sample(25, random_state=7)  # noqa: E712
    orders = pd.concat([orders, dupes]).sort_values("order_id", kind="stable").reset_index(drop=True)
    fx = pd.DataFrame({"month": ["2024-01", "2024-03", "2024-04", "2024-05", "2024-06"],
                       "eur_to_usd": [1.09, 1.08, 1.07, 1.08, 1.07]})
    orders.to_csv(out / "orders.csv", index=False)
    billing.to_csv(out / "customers_billing.csv", index=False)
    crm.to_csv(out / "customers_crm.csv", index=False)
    fx.to_csv(out / "fx_rates.csv", index=False)


def canteen():
    out = ROOT / "data" / "canteen"
    out.mkdir(parents=True, exist_ok=True)
    stalls = pd.DataFrame({"stall_id": ["S1", "S2", "S3", "S4"],
                           "stall_name": ["Dosa Corner", "Juice Point", "Chai Adda", "Biryani Hub"],
                           "block": ["Main Block", "Main Block", "Hostel Block", "Hostel Block"]})
    price = {"S1": 60, "S2": 40, "S3": 15, "S4": 120}
    rows = []
    for i in range(50):
        s = rng.choice(list(price))
        qty = rng.randint(5, 40)
        rows.append({"sale_id": 101 + i, "sale_date": f"2024-09-{rng.randint(1, 30):02d}", "stall_id": s,
                     "qty": qty, "amount": qty * price[s]})
    sales = pd.DataFrame(rows).sort_values("sale_date", kind="stable")
    sales.loc[sales.index[10], "amount"] = None
    sales = pd.concat([sales, sales.iloc[[3, 20]]])
    sales.to_csv(out / "sales.csv", index=False)
    stalls.to_csv(out / "stalls.csv", index=False)


if __name__ == "__main__":
    nimbus()
    canteen()
    print("wrote data/nimbus_retail and data/canteen")
