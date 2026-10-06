"""Run every trap check on every table.  Owner: Daniel."""
import pandas as pd

import profiler_checks as pc

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def detect_missing_months(df: pd.DataFrame, table: str) -> list[dict]:
    """Rate tables (a `month` column like 2024-01): flag months missing between the first and last."""
    if "month" not in df.columns:
        return []
    months = pd.PeriodIndex(df["month"].dropna().astype(str), freq="M")
    if len(months) < 2:
        return []
    full = pd.period_range(months.min(), months.max(), freq="M")
    gaps = [str(m) for m in full if m not in set(months)]
    if not gaps:
        return []
    return [pc.make_flag(table, "month", "missing_period", "high", len(gaps), [],
                         f"{table}: no row for {', '.join(gaps)}")]


def detect_contradictions(tables: dict) -> list[dict]:
    """Two tables share an *_id key and another column, but disagree on its value."""
    flags = []
    names = list(tables)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            da, db = tables[a], tables[b]
            keys = [c for c in da.columns if c in db.columns and c.lower().endswith("_id")]
            for key in keys:
                if da[key].duplicated().any() or db[key].duplicated().any():
                    continue  # only compare one-row-per-key tables (e.g. two customer lists)
                shared = [c for c in da.columns if c in db.columns and c != key]
                m = da.merge(db, on=key, suffixes=("_a", "_b"))
                for col in shared:
                    diff = m[m[f"{col}_a"].astype(str) != m[f"{col}_b"].astype(str)]
                    if len(diff):
                        ex = diff.iloc[0]
                        flags.append(pc.make_flag(
                            f"{a}+{b}", col, "contradiction", "high", len(diff), [],
                            f"{a} vs {b}: {col} differs for {len(diff)} {key}(s), e.g. "
                            f"{ex[key]}: {ex[f'{col}_a']} vs {ex[f'{col}_b']}"))
    return flags


def profile_all(tables: dict) -> list[dict]:
    flags = []
    for name, df in tables.items():
        for check in (pc.detect_duplicates, pc.detect_missing,
                      pc.detect_mixed_currency, pc.detect_ambiguous_dates, detect_missing_months):
            flags.extend(check(df, name))
    flags.extend(detect_contradictions(tables))
    return sorted(flags, key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
