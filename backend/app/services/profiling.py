from typing import Any

import numpy as np
import pandas as pd


def infer_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if non_null.empty:
        return "unknown"
    parsed_dates = pd.to_datetime(non_null, errors="coerce")
    if len(non_null) and parsed_dates.notna().mean() >= 0.9:
        return "datetime"
    return "categorical"


def _safe(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if pd.isna(value):
        return None
    return value


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    numeric_columns: list[str] = []
    for name in frame.columns:
        series = frame[name]
        inferred = infer_column_type(series)
        entry: dict[str, Any] = {
            "type": inferred,
            "missing_count": int(series.isna().sum()),
            "missing_percent": round(float(series.isna().mean() * 100), 2),
            "unique_count": int(series.nunique(dropna=True)),
        }
        if inferred == "numeric":
            numeric_columns.append(name)
            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = series[(series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)] if iqr > 0 else series.iloc[0:0]
            entry["numeric_summary"] = {key: _safe(value) for key, value in series.describe().to_dict().items()}
            entry["outlier_count"] = int(outliers.count())
        elif inferred == "categorical":
            entry["categorical_summary"] = {str(key): int(value) for key, value in series.value_counts(dropna=True).head(10).items()}
        elif inferred == "datetime":
            parsed = pd.to_datetime(series, errors="coerce")
            entry["date_range"] = {"min": parsed.min().isoformat() if parsed.notna().any() else None, "max": parsed.max().isoformat() if parsed.notna().any() else None}
        columns[str(name)] = entry
    duplicates = int(frame.duplicated().sum())
    missing_ratio = float(frame.isna().mean().mean()) if len(frame.columns) else 1.0
    duplicate_ratio = duplicates / len(frame) if len(frame) else 0.0
    quality = round(max(0.0, 100 * (1 - 0.7 * missing_ratio - 0.3 * duplicate_ratio)), 2)
    correlation = frame[numeric_columns].corr().round(4).replace({np.nan: None}).to_dict() if len(numeric_columns) >= 2 else {}
    return {"columns": columns, "duplicate_count": duplicates, "correlation": correlation, "quality_score": quality}
