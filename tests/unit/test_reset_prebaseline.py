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
        self.deleted_keys: list[tuple[str, str]] = []

    def get_paginator(self, _name: str):
        return self

    def paginate(self, **_kwargs):
        return [{"Contents": [{"Key": "1/model/MLmodel"}, {"Key": "1/model/model.pkl"}]}]

    def download_file(self, bucket: str, key: str, destination: str) -> None:
        self.downloaded.append((bucket, key))
        Path(destination).write_text(key, encoding="utf-8")

    def delete_objects(self, **kwargs) -> None:
        self.deleted.append(kwargs)

    def delete_object(self, **kwargs) -> None:
        self.deleted_keys.append((kwargs["Bucket"], kwargs["Key"]))


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

    objects = reset.snapshot_mlflow_artifacts(client, "weather-mlops-mlflow", tmp_path)

    assert client.downloaded == [
        ("weather-mlops-mlflow", "1/model/MLmodel"),
        ("weather-mlops-mlflow", "1/model/model.pkl"),
    ]
    assert (tmp_path / "mlflow-s3/1/model/MLmodel").read_text(encoding="utf-8") == "1/model/MLmodel"
    assert client.deleted == []

    completed = reset.clear_mlflow_artifacts(
        client,
        "weather-mlops-mlflow",
        objects,
        tmp_path / "mlflow-s3/deleted.json",
        max_objects=1,
    )

    assert completed is False
    assert client.deleted_keys == [("weather-mlops-mlflow", "1/model/MLmodel")]
    assert client.deleted == []

    completed = reset.clear_mlflow_artifacts(
        client,
        "weather-mlops-mlflow",
        objects,
        tmp_path / "mlflow-s3/deleted.json",
        max_objects=10,
    )

    assert completed is True
    assert client.deleted_keys == [
        ("weather-mlops-mlflow", "1/model/MLmodel"),
        ("weather-mlops-mlflow", "1/model/model.pkl"),
    ]


def test_mlflow_snapshot_can_resume_after_an_incomplete_download(tmp_path) -> None:
    reset = _reset_module()
    (tmp_path / "mlflow-s3").mkdir()
    client = _S3()

    objects = reset.snapshot_mlflow_artifacts(client, "weather-mlops-mlflow", tmp_path)

    assert objects == ["1/model/MLmodel", "1/model/model.pkl"]
    assert (tmp_path / "mlflow-s3/objects.json").exists()


def test_local_artifacts_are_backed_up_before_removal(tmp_path) -> None:
    reset = _reset_module()
    project_root = tmp_path / "project"
    source = project_root / "models/best_model.joblib"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"candidate")
    backup_dir = tmp_path / "backup"

    reset.snapshot_local_artifacts(project_root, backup_dir)

    assert source.exists()
    assert (backup_dir / "local/models/best_model.joblib").read_bytes() == b"candidate"

    reset.remove_local_artifacts(project_root)

    assert not source.exists()


def test_reset_allows_only_an_explicit_resume_of_an_existing_backup(tmp_path) -> None:
    reset = _reset_module()
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    with pytest.raises(FileExistsError):
        reset.prepare_backup_dir(backup_dir, resume=False)

    assert reset.prepare_backup_dir(backup_dir, resume=True) == backup_dir
