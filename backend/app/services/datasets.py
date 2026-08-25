from pathlib import Path

import pandas as pd
from fastapi import HTTPException

from app.services.storage import LocalDatasetStorage


def read_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        # Some spreadsheet applications retain a .csv name when exporting an
        # Excel workbook. Identify the workbook signature from its contents,
        # rather than trusting the filename alone.
        signature = path.read_bytes()[:8]
        if signature.startswith(b"PK\\x03\\x04") or signature.startswith(b"\\xd0\\xcf\\x11\\xe0"):
            return pd.read_excel(path)
        # CSV files exported from Excel and regional business tools commonly use
        # a BOM, Windows encoding, or a semicolon/tab separator. Let pandas infer
        # the delimiter while trying the common encodings before rejecting a file.
        errors: list[Exception] = []
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                frame = pd.read_csv(path, encoding=encoding, sep=None, engine="python")
                if frame.empty and len(frame.columns) == 0:
                    raise ValueError("The CSV has no columns.")
                return frame
            except (UnicodeError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
                errors.append(exc)
        raise ValueError("The CSV could not be decoded or parsed.") from errors[-1]
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise HTTPException(status_code=415, detail="Only CSV and XLSX files are supported.")


def cleaned_copy(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = frame.copy()
    if config.get("drop_duplicates"):
        result = result.drop_duplicates()
    for column in config.get("drop_rows_with_missing", []):
        if column in result:
            result = result.dropna(subset=[column])
    for column, value in config.get("fill_missing", {}).items():
        if column in result:
            result[column] = result[column].fillna(value)
    return result
