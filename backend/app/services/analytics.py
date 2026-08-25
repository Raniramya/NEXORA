import pandas as pd


def apply_filters(frame: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    result = frame.copy()
    for column, values in filters.items():
        if column in result and values:
            result = result[result[column].astype(str).isin(values)]
    return result


def aggregate(frame: pd.DataFrame, measure: str, aggregation: str, dimension: str | None = None) -> list[dict]:
    if measure not in frame:
        raise ValueError("Unknown measure")
    functions = {"sum": "sum", "mean": "mean", "min": "min", "max": "max", "count": "count"}
    if aggregation not in functions:
        raise ValueError("Unsupported aggregation")
    numeric = pd.to_numeric(frame[measure], errors="coerce")
    working = frame.assign(_measure=numeric)
    if dimension:
        if dimension not in working:
            raise ValueError("Unknown dimension")
        result = working.groupby(dimension, dropna=False)["_measure"].agg(functions[aggregation]).reset_index()
        return [{dimension: None if pd.isna(row[dimension]) else str(row[dimension]), "value": float(row["_measure"])} for _, row in result.iterrows()]
    value = getattr(working["_measure"], functions[aggregation])()
    return [{"value": float(value) if pd.notna(value) else 0.0}]


def time_trend(frame: pd.DataFrame, date_column: str, measure: str, aggregation: str) -> list[dict]:
    if date_column not in frame:
        raise ValueError("Unknown date column")
    dated = frame.assign(_date=pd.to_datetime(frame[date_column], errors="coerce")).dropna(subset=["_date"])
    dated["period"] = dated["_date"].dt.to_period("M").astype(str)
    return aggregate(dated, measure, aggregation, "period")


def top_bottom_entities(frame: pd.DataFrame, dimension: str, measure: str, limit: int = 10, ascending: bool = False) -> list[dict]:
    result = aggregate(frame, measure, "sum", dimension)
    return sorted(result, key=lambda item: item["value"], reverse=not ascending)[:limit]


def percentage_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)
