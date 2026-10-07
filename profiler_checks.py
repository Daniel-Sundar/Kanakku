# Trap Radar detectors - maintained by Aaron (B)
"""Trap detectors.  Owner: B.

Fill in the 4 functions marked TODO. Do NOT change their names or arguments.
Check your work with:   pytest tests/test_profiler_checks.py -q

Every function gets one table (`df`) and its name (`table`), and returns a list of Flags.
Return an empty list [] when the trap is not there.
Use make_flag() to build each Flag so the shape is always right.
"""
import re

import pandas as pd


def make_flag(table, column, trap, severity, count, example_rows, message):
    """Build one Flag. Already done for you: don't change it."""
    return {
        "table": table,
        "column": column,
        "trap": trap,
        "severity": severity,          # "high" | "medium" | "low"
        "count": int(count),
        "example_rows": [int(i) for i in list(example_rows)[:5]],   # at most 5 row numbers
        "message": message,
    }


def detect_duplicates(df: pd.DataFrame, table: str) -> list[dict]:
    """Find rows that are exact copies of an earlier row.

    If there are any: return ONE flag with
      column="*", trap="duplicate_rows", severity="high",
      count = how many extra copies there are,
      example_rows = the row numbers (df index) of the copies,
      message like "orders: 1 exact duplicate row(s)".
    Hint: df.duplicated()
    """
    d = df.duplicated()
    if not d.any():
        return []
    return [make_flag(table, "*", "duplicate_rows", "high", d.sum(), df.index[d],
                      f"{table}: {d.sum()} exact duplicate row(s)")]


def detect_missing(df: pd.DataFrame, table: str) -> list[dict]:
    """Find blank values.

    Return ONE flag PER COLUMN that has blanks, with
      column=<that column>, trap="missing_values", severity="high",
      count = number of blanks in that column,
      example_rows = row numbers of the blanks,
      message like "orders.amount: 1 missing value(s)".
    Hint: df[col].isna()
    """
    out = []
    for col in df.columns:
        m = df[col].isna()
        if m.any():
            out.append(make_flag(table, col, "missing_values", "high", m.sum(), df.index[m],
                                 f"{table}.{col}: {m.sum()} missing value(s)"))
    return out


def detect_mixed_currency(df: pd.DataFrame, table: str) -> list[dict]:
    """Find a currency column that has more than one currency in it.

    Only look at columns whose name contains "currency" (any upper/lower case).
    If a column has 2 or more different values (ignore blanks): return ONE flag with
      column=<that column>, trap="mixed_currency", severity="high",
      count = number of different currencies,
      example_rows = row numbers of rows NOT in the most common currency,
      message must name the currencies, like "orders.currency: 2 currencies (EUR, USD)".
    Hint: df[col].value_counts()
    """
    out = []
    for col in df.columns:
        if "currency" not in col.lower():
            continue
        vc = df[col].value_counts()
        if len(vc) >= 2:
            rows = df.index[df[col].notna() & (df[col] != vc.index[0])]
            out.append(make_flag(table, col, "mixed_currency", "high", len(vc), rows,
                                 f"{table}.{col}: {len(vc)} currencies ({', '.join(sorted(vc.index))})"))
    return out


AMBIGUOUS = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")


def detect_ambiguous_dates(df: pd.DataFrame, table: str) -> list[dict]:
    """Find dates like 03/02/2024 that could be read two ways (3 Feb or 2 Mar).

    Only look at columns whose name contains "date" (any case).
    A value is ambiguous when it matches AMBIGUOUS above AND both of the first two
    numbers are 12 or less AND they are different (05/05/2024 is NOT ambiguous).
    If any: return ONE flag per column with
      trap="ambiguous_date", severity="high",
      count = number of ambiguous values,
      example_rows = their row numbers,
      message like "orders.order_date: 1 ambiguous date(s), e.g. 03/02/2024".
    Hint: AMBIGUOUS.match(str(value))
    """
    out = []
    for col in df.columns:
        if "date" not in col.lower():
            continue
        rows = []
        for i, v in df[col].items():
            m = AMBIGUOUS.match(str(v))
            if m and int(m[1]) <= 12 and int(m[2]) <= 12 and m[1] != m[2]:
                rows.append(i)
        if rows:
            out.append(make_flag(table, col, "ambiguous_date", "high", len(rows), rows,
                                 f"{table}.{col}: {len(rows)} ambiguous date(s), e.g. {df[col][rows[0]]}"))
    return out
