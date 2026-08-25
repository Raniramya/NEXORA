from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: str
    filename: str
    original_filename: str
    row_count: int
    column_count: int
    uploaded_at: datetime
    processing_status: str
    quality_score: float

    model_config = {"from_attributes": True}


class DatasetDetail(DatasetSummary):
    profile: dict[str, Any]


class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]


class CleanedDatasetRequest(BaseModel):
    drop_duplicates: bool = False
    drop_rows_with_missing: list[str] = Field(default_factory=list)
    fill_missing: dict[str, Any] = Field(default_factory=dict)


class AnalyticsRequest(BaseModel):
    measure: str
    aggregation: str = "sum"
    dimension: str | None = None
    date_column: str | None = None
    filters: dict[str, list[str]] = Field(default_factory=dict)
