from types import SimpleNamespace

import pandas as pd

from weather_mlops.data.database import (
    catalog_registered_model,
    dataframe_to_records,
    feature_schema_from_csv,
    log_serving_prediction,
    store_dataset_metadata,
    store_model_version,
    store_prediction,
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
        self.updates: list[dict] = []
        self.filters: list[tuple] = []

    def select(self, *_args, **_kwargs):
        self.mode = "select"
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def neq(self, field, value):
        self.filters.append(("neq", field, value))
        return self

    def limit(self, _n):
        return self

    def upsert(self, row, on_conflict=None):
        self.mode = "upsert"
        self.row = row
        self.on_conflict = on_conflict
        return self

    def insert(self, row):
        self.mode = "insert"
        self.row = row
        return self

    def update(self, row):
        self.mode = "update"
        self.updates.append(row)
        return self

    def execute(self):
        if self.mode == "select":
            return SimpleNamespace(data=self.existing)
        return self


class FakeClient:
    def __init__(self, existing=None, tables=None) -> None:
        self.table_name = None
        self.existing = existing or []
        self.tables_existing = tables or {}
        self.queries: dict[str, FakeQuery] = {}
        self.query = FakeQuery(existing=self.existing)

    def table(self, name: str) -> FakeQuery:
        self.table_name = name
        if name not in self.queries:
            existing = self.tables_existing.get(name, self.existing)
            self.queries[name] = FakeQuery(existing=existing)
        self.query = self.queries[name]
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


def test_store_dataset_metadata_rejects_conflicting_lineage() -> None:
    existing = [
        {
            "storage_uri": "s3://weather-mlops-dvc/processed/sha256/manifest.json",
            "created_at": "2026-01-01T00:00:00+00:00",
            "git_commit": "oldcommit",
            "preprocessing_version": "2026.09.01",
            "parent_sha256": "parent-a",
            "created_by": "preprocess",
            "source": "open-meteo",
            "version_kind": "processed",
        }
    ]
    client = FakeClient(existing=existing)
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path="data/processed",
        size_bytes=8,
        md5="md5",
        sha256="sha256",
        version_kind="processed",
        storage_uri="s3://weather-mlops-dvc/processed/sha256/manifest.json",
        git_commit="newcommit",
        parent_sha256="parent-b",
        created_by="preprocess",
    )

    try:
        store_dataset_metadata(metadata, client=client)
        raise AssertionError("conflicting lineage must fail")
    except ValueError as exc:
        assert "Catalog lineage conflict" in str(exc)
        assert "parent_sha256" in str(exc) or "git_commit" in str(exc)


def test_store_dataset_metadata_keeps_existing_object_bytes() -> None:
    existing = [
        {
            "storage_uri": "s3://weather-mlops-dvc/processed/sha256/manifest.json",
            "created_at": "2026-01-01T00:00:00+00:00",
            "git_commit": "abc123",
            "preprocessing_version": "2026.09.01",
            "parent_sha256": "parent-a",
            "created_by": "preprocess",
            "source": "open-meteo",
            "version_kind": "processed",
            "path": "data/processed/first-run",
            "size_bytes": 42,
            "md5": "original-md5",
        }
    ]
    client = FakeClient(existing=existing)
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path="data/processed/second-run",
        size_bytes=99,
        md5="second-md5",
        sha256="sha256",
        version_kind="processed",
        storage_uri="s3://weather-mlops-dvc/processed/sha256/manifest.json",
        git_commit="abc123",
        parent_sha256="parent-a",
        created_by="preprocess",
    )

    store_dataset_metadata(metadata, client=client)

    assert client.query.row["path"] == "data/processed/first-run"
    assert client.query.row["size_bytes"] == 42
    assert client.query.row["md5"] == "original-md5"
    assert client.query.row["git_commit"] == "abc123"


def test_feature_schema_from_csv_records_columns_and_dtypes(tmp_path) -> None:
    path = tmp_path / "X_train.csv"
    path.write_text("Location,MinTemp,RainToday\nSydney,12.0,No\n", encoding="utf-8")

    schema = feature_schema_from_csv(path)

    assert schema is not None
    assert schema["columns"] == ["Location", "MinTemp", "RainToday"]
    assert "float" in schema["dtypes"]["MinTemp"]
    assert schema["dtypes"]["Location"]


