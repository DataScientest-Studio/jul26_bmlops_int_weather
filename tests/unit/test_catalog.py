from weather_mlops.data.catalog import (
    PREPROCESS_VERSION,
    build_catalog_record,
    current_git_commit,
)
from weather_mlops.data.versioning import DatasetMetadata, build_dataset_metadata


def test_build_catalog_record_adds_lineage_fields(tmp_path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("a,b\n1,2\n", encoding="utf-8")
    metadata = build_dataset_metadata(dataset)

    record = build_catalog_record(
        metadata,
        version_kind="processed",
        storage_uri="s3://weather-mlops-datasets/processed/abc/dataset.csv",
        git_commit="deadbeef",
        preprocessing_version=PREPROCESS_VERSION,
        parent_sha256="parent",
        source="open-meteo",
        created_by="airflow",
    )

    assert record.version_kind == "processed"
    assert record.storage_uri.endswith("dataset.csv")
    assert record.git_commit == "deadbeef"
    assert record.preprocessing_version == PREPROCESS_VERSION
    assert record.parent_sha256 == "parent"
    assert record.source == "open-meteo"
    assert record.created_by == "airflow"
    assert record.sha256 == metadata.sha256


def test_raw_catalog_record_defaults_are_stable(tmp_path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("a,b\n1,2\n", encoding="utf-8")
    metadata = build_dataset_metadata(dataset)

    record = build_catalog_record(metadata)

    assert record.version_kind == "raw"
    assert record.created_by == "local"
    assert isinstance(record, DatasetMetadata)


def test_current_git_commit_is_hex_or_none() -> None:
    commit = current_git_commit()
    if commit is None:
        return
    sha = commit.removesuffix("-dirty")
    assert len(sha) == 40
    assert all(char in "0123456789abcdef" for char in sha)


def test_current_git_commit_prefers_environment(monkeypatch) -> None:
    monkeypatch.setenv("GIT_COMMIT", "abc123-image")

    assert current_git_commit() == "abc123-image"


def test_current_git_commit_ignores_placeholder_environment(monkeypatch) -> None:
    monkeypatch.setenv("GIT_COMMIT", "-dirty")
    monkeypatch.setattr(
        "weather_mlops.data.catalog.subprocess.run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 1, "stdout": ""})(),
    )

    assert current_git_commit() is None
