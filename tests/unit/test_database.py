from types import SimpleNamespace

import pandas as pd

from weather_mlops.data.database import (
    dataframe_to_records,
    store_dataset_metadata,
    store_weather_observations,
)
from weather_mlops.data.versioning import DatasetMetadata


def test_dataframe_to_records_normalizes_weather_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": ["2020-01-01"],
            "Location": ["Sydney"],
            "MinTemp": [12.0],
            "MaxTemp": [23.0],
            "Rainfall": [0.0],
            "Evaporation": [None],
            "Sunshine": [8.0],
            "WindGustDir": ["W"],
            "WindGustSpeed": [31.0],
            "WindDir9am": ["N"],
            "WindDir3pm": ["W"],
            "WindSpeed9am": [10.0],
            "WindSpeed3pm": [13.0],
            "Humidity9am": [71.0],
            "Humidity3pm": [42.0],
            "Pressure9am": [1012.0],
            "Pressure3pm": [1009.0],
            "Cloud9am": [2.0],
            "Cloud3pm": [3.0],
            "Temp9am": [17.0],
            "Temp3pm": [21.0],
            "RainToday": ["No"],
            "RainTomorrow": ["Yes"],
        }
    )

    records = dataframe_to_records(dataframe)

    assert records[0]["source_row_number"] == 1
    assert records[0]["date"] == "2020-01-01"
    assert records[0]["min_temp"] == 12.0
    assert records[0]["evaporation"] is None
    assert records[0]["rain_tomorrow"] == "Yes"


def test_store_weather_observations_upserts_on_date_and_location() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": ["2020-01-01"],
            "Location": ["Sydney"],
            "MinTemp": [12.0],
            "MaxTemp": [23.0],
            "Rainfall": [0.0],
            "Evaporation": [None],
            "Sunshine": [8.0],
            "WindGustDir": ["W"],
            "WindGustSpeed": [31.0],
            "WindDir9am": ["N"],
            "WindDir3pm": ["W"],
            "WindSpeed9am": [10.0],
            "WindSpeed3pm": [13.0],
            "Humidity9am": [71.0],
            "Humidity3pm": [42.0],
            "Pressure9am": [1012.0],
            "Pressure3pm": [1009.0],
            "Cloud9am": [2.0],
            "Cloud3pm": [3.0],
            "Temp9am": [17.0],
            "Temp3pm": [21.0],
            "RainToday": ["No"],
            "RainTomorrow": ["Yes"],
        }
    )
    client = FakeClient()

    stored = store_weather_observations(dataframe, client=client)

    assert stored == 1
    assert client.query.on_conflict == "date,location"


class FakeQuery:
    def __init__(self, existing=None) -> None:
        self.row = None
        self.on_conflict = None
        self.existing = existing or []
        self.mode = "upsert"

    def select(self, *_args, **_kwargs):
        self.mode = "select"
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    def upsert(self, row, on_conflict=None):
        self.mode = "upsert"
        self.row = row
        self.on_conflict = on_conflict
        return self

    def execute(self):
        if self.mode == "select":
            return SimpleNamespace(data=self.existing)
        return self


class FakeClient:
    def __init__(self, existing=None) -> None:
        self.table_name = None
        self.query = FakeQuery(existing=existing)

    def table(self, name: str) -> FakeQuery:
        self.table_name = name
        return self.query


def test_store_dataset_metadata_writes_lineage_columns() -> None:
    client = FakeClient()
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path="data/raw/weatherAUS_current.csv",
        size_bytes=8,
        md5="md5",
        sha256="sha256",
        version_kind="processed",
        storage_uri="s3://weather-mlops-datasets/processed/sha256/file.csv",
        git_commit="abc123",
        preprocessing_version="2026.09.15",
        parent_sha256="parent",
        source="open-meteo",
        created_by="airflow",
    )

    store_dataset_metadata(metadata, client=client)

    assert client.table_name == "dataset_versions"
    assert client.query.row["version_kind"] == "processed"
    assert client.query.row["git_commit"] == "abc123"
    assert client.query.row["preprocessing_version"] == "2026.09.15"
    assert client.query.row["storage_uri"].startswith("s3://")
    assert client.query.on_conflict == "dataset_name,sha256"


def test_store_dataset_metadata_does_not_null_out_storage_uri() -> None:
    existing = [
        {
            "storage_uri": "s3://weather-mlops-dvc/raw/sha256/file.csv",
            "created_at": "2026-01-01T00:00:00+00:00",
            "git_commit": "abc123",
            "preprocessing_version": None,
            "parent_sha256": None,
            "created_by": "register",
            "source": "weatherAUS",
            "version_kind": "raw",
        }
    ]
    client = FakeClient(existing=existing)
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path="data/raw/weatherAUS_current.csv",
        size_bytes=8,
        md5="md5",
        sha256="sha256",
        created_by="load_to_supabase",
    )

    store_dataset_metadata(metadata, client=client)

    assert client.query.row["storage_uri"] == "s3://weather-mlops-dvc/raw/sha256/file.csv"
    assert client.query.row["created_at"] == "2026-01-01T00:00:00+00:00"
    assert client.query.row["git_commit"] == "abc123"
    assert client.query.row["created_by"] == "load_to_supabase"
