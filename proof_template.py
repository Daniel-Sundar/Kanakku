"""The proof script every answer ships with.  Owner: Daniel.

planner.make_proof() fills the PLAN block at the top and saves it as proofs/q_<n>.py.
The script reads the CSVs itself, handles every trap with a stated rule, and prints ONE line:
  RESULT={"value": 2000.0, "unit": "USD", "rows_used": [...], "assumptions": [...]}
  RESULT={"value": {"if_DD/MM": 1788.0, "if_MM/DD": 2814.0}, ...}     (two plausible readings)
  RESULT={"abstain": "why", "needed": "what would fix it"}             (data can't support it)
"""

TEMPLATE = r'''"""Kanakku proof: {question}
Re-run it yourself:  python {proof_path}
"""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd

# ---- PLAN (filled in from the question) ------------------------------------
DATA = Path(__file__).resolve().parents[1] / {data_rel}
FACT = {fact!r}                 # main table
DATE_COL = {date_col!r}
VALUE_COL = {value_col!r}       # None means "count rows"
AGG = {agg!r}                   # sum | count | mean
MONTHS = {months!r}             # months in scope, [] = all
DAYS = {days!r}                 # [first day, last day] when the question gives exact dates
CURRENCY_COL = {currency_col!r}
CURRENCY_MODE = {currency_mode!r}   # filter | convert | none
CURRENCY = {currency!r}
KEY_COL = {key_col!r}           # join key to the dimension tables
FILTERS = {filters!r}           # e.g. {{"region": "North"}} looked up in the other tables
# ----------------------------------------------------------------------------

# Fingerprint of the exact data this proof read: if anyone edits a CSV, the fingerprint changes.
FINGERPRINT = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(DATA.glob("*.csv")))).hexdigest()[:16]

def finish(**kw):
    kw["data_fingerprint"] = FINGERPRINT
    print("RESULT=" + json.dumps(kw))
    raise SystemExit(0)

tables = {{p.stem: pd.read_csv(p, dtype=str, skipinitialspace=True) for p in sorted(DATA.glob("*.csv"))}}
df = tables[FACT]
assumptions = []

# Trap 1: exact duplicate rows are counted once.
dupes = int(df.duplicated().sum())
if dupes:
    assumptions.append(f"{{dupes}} exact duplicate row(s) in {{FACT}} counted once")
    df = df.drop_duplicates()
if VALUE_COL:
    df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
id_col = next((c for c in df.columns if c.lower().endswith(("id", "_no", "number")) and c != KEY_COL), None)
label = (lambda i: str(df.loc[i, id_col])) if id_col else (lambda i: f"row {{i}}")

# Trap 2: a date like 03/02/2024 can be read two ways, so we compute both readings.
ISO = re.compile(r"^\d{{4}}-\d{{2}}-\d{{2}}$")
SLASH = re.compile(r"^(\d{{1,2}})[/-](\d{{1,2}})[/-](\d{{4}})$")

def to_month(value, reading):
    s = str(value).strip()
    if ISO.match(s):
        return s[:7]
    m = SLASH.match(s)
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
    day, month = (a, b) if reading == "DD/MM" else (b, a)
    if month > 12:                      # only one reading is a real date
        day, month = month, day
    return f"{{y}}-{{month:02d}}"

def to_day(value, reading):
    s = str(value).strip()
    if ISO.match(s):
        return s[:10]
    m = SLASH.match(s)
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
    day, month = (a, b) if reading == "DD/MM" else (b, a)
    if month > 12:
        day, month = month, day
    return f"{{y}}-{{month:02d}}-{{day:02d}}"

ambiguous = []
if DATE_COL:
    for i, v in df[DATE_COL].items():
        m = SLASH.match(str(v).strip())
        if m and int(m.group(1)) <= 12 and int(m.group(2)) <= 12 and m.group(1) != m.group(2):
            ambiguous.append(i)

def fx_rate(src, dst, month):
    """Look for a table with a month column and a column named like eur_to_usd."""
    for t in tables.values():
        col = f"{{src}}_to_{{dst}}".lower()
        cols = {{c.lower(): c for c in t.columns}}
        if "month" in cols and col in cols:
            row = t[t[cols["month"]] == month]
            if len(row):
                return float(row[cols[col]].iloc[0])
    return None

def compute(reading):
    d = df.copy()
    if DATE_COL:
        d["_month"] = d[DATE_COL].apply(lambda v: to_month(v, reading))
    if MONTHS:
        d = d[d["_month"].isin(MONTHS)]
        if len(d) == 0:     # a period the data doesn't cover is unknown, not zero
            have = sorted(m for m in df[DATE_COL].apply(lambda v: to_month(v, reading)).dropna().unique())
            return {{"abstain": f"there are no rows for {{MONTHS[0]}}" + (f" to {{MONTHS[-1]}}" if len(MONTHS) > 1 else "")
                               + (f"; the data covers {{have[0]}} to {{have[-1]}}" if have else ""),
                    "needed": "data for that period, or ask about a period inside the data"}}
        if DAYS:
            day = d[DATE_COL].apply(lambda v: to_day(v, reading))
            d = d[(day >= DAYS[0]) & (day <= DAYS[1])]
    # Trap 3: the same customer described differently in two tables.
    for col, want in FILTERS.items():
        if col == KEY_COL:              # one customer / buyer by id
            d = d[d[KEY_COL].str.upper() == str(want).upper()]
            continue
        sources = [(n, t) for n, t in tables.items() if n != FACT and col in t.columns and KEY_COL in t.columns]
        maps = [(n, dict(zip(t[KEY_COL], t[col]))) for n, t in sources]
        for k in d[KEY_COL].dropna().unique():
            vals = {{n: m.get(k) for n, m in maps if k in m}}
            # only a disagreement that changes whether this row is in or out matters
            if len(set(vals.values())) > 1 and any(str(v).lower() == str(want).lower() for v in vals.values()):
                return {{"abstain": f"{{KEY_COL}} {{k}} has {{col}} " + " vs ".join(f"{{v}} in {{n}}" for n, v in vals.items()),
                        "needed": f"which table is correct for {{k}}'s {{col}}"}}
        lookup = {{}}
        for _, m in maps:
            lookup.update(m)
        d = d[d[KEY_COL].map(lookup).str.lower() == str(want).lower()]
    # Trap 4: mixed currencies are filtered or converted, never added raw.
    if CURRENCY_COL and CURRENCY_MODE == "filter":
        d = d[d[CURRENCY_COL].str.upper() == CURRENCY]
    # Trap 5: a blank value inside the answer's rows makes the answer unknowable.
    if VALUE_COL:
        blanks = d[d[VALUE_COL].isna()]
        if len(blanks):
            who = ", ".join(label(i) for i in blanks.index)
            return {{"abstain": f"{{VALUE_COL}} is blank for {{who}}, which is inside the question's scope",
                    "needed": f"the {{VALUE_COL}} for {{who}}"}}
    if CURRENCY_COL and VALUE_COL:
        curs = sorted(d[CURRENCY_COL].dropna().str.upper().unique())
        if CURRENCY_MODE == "convert":
            vals = []
            for i, r in d.iterrows():
                cur = str(r[CURRENCY_COL]).upper()
                if cur == CURRENCY:
                    vals.append(r[VALUE_COL])
                    continue
                rate = fx_rate(cur, CURRENCY, r["_month"])
                if rate is None:
                    return {{"abstain": f"no {{cur}} to {{CURRENCY}} rate for {{r['_month']}} ({{label(i)}} needs it)",
                            "needed": f"the {{cur}} to {{CURRENCY}} rate for {{r['_month']}}"}}
                vals.append(r[VALUE_COL] * rate)
            d = d.assign(**{{VALUE_COL: vals}}) if len(d) else d
        elif len(curs) > 1:
            return {{"abstain": f"the rows mix currencies ({{', '.join(curs)}}) and the question doesn't say which",
                    "needed": "which currency to report in (e.g. add 'in USD')"}}
    if AGG == "count":
        value = int(len(d))
    elif len(d) == 0:
        value = 0.0
    elif AGG == "mean":
        value = round(float(d[VALUE_COL].mean()), 2)
    else:
        value = round(float(d[VALUE_COL].sum()), 2)
    return {{"value": value, "rows": [label(i) for i in d.index]}}

def _touches_scope(i):
    dd, mm = to_month(df.loc[i, DATE_COL], "DD/MM"), to_month(df.loc[i, DATE_COL], "MM/DD")
    if MONTHS:
        return dd in MONTHS or mm in MONTHS
    return CURRENCY_MODE == "convert"   # the month still picks the exchange rate

in_play = [i for i in ambiguous if _touches_scope(i)]
readings = ["DD/MM", "MM/DD"] if in_play else ["DD/MM"]
results = {{r: compute(r) for r in readings}}
unit = CURRENCY if (CURRENCY and AGG != "count") else ("rows" if AGG == "count" else "")

stops = [r for r in results.values() if "abstain" in r]
if stops:
    finish(abstain=stops[0]["abstain"], needed=stops[0]["needed"])
values = {{r: res["value"] for r, res in results.items()}}
if len(set(values.values())) == 1:
    first = results[readings[0]]
    if in_play:
        assumptions.append(f"date of {{', '.join(label(i) for i in in_play)}} is ambiguous but both readings give the same answer")
    finish(value=first["value"], unit=unit, rows_used=first["rows"], assumptions=assumptions)
assumptions.append(f"date of {{', '.join(label(i) for i in in_play)}} is ambiguous, so both readings are shown")
finish(value={{f"if_{{r}}": v for r, v in values.items()}}, unit=unit,
       rows_used={{f"if_{{r}}": res["rows"] for r, res in results.items()}}, assumptions=assumptions)
'''


