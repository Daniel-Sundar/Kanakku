"""Question -> JSON plan -> proof script.  Owner: Daniel.

The AI (or the rule parser when no AI is reachable) only produces a small JSON plan.
The proof code is generated from that plan by proof_template.py, so the AI can never type a number.
"""
import json
import re

import pandas as pd

import llm_client
from proof_template import TEMPLATE

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
    return {"fact": best, "date_col": date_col, "value_col": value_col, "currency_col": currency_col,
            "key_col": key_col, "currencies": currencies, "dims": dims, "all_cols": all_cols}


# ---------- plan from rules -------------------------------------------------
def rule_plan(question: str, s: dict) -> dict:
    q = question.lower()
    plan = {"agg": "sum", "months": [], "currency_mode": "none", "currency": None, "filters": {}}
    if re.search(r"\bhow many\b|\bnumber of\b|\bcount\b", q):
        plan["agg"] = "count"
    elif re.search(r"\baverage\b|\bmean\b|\bavg\b", q):
        plan["agg"] = "mean"
    year = (re.search(r"\b(20\d\d)\b", q) or [None, None])[1]
    qm = re.search(r"\bq([1-4])\b", q)
    if qm and year:
        start = (int(qm.group(1)) - 1) * 3
        plan["months"] = [f"{year}-{m:02d}" for m in range(start + 1, start + 4)]
    else:
        found = [i + 1 for i, m in enumerate(MONTHS) if re.search(rf"\b{m}\b|\b{m[:3]}\b", q)]
        if found and year:
            plan["months"] = [f"{year}-{m:02d}" for m in found]
        elif year:
            plan["months"] = [f"{year}-{m:02d}" for m in range(1, 13)]
    for cur in s["currencies"] or ["USD", "EUR", "INR"]:
        c = cur.lower()
        if re.search(rf"\b{c}\s+(orders|sales|transactions|payments)\b|\b(orders|sales)\s+(in|paid in)\s+{c}\b", q):
            plan.update(currency_mode="filter", currency=cur)
            break
        if re.search(rf"\b{c}\b", q):
            plan.update(currency_mode="convert", currency=cur)
    for col, values in s["dims"].items():
        for v in values:
            if re.search(rf"\b{re.escape(v.lower())}\b", q):
                plan["filters"][col] = v
    return plan


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
        return plan, mode
    except (AttributeError, json.JSONDecodeError, TypeError):
        return None, f"{mode}: unreadable plan"


def missing_concept(question: str, s: dict):
    q = question.lower()
    for concept, needs in CONCEPTS.items():
        if re.search(rf"\b{concept}", q) and not any(n in c for c in s["all_cols"] for n in needs):
            return concept, needs
    return None


def make_proof(question: str, plan: dict, s: dict, data_rel: str, proof_path: str) -> str:
    return TEMPLATE.format(
        question=question.replace('"""', "'''"), proof_path=proof_path,
        data_rel=" / ".join(repr(p) for p in data_rel.split("/")),
        fact=s["fact"], date_col=s["date_col"], value_col=None if plan["agg"] == "count" else s["value_col"],
        agg=plan["agg"], months=plan["months"], currency_col=s["currency_col"],
        currency_mode=plan["currency_mode"] if s["currency_col"] else "none", currency=plan["currency"],
        key_col=s["key_col"], filters=plan["filters"])
