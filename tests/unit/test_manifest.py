import pytest

from weather_mlops.data.manifest import (
    PROCESSED_FILES,
    build_processed_manifest,
    read_processed_manifest,
    verify_processed_manifest,
    write_processed_manifest,
)


def _write_splits(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")


def test_processed_manifest_hashes_all_six_splits(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")

    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    path = write_processed_manifest(manifest, tmp_path / "manifest.json")

    assert set(manifest["files"]) == set(PROCESSED_FILES)
    assert manifest["parent_sha256"] == "rawsha"
    assert manifest["preprocessing_version"]
    loaded = read_processed_manifest(path)
    assert loaded is not None
    assert loaded["sha256"] == manifest["sha256"]


def test_verify_processed_manifest_rejects_stale_csv(tmp_path) -> None:
    _write_splits(tmp_path)
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    (tmp_path / "X_train.csv").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not match"):
        verify_processed_manifest(tmp_path)


def test_verify_processed_manifest_requires_the_json_file(tmp_path) -> None:
    _write_splits(tmp_path)

    with pytest.raises(FileNotFoundError, match="manifest"):
        verify_processed_manifest(tmp_path)
