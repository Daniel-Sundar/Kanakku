"""Question -> JSON plan -> proof script.  Owner: Daniel.

The AI (or the rule parser when no AI is reachable) only produces a small JSON plan.
The proof code is generated from that plan by proof_template.py, so the AI can never type a number.
"""
import json
import re

import pandas as pd

import llm_client
from proof_template import LOOKUP_TEMPLATE, TEMPLATE

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
VALUE_WORDS = ("amount", "revenue", "sales", "price", "total", "value", "fee", "paid")
# Concepts people ask about that need a column we may not have.
CONCEPTS = {"profit": ["profit", "cost", "margin"], "margin": ["margin", "cost"],
            "cost": ["cost", "expense"], "expense": ["expense", "cost"], "salary": ["salary"],
            "rating": ["rating"], "satisfaction": ["satisfaction", "rating"], "discount": ["discount"],
            "tax": ["tax", "gst"], "refund": ["refund", "return"], "inventory": ["stock", "inventory"]}


# ---------- schema ---------------------------------------------------------
def schema(tables: dict) -> dict:
    """Pick the fact table and its date / value / currency / key columns by name."""
    def cols(df, words):
        return [c for c in df.columns if any(w in c.lower() for w in words)]
    best, best_score = None, -1
    for name, df in tables.items():
        score = (len(cols(df, ("date",))) > 0) * 2 + (len(cols(df, VALUE_WORDS)) > 0) * 2 + len(df) / 1e6
        if score > best_score:
            best, best_score = name, score
    df = tables[best]
    date_col = next(iter(cols(df, ("date",))), None)
    value_col = next((c for c in cols(df, VALUE_WORDS) if pd.to_numeric(df[c], errors="coerce").notna().any()), None)
    currency_col = next(iter(cols(df, ("currency", "curr"))), None)
    others = [c for n, t in tables.items() if n != best for c in t.columns]
    key_col = next((c for c in df.columns if c.lower().endswith("_id") and c in others), None)
    currencies = sorted(df[currency_col].dropna().str.upper().unique()) if currency_col else []
    dims = {}
    for n, t in tables.items():
        if n != best and key_col in t.columns:
            for c in t.columns:
                if c != key_col and not pd.api.types.is_numeric_dtype(t[c]) and t[c].nunique() <= 50:
                    dims.setdefault(c, set()).update(str(v) for v in t[c].dropna())
    all_cols = {c.lower() for t in tables.values() for c in t.columns}
    keys = sorted(df[key_col].dropna().astype(str).unique()) if key_col else []
    present = set()
    for v in (df[date_col].dropna().astype(str) if date_col else []):
        v = v.strip()
        if re.match(r"^\d{4}-\d{2}", v):
            present.add(v[:7])
        elif re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}$", v):
            a, b, y = re.split(r"[/-]", v)
            present.update(f"{y}-{int(m):02d}" for m in (a, b) if 1 <= int(m) <= 12)
    nums = [c for c in df.columns if c not in (date_col, key_col) and not c.lower().endswith(("id", "_no"))
            and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.8]
    return {"months_present": sorted(present), "num_cols": nums,
            "fact": best, "date_col": date_col, "value_col": value_col, "currency_col": currency_col,
            "key_col": key_col, "keys": keys, "currencies": currencies, "dims": dims, "all_cols": all_cols}


