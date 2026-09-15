from types import SimpleNamespace

from weather_mlops.data.manifest import (
    PROCESSED_FILES,
    build_processed_manifest,
    write_processed_manifest,
)
from weather_mlops.data.snapshots import (
    register_local_snapshot,
    register_processed_snapshot,
    snapshot_object_key,
    snapshot_uri,
    upload_snapshot,
)
from weather_mlops.data.versioning import DatasetMetadata, hash_file


class FakeStorage:
    def __init__(self, error: Exception | None = None) -> None:
        self.uploads: list[tuple[str, str]] = []
        self.error = error

    def from_(self, bucket: str):
        self.bucket = bucket
        return self

    def upload(self, object_key: str, _data: bytes, _options: dict) -> None:
        if self.error is not None:
            raise self.error
        self.uploads.append((self.bucket, object_key))


def test_snapshot_uri_is_content_addressed() -> None:
    uri = snapshot_uri(
        kind="processed",
        sha256="abc123",
        filename="X_train.csv",
        bucket="weather-mlops-dvc",
    )

    assert uri == "s3://weather-mlops-dvc/processed/abc123/X_train.csv"


def test_snapshot_object_key_keeps_raw_and_processed_apart() -> None:
    raw_key = snapshot_object_key("raw", "aaa", "weatherAUS_current.csv")
    processed_key = snapshot_object_key("processed", "bbb", "X_train.csv")

    assert raw_key.startswith("raw/")
    assert processed_key.startswith("processed/")
    assert raw_key != processed_key


def test_upload_snapshot_writes_hash_keyed_object(tmp_path) -> None:
    path = tmp_path / "weatherAUS_current.csv"
    path.write_text("Date,Location\n2026-01-01,Sydney\n", encoding="utf-8")
    storage = FakeStorage()
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path=str(path),
        size_bytes=path.stat().st_size,
        md5="m",
        sha256="abc123",
        version_kind="raw",
        storage_uri="s3://weather-mlops-dvc/raw/abc123/weatherAUS_current.csv",
    )

    uri = upload_snapshot(path, metadata, client=storage)

    assert uri == metadata.storage_uri
    assert storage.uploads == [("weather-mlops-dvc", "raw/abc123/weatherAUS_current.csv")]


def test_upload_snapshot_ignores_duplicate_object(tmp_path) -> None:
    path = tmp_path / "weatherAUS_current.csv"
    path.write_text("Date,Location\n2026-01-01,Sydney\n", encoding="utf-8")
    duplicate = Exception("Duplicate")
    duplicate.status = 409  # type: ignore[attr-defined]
    storage = FakeStorage(error=duplicate)
    metadata = DatasetMetadata(
        dataset_name="weatherAUS",
        path=str(path),
        size_bytes=1,
        md5="m",
        sha256="abc123",
        version_kind="raw",
        storage_uri="s3://weather-mlops-dvc/raw/abc123/weatherAUS_current.csv",
    )

    uri = upload_snapshot(path, metadata, client=storage)

    assert uri == metadata.storage_uri


def test_register_local_snapshot_dry_run_does_not_upload(tmp_path) -> None:
    path = tmp_path / "weatherAUS_current.csv"
    path.write_text("Date,Location\n2026-01-01,Sydney\n", encoding="utf-8")
    storage = FakeStorage()

    metadata = register_local_snapshot(path, dry_run=True, storage_client=storage)

    assert metadata.storage_uri is not None
    assert "raw/" in metadata.storage_uri
    assert storage.uploads == []


class FakeCatalog:
    def __init__(self) -> None:
        self.row = None
        self.mode = "upsert"

    def table(self, _name):
        return self

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
        return self

    def execute(self):
        if self.mode == "select":
            return SimpleNamespace(data=[])
        return self


def test_register_processed_snapshot_uses_combined_hash_and_uploads_csvs(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    storage = FakeStorage()
    catalog = FakeCatalog()

    metadata = register_processed_snapshot(
        tmp_path,
        created_by="test",
        storage_client=storage,
        catalog_client=catalog,
    )

    json_sha = hash_file(tmp_path / "manifest.json", "sha256")
    uploaded_names = {key.split("/")[-1] for _bucket, key in storage.uploads}

    assert metadata.sha256 == manifest["sha256"]
    assert metadata.sha256 != json_sha
    assert metadata.parent_sha256 == "rawsha"
    assert metadata.storage_uri.endswith(f"processed/{manifest['sha256']}/manifest.json")
    assert uploaded_names == {*PROCESSED_FILES, "manifest.json"}
    assert catalog.row["sha256"] == manifest["sha256"]
