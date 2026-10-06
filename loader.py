"""Load every table in a folder.  Owner: Daniel."""
from pathlib import Path

import pandas as pd


def _maybe_numeric(col: pd.Series) -> pd.Series:
    """Turn a text column into numbers only if every non-blank value is a number.
    ID-like and date-like columns always stay as text, so detectors see the raw values."""
    name = col.name.lower()
    if name.endswith("id") or "date" in name or "month" in name:
        return col
    converted = pd.to_numeric(col, errors="coerce")
    if converted[col.notna()].notna().all():
        return converted
    return col


def load_folder(path: str) -> dict[str, pd.DataFrame]:
    """Return {"orders": df, ...} for every .csv / .xlsx file in `path` (file name without extension)."""
    tables = {}
    for f in sorted(Path(path).iterdir()):
        if f.suffix.lower() == ".csv":
            df = pd.read_csv(f, dtype=str, skipinitialspace=True)
        elif f.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(f, dtype=str)
        else:
            continue
        tables[f.stem] = df.apply(_maybe_numeric)
    return tables