# ---------- plan from rules -------------------------------------------------
def rule_plan(question: str, s: dict) -> dict:
    q = question.lower()
    plan = {"agg": "sum", "months": [], "currency_mode": "none", "currency": None, "filters": {}}
    if re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", q):
        plan["agg"] = "count"
    elif re.search(r"\baverage\b|\bmean\b|\bavg\b", q):
        plan["agg"] = "mean"
    plan["days"] = []
    year = (re.search(r"\b(20\d\d)\b", q) or [None, None])[1]
    qm = re.search(r"\bq([1-4])\b", q)
    hm = re.search(r"\bh([12])\b", q)
    days = [f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in re.findall(r"\b(20\d\d)[-/.](\d{1,2})[-/.](\d{1,2})\b", q)
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31]
    found = [i + 1 for i, m in enumerate(MONTHS) if re.search(rf"\b{m}\b|\b{m[:3]}\b", q)]
    for n in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+month\b|\bmonth\s+(?:no\.?\s*)?(\d{1,2})\b", q):
        n = int(n[0] or n[1])
        if 1 <= n <= 12 and n not in found:
            found.append(n)
    my = re.search(r"\b(\d{1,2})[/-](20\d\d)\b", q)
    if my and 1 <= int(my.group(1)) <= 12 and not days:
        year, found = my.group(2), found + [int(my.group(1))]
    present = s.get("months_present", [])
    if not year and (found or qm or hm) and present:
        # no year given: use the one year the data has for that month (said in the scope line)
        want = found or ([(int(qm.group(1)) - 1) * 3 + 1] if qm else [(int(hm.group(1)) - 1) * 6 + 1])
        cands = sorted({m[:4] for m in present if int(m[5:]) in want})
        if cands:
            year = cands[-1]
            plan["assumed_year"] = year if len(cands) == 1 else f"{year} (latest year in the data with that month)"
    if days:
        lo, hi = min(days), max(days)
        plan["days"] = [lo, hi]
        months, (y, m) = [], (int(lo[:4]), int(lo[5:7]))
        while (y, m) <= (int(hi[:4]), int(hi[5:7])):
            months.append(f"{y}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        plan["months"] = months
    elif hm and year:
        start = (int(hm.group(1)) - 1) * 6
        plan["months"] = [f"{year}-{m:02d}" for m in range(start + 1, start + 7)]
    elif qm and year:
        start = (int(qm.group(1)) - 1) * 3
        plan["months"] = [f"{year}-{m:02d}" for m in range(start + 1, start + 4)]
    elif found and year:
        if len(found) == 2 and re.search(r"\b(to|through|till|until|-)\b|\bbetween\b", q):
            found = list(range(min(found), max(found) + 1))     # "January to March"
        plan["months"] = [f"{year}-{m:02d}" for m in found]
    elif year:
        plan["months"] = [f"{year}-{m:02d}" for m in range(1, 13)]
    plan["fx_reference"] = bool(re.search(
        r"\b(standard|market|reference|world|official|current|live|default|global|international)\s+"
        r"(fx\s+|exchange\s+|conversion\s+|currency\s+)?(rates?|conversion|metrics?)\b", q))
    for cur in s["currencies"] or ["USD", "EUR", "INR"]:
        c = cur.lower()
        if re.search(rf"\b{c}\s+(orders?|sales?|transactions?|payments?|invoices?|bills?|receipts?)\b|\b(orders|sales|invoices|bills)\s+(in|paid in|billed in)\s+{c}\b", q):
            plan.update(currency_mode="filter", currency=cur)
            break
        if re.search(rf"\b{c}\b", q) and (plan["currency_mode"] != "convert"
                                            or re.search(rf"\b(in|into)\s+{c}\b", q)):
            plan.update(currency_mode="convert", currency=cur)   # "convert USD into INR": INR is the target
    syn = {"qty": ("qty", "quantity", "units", "pieces"), "quantity": ("qty", "quantity", "units")}
    for c in s.get("num_cols", []):
        words = syn.get(c.lower(), (c.lower(), c.lower().replace("_", " ")))
        if c != s["value_col"] and any(re.search(rf"\b{re.escape(w)}\b", q) for w in words):
            plan["value_col"] = c
    for col, values in s["dims"].items():
        for v in values:
            if mentions(q, v):
                plan["filters"][col] = v
    for v in s.get("keys", []):
        if re.search(rf"\b{re.escape(v.lower())}\b", q):
            plan["filters"][s["key_col"]] = v
    return plan


UNSUPPORTED = [
    (re.compile(r"\b(top|highest|lowest|most|least|best|worst|biggest|smallest|rank|ranking|largest)\b", re.I),
     "This asks for a ranking. ProofPilot proves one total, count, average or list at a time.",
     "Ask for one total per item instead, e.g. 'Total USD revenue for customer C5 in January 2024'."),
    (re.compile(r"\b(compare|versus|vs\.?|difference between|growth|trend)\b", re.I),
     "This asks for a comparison. ProofPilot proves one number at a time.",
     "Ask for each period separately, then compare the two proven numbers."),
    (re.compile(r"\b(blank|missing|empty|null|duplicates?|duplicated)\b", re.I),
     "This asks about data problems, which the Trap Radar on the Datasets page already lists with row numbers.",
     "Open Datasets and read the Trap Radar cards."),
]


def unsupported(question: str):
    for rx, reason, needed in UNSUPPORTED:
        if rx.search(question):
            return reason, needed
    return None


def _squash(x: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def mentions(q: str, value: str) -> bool:
    """'Tamil Nadu' matches 'tamil nadu' and 'tamilnadu'."""
    if re.search(rf"\b{re.escape(str(value).lower())}\b", q.lower()):
        return True
    v = _squash(value)
    return len(v) >= 5 and " " in str(value).strip() and v in _squash(q)


# ---------- list questions: "list the buyers in Tamil Nadu" -----------------------
LIST_WORDS = re.compile(r"^\s*(please\s+)?(list|show|name|give|tell|which|who)\b|\blist (of|me|all)\b", re.I)
NUMBER_WORDS = re.compile(r"\b(total|revenue|sum|average|mean|amount|value|spent|sales from|how much)\b", re.I)


def lookup_plan(question: str, tables: dict, s: dict):
    """A plan for listing or counting entities (buyers, customers, stalls), or None if this isn't one."""
    q = question.lower()
    key = s["key_col"]
    if not key:
        return None
    dim_tables = [n for n, t in tables.items() if n != s["fact"] and key in t.columns]
    if not dim_tables:
        return None
    stems = {re.sub(r"s$", "", w) for n in dim_tables for w in re.split(r"[_\W]+", n.lower()) if len(w) > 3}
    stems.add(key.lower().replace("_id", ""))
    entity_named = any(re.search(rf"\b{re.escape(st)}s?\b", q) for st in stems)
    counting = bool(re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", q))
    # one record named by id or name: "who is customer C5", "which state is Aroma Traders in"
    record = {}
    for n in dim_tables:
        t = tables[n]
        for v in t[key].dropna().astype(str).unique():
            if re.search(rf"\b{re.escape(v.lower())}\b", q):
                record[key] = v
        for c in [c for c in t.columns if "name" in c.lower()]:
            for v in t[c].dropna().astype(str).unique():
                if mentions(q, v):
                    record[c] = v
    asks_detail = bool(record) and bool(LIST_WORDS.search(q) or re.search(r"^\s*(what|where|details?|info)\b", q))
    if NUMBER_WORDS.search(q) or not (asks_detail or (entity_named and (LIST_WORDS.search(q) or counting))):
        return None
    if asks_detail and not counting:
        use = [n for n in dim_tables if all(c in tables[n].columns for c in record)]
        return {"kind": "lookup", "tables": use, "key": key, "filters": record, "count": False, "detail": True,
                "entity": "match" if len(record) else key}
    if counting and re.search(r"\b(orders?|sales?|invoices?|transactions?|bills?)\b", q):
        return None                  # "how many orders" counts fact rows, handled by the normal plan
    filters = {}
    for n in dim_tables:
        for c in tables[n].columns:
            if c != key and not pd.api.types.is_numeric_dtype(tables[n][c]) and tables[n][c].nunique() <= 50:
                for v in tables[n][c].dropna().unique():
                    if mentions(q, v):
                        filters[c] = str(v)
    hinted = [n for n in dim_tables if _squash(n) in _squash(q) or _squash(re.sub(r"s$", "", n)) in _squash(q)]
    use = hinted[:1] or [n for n in dim_tables if all(c in tables[n].columns for c in filters)]
    return {"kind": "lookup", "tables": use, "key": key, "filters": filters, "count": counting,
            "entity": next((st for st in stems if re.search(rf"\b{re.escape(st)}s?\b", q)), key) + "s"}


def make_lookup_proof(question: str, plan: dict, data_rel: str, proof_path: str) -> str:
    return LOOKUP_TEMPLATE.format(
        question=question.replace('"""', "'''"), proof_path=proof_path,
        data_rel=" / ".join(repr(p) for p in data_rel.split("/")),
        tables=plan["tables"], key=plan["key"], filters=plan["filters"], count=plan["count"],
        detail=plan.get("detail", False))


# ---------- plan from the AI ------------------------------------------------
def llm_plan(question: str, s: dict, tables: dict):
    """Ask the AI for the same JSON plan. Returns (plan, mode) or (None, reason)."""
    sample = {n: {"columns": list(t.columns), "first_rows": t.head(3).astype(str).values.tolist()}
              for n, t in tables.items()}
    prompt = (
        "You turn a business question into a JSON plan for a pandas script. Reply with JSON only.\n"
        f"Tables: {json.dumps(sample)}\n"
        f"Filterable values: {json.dumps({k: sorted(v) for k, v in s['dims'].items()})}\n"
        f"Currencies in the data: {s['currencies']}\n"
        "JSON keys: agg (sum|count|mean), months (list of YYYY-MM in scope, [] for all), "
        "currency_mode (filter = only rows already in that currency, convert = convert other currencies, none), "
        "currency (e.g. USD or null), filters (object of column -> value from the filterable values).\n"
        f"Question: {question}\nJSON:")
    text, mode = llm_client.generate(prompt, cache_key=question)
    if text is None:
        return None, mode
    try:
        raw = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        plan = {"agg": raw.get("agg", "sum") if raw.get("agg") in ("sum", "count", "mean") else "sum",
                "months": [m for m in raw.get("months") or [] if re.fullmatch(r"\d{4}-\d{2}", str(m))],
                "currency_mode": raw.get("currency_mode") if raw.get("currency_mode") in ("filter", "convert") else "none",
                "currency": (raw.get("currency") or None) and str(raw["currency"]).upper(),
                "filters": {k: v for k, v in (raw.get("filters") or {}).items()
                            if k in s["dims"] and str(v) in s["dims"][k]}}
        if plan["currency_mode"] != "none" and not plan["currency"]:
            plan["currency_mode"] = "none"
        exact = rule_plan(question, s)      # exact day ranges are parsed by rule, never guessed
        plan["days"] = exact["days"]
        if exact["days"] or (exact["months"] and not plan["months"]):
            plan["months"] = exact["months"]
        for k in ("value_col", "assumed_year", "fx_reference"):
            if k in exact:
                plan[k] = exact[k]
        for k, v in exact["filters"].items():
            plan["filters"].setdefault(k, v)
        return plan, mode
    except (AttributeError, json.JSONDecodeError, TypeError):
        return None, f"{mode}: unreadable plan"


def missing_concept(question: str, s: dict):
    q = question.lower()
    for concept, needs in CONCEPTS.items():
        if re.search(rf"\b{concept}", q) and not any(n in c for c in s["all_cols"] for n in needs):
            return concept, needs
    return None


KNOWN = {"total", "revenue", "sales", "orders", "order", "sum", "average", "mean", "count", "how", "what",
         "which", "the", "in", "for", "of", "and", "who", "where", "month", "tell", "list", "number", "amount", "customer", "customers", "region",
         "month", "year", "all", "i", "is", "was", "were", "show", "give", "me", "average", "q1", "q2", "q3", "q4", "h1", "h2"}


COMMON = set("""convert converted provide give get find calculate compute please also then final overall
total revenue sales show tell list what which who where when how many much all every other others currency currencies
into to from by with and or the a an of in on for is are was were be i we my our me you your it this that these those
amount value sum average mean count number data table orders order invoices invoice bills bill buyers buyer
customers customer dealers dealer stalls stall region state city block month year day date seen have has had
answer result report""".split())


def unknown_names(question: str, tables: dict, s: dict) -> list:
    """Names in the question (capitalised words, IDs like C99) that appear nowhere in the data."""
    cands = []
    for sentence in re.split(r"[.!?;:\n]+", question):     # the first word of each sentence is capitalised anyway
        words = re.findall(r"[A-Za-z][A-Za-z0-9_]*", sentence)
        cands += [w for i, w in enumerate(words) if (i > 0 and w[0].isupper() and not w.isupper() and w.lower() not in COMMON)
                  or re.fullmatch(r"[A-Za-z]+\d+", w)]
    if not cands:
        return []
    seen = set()
    for t in tables.values():
        for c in t.columns:
            seen.update(re.findall(r"[a-z0-9]+", str(c).lower()))
            if not pd.api.types.is_numeric_dtype(t[c]):
                for v in t[c].dropna().astype(str).unique():
                    seen.update(re.findall(r"[a-z0-9]+", v.lower()))
    skip = KNOWN | {m for m in MONTHS} | {m[:3] for m in MONTHS} | {c.lower() for c in s["currencies"] or []} \
        | {"usd", "eur", "inr", "gbp"}
    return [w for w in dict.fromkeys(cands) if w.lower() not in skip and w.lower() not in seen]


def make_proof(question: str, plan: dict, s: dict, data_rel: str, proof_path: str) -> str:
    return TEMPLATE.format(
        question=question.replace('"""', "'''"), proof_path=proof_path,
        data_rel=" / ".join(repr(p) for p in data_rel.split("/")),
        fact=s["fact"], date_col=s["date_col"], value_col=None if plan["agg"] == "count" else plan.get("value_col") or s["value_col"],
        agg=plan["agg"], months=plan["months"], days=plan.get("days") or [], currency_col=s["currency_col"],
        currency_mode=plan["currency_mode"] if s["currency_col"] else "none", currency=plan["currency"],
        key_col=s["key_col"], filters=plan["filters"], fx_reference=bool(plan.get("fx_reference")))
