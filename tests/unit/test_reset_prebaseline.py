import importlib.util
from pathlib import Path

import pytest


def _reset_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts/reset_prebaseline.py"
    if not script_path.exists():
        pytest.fail("scripts/reset_prebaseline.py is required for the pre-baseline reset")
    spec = importlib.util.spec_from_file_location("reset_prebaseline", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Connection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


class _S3:
    def __init__(self) -> None:
        self.downloaded: list[tuple[str, str]] = []
        self.deleted: list[dict] = []

    def get_paginator(self, _name: str):
        return self

    def paginate(self, **_kwargs):
        return [{"Contents": [{"Key": "1/model/MLmodel"}, {"Key": "1/model/model.pkl"}]}]

    def download_file(self, bucket: str, key: str, destination: str) -> None:
        self.downloaded.append((bucket, key))
        Path(destination).write_text(key, encoding="utf-8")

    def delete_objects(self, **kwargs) -> None:
        self.deleted.append(kwargs)


def test_reset_catalog_clears_only_experimental_lineage_tables() -> None:
    reset = _reset_module()
    connection = _Connection()

    reset.reset_catalog(connection)

    assert connection.statements == [
        "TRUNCATE TABLE public.predictions, public.drift_reports, public.model_versions, "
        "public.dataset_versions, public.ingestion_batches RESTART IDENTITY;"
    ]


def test_reset_preserves_raw_sources_and_the_singapore_fixture() -> None:
    reset = _reset_module()
    paths = {str(path) for path in reset.LOCAL_RESET_PATHS}

    assert "data/raw/weatherAUS.csv" not in paths
    assert "data/raw/weatherSingapore_current.csv" not in paths
    assert "data/raw/weatherAUS_current.csv" in paths
    assert "models/best_model.joblib" in paths
    assert "reports/mlflow_run.json" in paths


def test_reset_requires_an_explicit_confirmation_token() -> None:
    reset = _reset_module()
    with pytest.raises(ValueError, match="confirmation"):
        reset.require_confirmation("wrong")

    reset.require_confirmation(reset.CONFIRMATION_TOKEN)


def test_reset_archives_then_deletes_mlflow_artifacts(tmp_path) -> None:
    reset = _reset_module()
    client = _S3()

    reset.snapshot_and_clear_mlflow_artifacts(client, "weather-mlops-mlflow", tmp_path)

    assert client.downloaded == [
        ("weather-mlops-mlflow", "1/model/MLmodel"),
        ("weather-mlops-mlflow", "1/model/model.pkl"),
    ]
    assert (tmp_path / "mlflow-s3/1/model/MLmodel").read_text(encoding="utf-8") == "1/model/MLmodel"
    assert client.deleted == [
        {
            "Bucket": "weather-mlops-mlflow",
            "Delete": {
                "Objects": [
                    {"Key": "1/model/MLmodel"},
                    {"Key": "1/model/model.pkl"},
                ]
            },
        }
    ]
