"""Turn uploaded files into CSV tables the engine can prove answers from.  Owner: Daniel.

CSV and Excel are copied as tables. PDF and Word files are searched for tables
(every table becomes its own CSV, first row = header). The proofs then read these CSVs,
so anyone can re-run them.
"""
import io
import re
from pathlib import Path

import pandas as pd


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", Path(name).stem.lower()).strip("_") or "table"


def _table_from_rows(rows):
    rows = [[(c or "").strip() for c in r] for r in rows if r and any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return None
    header = [h or f"col{i + 1}" for i, h in enumerate(rows[0])]
    width = len(header)
    body = [(r + [""] * width)[:width] for r in rows[1:]]
    return pd.DataFrame(body, columns=header)


def extract(name: str, data: bytes) -> list[tuple[str, pd.DataFrame]]:
    """Return [(table_name, DataFrame), ...] for one uploaded file. Raises ValueError with a friendly reason."""
    ext = Path(name).suffix.lower()
    base = _clean_name(name)
    if ext == ".csv":
        return [(base, pd.read_csv(io.BytesIO(data), dtype=str, skipinitialspace=True))]
    if ext in (".xlsx", ".xls"):
        sheets = pd.read_excel(io.BytesIO(data), dtype=str, sheet_name=None)
        return [(base if len(sheets) == 1 else f"{base}_{_clean_name(s)}", df) for s, df in sheets.items()]
    if ext == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            raise ValueError("PDF support needs one package: pip install pdfplumber") from None
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p, page in enumerate(pdf.pages, 1):
                for t, rows in enumerate(page.extract_tables(), 1):
                    df = _table_from_rows(rows)
                    if df is not None:
                        out.append((f"{base}_p{p}_t{t}", df))
        if not out:
            raise ValueError(f"{name}: no tables found in this PDF (scanned images and plain text can't be read yet)")
        return out
    if ext == ".docx":
        try:
            import docx
        except ImportError:
            raise ValueError("Word support needs one package: pip install python-docx") from None
        doc = docx.Document(io.BytesIO(data))
        out = []
        for t, table in enumerate(doc.tables, 1):
            df = _table_from_rows([[c.text for c in row.cells] for row in table.rows])
            if df is not None:
                out.append((f"{base}_t{t}", df))
        if not out:
            raise ValueError(f"{name}: no tables found in this Word file")
        return out
    raise ValueError(f"{name}: unsupported file type {ext or '(none)'}; use CSV, Excel, PDF or Word")


def save_uploads(files, dest: Path) -> tuple[list[str], list[str]]:
    """files: [(name, bytes)]. Writes CSVs into dest. Returns (table names written, error messages)."""
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("*.csv"):
        old.unlink()
    written, errors = [], []
    for name, data in files:
        try:
            for table, df in extract(name, data):
                df.to_csv(dest / f"{table}.csv", index=False)
                written.append(table)
        except Exception as e:  # noqa: BLE001  (show the reason, keep the other files)
            errors.append(str(e) if isinstance(e, ValueError) else f"{name}: couldn't read it ({e})")
    return written, errors
