from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from supabase import Client, create_client
from weather_mlops.config.settings import settings
from weather_mlops.data.versioning import DatasetMetadata

COLUMN_RENAMES = {
    "Date": "date",
    "Location": "location",
    "MinTemp": "min_temp",
    "MaxTemp": "max_temp",
    "Rainfall": "rainfall",
    "Evaporation": "evaporation",
    "Sunshine": "sunshine",
    "WindGustDir": "wind_gust_dir",
    "WindGustSpeed": "wind_gust_speed",
    "WindDir9am": "wind_dir_9am",
    "WindDir3pm": "wind_dir_3pm",
    "WindSpeed9am": "wind_speed_9am",
    "WindSpeed3pm": "wind_speed_3pm",
    "Humidity9am": "humidity_9am",
    "Humidity3pm": "humidity_3pm",
    "Pressure9am": "pressure_9am",
    "Pressure3pm": "pressure_3pm",
    "Cloud9am": "cloud_9am",
    "Cloud3pm": "cloud_3pm",
    "Temp9am": "temp_9am",
    "Temp3pm": "temp_3pm",
    "RainToday": "rain_today",
    "RainTomorrow": "rain_tomorrow",
}


def get_supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env.")

    return create_client(settings.supabase_url, settings.supabase_key)


def expected_weather_columns() -> list[str]:
    return ["source_row_number", *COLUMN_RENAMES.values()]


def normalize_weather_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = set(COLUMN_RENAMES) - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")

    normalized = df.rename(columns=COLUMN_RENAMES).copy()
    normalized.insert(0, "source_row_number", range(1, len(normalized) + 1))
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    return normalized


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    normalized = normalize_weather_dataframe(df)
    normalized = normalized.astype(object).where(pd.notna(normalized), None)

    return normalized.to_dict(orient="records")


def chunk_records(
    records: list[dict[str, Any]],
    batch_size: int,
) -> Iterable[list[dict[str, Any]]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")

    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def store_weather_observations(
    df: pd.DataFrame,
    batch_size: int = 1000,
    client: Client | None = None,
) -> int:
    supabase = client or get_supabase_client()
    records = dataframe_to_records(df)

    for batch in chunk_records(records, batch_size):
        supabase.table(settings.supabase_weather_table).upsert(
            batch,
            on_conflict="source_row_number",
        ).execute()

    return len(records)


def store_dataset_metadata(
    metadata: DatasetMetadata,
    client: Client | None = None,
) -> None:
    supabase = client or get_supabase_client()
    supabase.table(settings.supabase_dataset_versions_table).upsert(
        {
            "dataset_name": metadata.dataset_name,
            "path": metadata.path,
            "size_bytes": metadata.size_bytes,
            "md5": metadata.md5,
            "sha256": metadata.sha256,
            "created_at": metadata.created_at or datetime.now(UTC).isoformat(),
        },
        on_conflict="dataset_name,sha256",
    ).execute()
