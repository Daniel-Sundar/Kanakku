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
    # TODO (B3)
    return []


def detect_missing(df: pd.DataFrame, table: str) -> list[dict]:
    """Find blank values.

    Return ONE flag PER COLUMN that has blanks, with
      column=<that column>, trap="missing_values", severity="high",
      count = number of blanks in that column,
      example_rows = row numbers of the blanks,
      message like "orders.amount: 1 missing value(s)".
    Hint: df[col].isna()
    """
    # TODO (B3)
    return []


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
    # TODO (B3)
    return []


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
    # TODO (B3)
    return []