def test_feature_schema_from_csv_is_none_when_file_missing(tmp_path) -> None:
    assert feature_schema_from_csv(tmp_path / "missing.csv") is None


def test_store_model_version_upserts_on_mlflow_run_id() -> None:
    client = FakeClient()

    store_model_version(
        {
            "mlflow_run_id": "run-1",
            "mlflow_model_uri": "models:/weather-rainfall-classifier/1",
            "dataset_sha256": "abc",
            "name": "weather-rainfall-classifier",
            "stage": "candidate",
            "metrics": {"validation_roc_auc": 0.88},
            "params": {"max_depth": 4},
            "feature_schema": {"columns": ["Location"]},
        },
        client=client,
    )

    assert client.table_name == "model_versions"
    assert client.query.on_conflict == "mlflow_run_id"
    assert client.query.row["mlflow_run_id"] == "run-1"
    assert client.query.row["stage"] == "candidate"
    assert client.query.row["dataset_sha256"] == "abc"
    assert client.query.row["feature_schema"]["columns"] == ["Location"]
    assert client.query.updates == []


def test_store_model_version_demotes_previous_champion() -> None:
    client = FakeClient()

    store_model_version(
        {
            "mlflow_run_id": "run-2",
            "name": "weather-rainfall-classifier",
            "stage": "champion",
        },
        client=client,
    )

    assert client.query.updates == [{"stage": "previous"}]
    assert ("eq", "stage", "champion") in client.query.filters
    assert ("neq", "mlflow_run_id", "run-2") in client.query.filters


def test_catalog_registered_model_stores_version_for_lookup() -> None:
    client = FakeClient()

    catalog_registered_model(
        run_id="run-9",
        model_version="4",
        model_uri="models:/weather-rainfall-classifier/4",
        dataset_sha256="data-sha",
        params={"max_depth": 4},
        metrics={"train_roc_auc": 0.81},
        stage="candidate",
        client=client,
    )

    assert client.query.row["mlflow_run_id"] == "run-9"
    assert client.query.row["mlflow_model_version"] == "4"
    assert client.query.row["stage"] == "candidate"
    assert client.query.row["mlflow_model_uri"].endswith("/4")


def test_store_prediction_inserts_serving_row() -> None:
    client = FakeClient()

    store_prediction(
        {
            "model_version_id": 7,
            "features": {"Location": "Sydney", "MinTemp": 12.0},
            "predicted_class": "No",
            "probability": 0.12,
            "observation_date": "2026-09-16",
            "location": "Sydney",
            "endpoint": "predict",
            "latency_ms": 8,
        },
        client=client,
    )

    assert client.table_name == "predictions"
    assert client.query.row["endpoint"] == "predict"
    assert client.query.row["location"] == "Sydney"
    assert client.query.row["model_version_id"] == 7
    assert client.query.row["probability"] == 0.12
    assert client.query.on_conflict is None


def test_log_serving_prediction_links_model_version_and_endpoint() -> None:
    client = FakeClient(tables={"model_versions": [{"id": 7}]})

    log_serving_prediction(
        endpoint="live_data",
        features={"Location": "Sydney", "MinTemp": 18.0},
        result={
            "rain_tomorrow": True,
            "probability": 0.81,
            "model": {
                "name": "weather-rainfall-classifier",
                "version": "3",
                "alias": "champion",
            },
        },
        observation_date="2026-09-16",
        location="Sydney",
        latency_ms=11,
        client=client,
    )

    row = client.queries["predictions"].row
    assert row["endpoint"] == "live_data"
    assert row["model_version_id"] == 7
    assert row["predicted_class"] == "Yes"
    assert row["observation_date"] == "2026-09-16"
    assert ("eq", "mlflow_model_version", "3") in client.queries["model_versions"].filters


def test_log_serving_prediction_does_not_raise_when_catalog_fails() -> None:
    class Boom:
        def table(self, _name):
            raise RuntimeError("supabase down")

    log_serving_prediction(
        endpoint="predict",
        features={"Location": "Sydney"},
        result={"rain_tomorrow": False, "probability": 0.1, "model": {}},
        location="Sydney",
        client=Boom(),
    )
