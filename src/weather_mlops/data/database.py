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
            on_conflict="date,location",
        ).execute()

    return len(records)


def _existing_dataset_row(client: Client, dataset_name: str, sha256: str) -> dict[str, Any] | None:
    response = (
        client.table(settings.supabase_dataset_versions_table)
        .select(
            "storage_uri,created_at,git_commit,preprocessing_version,"
            "parent_sha256,created_by,source,version_kind"
        )
        .eq("dataset_name", dataset_name)
        .eq("sha256", sha256)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def store_dataset_metadata(
    metadata: DatasetMetadata,
    client: Client | None = None,
) -> None:
    """Upsert catalog identity. Never replace a stored URI with null.

    Repeat loads keep the original created_at and fill only blank lineage
    fields. Snapshot registration remains the source of storage_uri.
    """

    supabase = client or get_supabase_client()
    payload: dict[str, Any] = {
        "dataset_name": metadata.dataset_name,
        "path": metadata.path,
        "size_bytes": metadata.size_bytes,
        "md5": metadata.md5,
        "sha256": metadata.sha256,
        "created_at": metadata.created_at or datetime.now(UTC).isoformat(),
        "version_kind": metadata.version_kind,
        "storage_uri": metadata.storage_uri,
        "git_commit": metadata.git_commit,
        "preprocessing_version": metadata.preprocessing_version,
        "parent_sha256": metadata.parent_sha256,
        "source": metadata.source,
        "created_by": metadata.created_by,
    }
    existing = _existing_dataset_row(supabase, metadata.dataset_name, metadata.sha256)
    if existing:
        if existing.get("created_at"):
            payload["created_at"] = existing["created_at"]
        for field in (
            "storage_uri",
            "git_commit",
            "preprocessing_version",
            "parent_sha256",
            "created_by",
            "source",
            "version_kind",
        ):
            if not payload.get(field) and existing.get(field):
                payload[field] = existing[field]

    supabase.table(settings.supabase_dataset_versions_table).upsert(
        payload,
        on_conflict="dataset_name,sha256",
    ).execute()


def store_ingestion_batch(
    *,
    batch_date: str,
    storage_uri: str,
    sha256: str,
    location_count: int | None = None,
    source: str = "open-meteo",
    git_commit: str | None = None,
    client: Client | None = None,
) -> None:
    supabase = client or get_supabase_client()
    supabase.table(settings.supabase_ingestion_batches_table).upsert(
        {
            "batch_date": batch_date,
            "location_count": location_count,
            "storage_uri": storage_uri,
            "sha256": sha256,
            "source": source,
            "git_commit": git_commit,
        },
        on_conflict="batch_date,sha256",
    ).execute()
