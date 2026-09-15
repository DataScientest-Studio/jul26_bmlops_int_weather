import pytest

from weather_mlops.data.manifest import (
    PROCESSED_FILES,
    build_processed_manifest,
    write_processed_manifest,
)
from weather_mlops.models.training import load_verified_training_inputs


def test_load_verified_training_inputs_rejects_stale_csv(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    (tmp_path / "X_train.csv").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not match"):
        load_verified_training_inputs(tmp_path / "X_train.csv", tmp_path / "y_train.csv")


def test_load_verified_training_inputs_requires_manifest(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="manifest"):
        load_verified_training_inputs(tmp_path / "X_train.csv", tmp_path / "y_train.csv")


def test_load_verified_training_inputs_returns_stored_identity(tmp_path) -> None:
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")

    x_path, y_path, verified = load_verified_training_inputs(
        tmp_path / "X_train.csv",
        tmp_path / "y_train.csv",
    )

    assert x_path.name == "X_train.csv"
    assert y_path.name == "y_train.csv"
    assert verified["sha256"] == manifest["sha256"]
    assert verified["parent_sha256"] == "rawsha"
