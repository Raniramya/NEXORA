from pathlib import Path

import pandas as pd

from app.services.analytics import aggregate, percentage_change, top_bottom_entities
from app.services.datasets import read_dataset
from app.services.profiling import infer_column_type, profile_dataframe


def fixture_frame() -> pd.DataFrame:
    return pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-02"], "region": ["North", "South", "South"], "revenue": [100, 200, 200], "missing": [1, None, None]})


def test_csv_ingestion(tmp_path: Path) -> None:
    path = tmp_path / "tiny.csv"
    fixture_frame().to_csv(path, index=False)
    assert read_dataset(path).shape == (3, 4)


def test_csv_ingestion_accepts_excel_style_delimiters(tmp_path: Path) -> None:
    path = tmp_path / "regional-export.csv"
    path.write_text("region;revenue\nNorth;100\nSouth;200\n", encoding="utf-8-sig")
    frame = read_dataset(path)
    assert frame.columns.tolist() == ["region", "revenue"]
    assert frame.shape == (2, 2)


def test_type_inference_and_profile() -> None:
    profile = profile_dataframe(fixture_frame())
    assert infer_column_type(fixture_frame()["revenue"]) == "numeric"
    assert profile["columns"]["date"]["type"] == "datetime"
    assert profile["columns"]["missing"]["missing_count"] == 2
    assert profile["duplicate_count"] == 1
    assert 0 <= profile["quality_score"] <= 100


def test_analytics_aggregation() -> None:
    result = aggregate(fixture_frame(), "revenue", "sum", "region")
    assert {item["region"]: item["value"] for item in result} == {"North": 100.0, "South": 400.0}
    assert top_bottom_entities(fixture_frame(), "region", "revenue")[0]["region"] == "South"
    assert percentage_change(120, 100) == 20.0
