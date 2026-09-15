from dataclasses import replace
from pathlib import Path

from weather_mlops.config.settings import settings
from weather_mlops.data.catalog import build_catalog_record, current_git_commit
from weather_mlops.data.versioning import (
    DatasetMetadata,
    build_dataset_metadata,
    display_path,
    hash_file,
)

RAW_KIND = "raw"
PROCESSED_KIND = "processed"


def snapshot_object_key(kind: str, sha256: str, filename: str) -> str:
    return f"{kind}/{sha256}/{filename}"


def snapshot_uri(
    kind: str,
    sha256: str,
    filename: str,
    bucket: str | None = None,
) -> str:
    bucket_name = bucket or settings.supabase_datasets_bucket
    return f"s3://{bucket_name}/{snapshot_object_key(kind, sha256, filename)}"


def build_snapshot_metadata(
    path: Path,
    *,
    kind: str = RAW_KIND,
    dataset_name: str = "weatherAUS",
    created_by: str = "local",
    parent_sha256: str | None = None,
    source: str = "weatherAUS",
    preprocessing_version: str | None = None,
    bucket: str | None = None,
) -> DatasetMetadata:
    metadata = build_dataset_metadata(path, dataset_name=dataset_name)
    return build_catalog_record(
        metadata,
        version_kind=kind,
        storage_uri=snapshot_uri(kind, metadata.sha256, path.name, bucket=bucket),
        git_commit=current_git_commit(),
        preprocessing_version=preprocessing_version,
        parent_sha256=parent_sha256,
        source=source,
        created_by=created_by,
    )


def upload_snapshot(
    path: Path,
    metadata: DatasetMetadata,
    *,
    client=None,
    bucket: str | None = None,
) -> str:
    """Upload an immutable snapshot. The object key includes the content hash.

    A second upload of the same hash is a no-op: the object is already the
    snapshot. Callers still write the catalog row afterwards.
    """

    if metadata.storage_uri is None:
        raise ValueError("Dataset metadata is missing storage_uri.")

    bucket_name = bucket or settings.supabase_datasets_bucket
    object_key = snapshot_object_key(metadata.version_kind, metadata.sha256, path.name)
    storage = client or _storage_client()
    try:
        storage.from_(bucket_name).upload(
            object_key,
            path.read_bytes(),
            {"content-type": "application/octet-stream", "upsert": "false"},
        )
    except Exception as exc:  # noqa: BLE001 - Storage client raises several types
        if not _already_stored(exc):
            raise
    return metadata.storage_uri


def register_local_snapshot(
    path: Path,
    *,
    kind: str = RAW_KIND,
    created_by: str = "local",
    parent_sha256: str | None = None,
    source: str = "weatherAUS",
    preprocessing_version: str | None = None,
    dry_run: bool = False,
    storage_client=None,
    catalog_client=None,
) -> DatasetMetadata:
    """Hash a local file, upload it if needed, and upsert dataset_versions.

    This is the one helper Airflow should call later. DVC still feeds a
    developer checkout; this path is the catalog + immutable copy.
    """

    from weather_mlops.data.database import store_dataset_metadata

    metadata = build_snapshot_metadata(
        path,
        kind=kind,
        created_by=created_by,
        parent_sha256=parent_sha256,
        source=source,
        preprocessing_version=preprocessing_version,
    )
    if dry_run:
        return metadata
    upload_snapshot(path, metadata, client=storage_client)
    store_dataset_metadata(metadata, client=catalog_client)
    return metadata


def _processed_dir(path: Path | None) -> Path:
    if path is None:
        return settings.processed_data_dir
    if path.is_dir():
        return path
    return path.parent


def register_processed_snapshot(
    path: Path | None = None,
    *,
    created_by: str = "local",
    source: str = "weatherAUS",
    dry_run: bool = False,
    storage_client=None,
    catalog_client=None,
) -> DatasetMetadata:
    """Upload the six splits plus manifest under one combined-hash identity.

    Catalog `sha256` matches training's `dataset_sha256`. Parent hash and
    preprocess version come from the verified manifest, not the current raw
    file or running code.
    """

    from weather_mlops.data.database import store_dataset_metadata
    from weather_mlops.data.manifest import PROCESSED_FILES, verify_processed_manifest

    output_dir = _processed_dir(path)
    manifest_path = output_dir / "manifest.json"
    manifest = verify_processed_manifest(output_dir)
    dataset_sha = manifest["sha256"]
    metadata = DatasetMetadata(
        dataset_name=str(manifest.get("dataset_name") or "weatherAUS"),
        path=str(manifest.get("path") or display_path(manifest_path)),
        size_bytes=manifest_path.stat().st_size,
        md5=hash_file(manifest_path, "md5"),
        sha256=dataset_sha,
        version_kind=PROCESSED_KIND,
        storage_uri=snapshot_uri(PROCESSED_KIND, dataset_sha, "manifest.json"),
        git_commit=manifest.get("git_commit"),
        preprocessing_version=manifest.get("preprocessing_version"),
        parent_sha256=manifest.get("parent_sha256"),
        source=source,
        created_by=created_by,
    )
    if dry_run:
        return metadata

    for filename in (*PROCESSED_FILES, "manifest.json"):
        file_path = output_dir / filename
        file_meta = replace(
            metadata,
            storage_uri=snapshot_uri(PROCESSED_KIND, dataset_sha, filename),
        )
        upload_snapshot(file_path, file_meta, client=storage_client)
    store_dataset_metadata(metadata, client=catalog_client)
    return metadata


def _already_stored(exc: Exception) -> bool:
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    text = str(getattr(exc, "message", exc)).lower()
    return status == 409 or "duplicate" in text or "already exists" in text


def _storage_client():
    from weather_mlops.data.database import get_supabase_client

    return get_supabase_client().storage
