"""Processed-split identity: one JSON manifest for the six CSV files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from weather_mlops.config.settings import settings
from weather_mlops.data.catalog import current_git_commit
from weather_mlops.data.preprocess import PREPROCESS_VERSION
from weather_mlops.data.versioning import display_path, hash_file

PROCESSED_FILES = (
    "X_train.csv",
    "X_validation.csv",
    "X_test.csv",
    "y_train.csv",
    "y_validation.csv",
    "y_test.csv",
)


def build_processed_manifest(
    output_dir: Path,
    *,
    parent_sha256: str | None,
    train_fraction: float,
    validation_fraction: float,
) -> dict[str, Any]:
    files: dict[str, dict[str, str | int]] = {}
    digest = hashlib.sha256()
    for filename in PROCESSED_FILES:
        path = output_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Processed split missing: {path}")
        sha256 = hash_file(path, "sha256")
        files[filename] = {
            "sha256": sha256,
            "md5": hash_file(path, "md5"),
            "size_bytes": path.stat().st_size,
        }
        digest.update(f"{filename}:{sha256}".encode())

    return {
        "dataset_name": "weatherAUS",
        "version_kind": "processed",
        "path": display_path(output_dir / "manifest.json"),
        "sha256": digest.hexdigest(),
        "preprocessing_version": PREPROCESS_VERSION,
        "parent_sha256": parent_sha256,
        "git_commit": current_git_commit(),
        "train_fraction": train_fraction,
        "validation_fraction": validation_fraction,
        "files": files,
    }


def write_processed_manifest(manifest: dict[str, Any], path: Path | None = None) -> Path:
    output_path = path or settings.processed_manifest_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output_path


def verify_processed_manifest(
    output_dir: Path,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Confirm the six CSVs still match the stored combined identity."""

    stored = (
        manifest if manifest is not None else read_processed_manifest(output_dir / "manifest.json")
    )
    if stored is None:
        raise FileNotFoundError(f"Processed manifest missing under {output_dir}")
    current = build_processed_manifest(
        output_dir,
        parent_sha256=stored.get("parent_sha256"),
        train_fraction=float(stored["train_fraction"]),
        validation_fraction=float(stored["validation_fraction"]),
    )
    if current["sha256"] != stored["sha256"]:
        raise ValueError(
            "Processed CSVs do not match manifest.json "
            f"(disk={current['sha256']} manifest={stored['sha256']})"
        )
    return stored


def read_processed_manifest(path: Path | None = None) -> dict[str, Any] | None:
    manifest_path = path or settings.processed_manifest_path
    if not manifest_path.exists():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None
