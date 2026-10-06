"""B's tests (ticket B3). They FAIL until the TODOs in profiler_checks.py are filled. Don't edit this file."""
import pandas as pd

import profiler_checks as pc

KEYS = {"table", "column", "trap", "severity", "count", "example_rows", "message"}


def _ok_shape(flags):
    assert isinstance(flags, list)
    for f in flags:
        assert set(f) == KEYS
        assert f["message"]


# ---------- duplicates ----------
def test_duplicates_found(example):
    flags = pc.detect_duplicates(example["orders"], "orders")
    _ok_shape(flags)
    assert len(flags) == 1
    assert flags[0]["trap"] == "duplicate_rows" and flags[0]["count"] == 1
    assert flags[0]["example_rows"] == [2]


def test_duplicates_none(example):
    assert pc.detect_duplicates(example["customers_crm"], "customers_crm") == []


# ---------- missing ----------
def test_missing_found(example):
    flags = pc.detect_missing(example["orders"], "orders")
    _ok_shape(flags)
    assert len(flags) == 1
    f = flags[0]
    assert (f["column"], f["trap"], f["count"], f["example_rows"]) == ("amount", "missing_values", 1, [4])


def test_missing_one_flag_per_column():
    df = pd.DataFrame({"a": [1, None, None], "b": [None, "x", "y"], "c": [1, 2, 3]})
    flags = pc.detect_missing(df, "t")
    assert sorted((f["column"], f["count"]) for f in flags) == [("a", 2), ("b", 1)]


def test_missing_none(example):
    assert pc.detect_missing(example["fx_rates"], "fx_rates") == []


# ---------- currency ----------
def test_currency_found(example):
    flags = pc.detect_mixed_currency(example["orders"], "orders")
    _ok_shape(flags)
    assert len(flags) == 1
    f = flags[0]
    assert (f["column"], f["trap"], f["count"]) == ("currency", "mixed_currency", 2)
    assert f["example_rows"] == [3, 5]
    assert "EUR" in f["message"] and "USD" in f["message"]


def test_currency_single_is_fine():
    df = pd.DataFrame({"Currency": ["USD", "USD", None]})
    assert pc.detect_mixed_currency(df, "t") == []


def test_currency_ignores_other_columns():
    df = pd.DataFrame({"region": ["North", "South"]})
    assert pc.detect_mixed_currency(df, "t") == []


# ---------- ambiguous dates ----------
def test_dates_found(example):
    flags = pc.detect_ambiguous_dates(example["orders"], "orders")
    _ok_shape(flags)
    assert len(flags) == 1
    f = flags[0]
    assert (f["column"], f["trap"], f["count"], f["example_rows"]) == ("order_date", "ambiguous_date", 1, [3])
    assert "03/02/2024" in f["message"]


def test_dates_not_ambiguous():
    df = pd.DataFrame({"Order_Date": ["2024-01-05", "25/03/2024", "05/05/2024", "13/01/2024", None]})
    assert pc.detect_ambiguous_dates(df, "t") == []