LOOKUP_TEMPLATE = r'''"""ProofPilot proof (list/count): {question}
Re-run it yourself:  python {proof_path}
"""
from pathlib import Path
import hashlib
import json
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / {data_rel}
TABLES = {tables!r}          # where the list comes from
KEY = {key!r}
FILTERS = {filters!r}
COUNT = {count!r}            # True: answer is how many; False: the list itself

FINGERPRINT = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(DATA.glob("*.csv")))).hexdigest()[:16]

def finish(**kw):
    kw["data_fingerprint"] = FINGERPRINT
    print("RESULT=" + json.dumps(kw))
    raise SystemExit(0)

squash = lambda x: "".join(ch for ch in str(x).lower() if ch.isalnum())
answers = {{}}
for name in TABLES:
    t = pd.read_csv(DATA / f"{{name}}.csv", dtype=str, skipinitialspace=True).drop_duplicates()
    for col, want in FILTERS.items():
        t = t[t[col].map(squash) == squash(want)]
    label_col = next((c for c in t.columns if "name" in c.lower()), None)
    answers[name] = sorted(f"{{r[KEY]}} {{r[label_col]}}".strip() if label_col else str(r[KEY]) for _, r in t.iterrows())
# Trap: two tables listing the same things differently
lists = list(answers.values())
if any(set(x) != set(lists[0]) for x in lists[1:]):
    a, b = list(answers)[:2]
    only = sorted(set(answers[a]) ^ set(answers[b]))
    finish(abstain=f"{{a}} and {{b}} disagree about {{', '.join(only)}}",
           needed=f"which table is correct, or name one table in the question (e.g. 'use {{a}}')")
rows = lists[0] if lists else []
assumptions = [f"from {{', '.join(TABLES)}}"] + [f"{{c}} = {{v}}" for c, v in FILTERS.items()]
finish(value=len(rows) if COUNT else rows, unit="items" if COUNT else "list", rows_used=rows, assumptions=assumptions)
'''
