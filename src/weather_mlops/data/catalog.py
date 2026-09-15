from __future__ import annotations

import os
import subprocess
from dataclasses import replace

from weather_mlops.config.settings import PROJECT_ROOT
from weather_mlops.data.preprocess import PREPROCESS_VERSION
from weather_mlops.data.versioning import DatasetMetadata

# Re-exported so Airflow can pin the exact preprocess contract when it
# runs: ingest batch -> register raw version -> preprocess -> register
# processed version -> POST /train -> Jonathan's MLflow compare/promote.
__all__ = [
    "PREPROCESS_VERSION",
    "build_catalog_record",
    "current_git_commit",
]


def current_git_commit() -> str | None:
    """Return the code revision for catalog/model metadata.

    Prefers GIT_COMMIT (image build-arg / Compose). Falls back to `git
    rev-parse`. Appends `-dirty` when the worktree has local changes.
    """

    env_value = os.environ.get("GIT_COMMIT")
    if env_value:
        sha = env_value.removesuffix("-dirty")
        if sha:
            return env_value

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip()
    if not commit:
        return None

    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return commit

    if dirty.returncode == 0 and dirty.stdout.strip():
        return f"{commit}-dirty"
    return commit


def build_catalog_record(
    metadata: DatasetMetadata,
    *,
    version_kind: str = "raw",
    storage_uri: str | None = None,
    git_commit: str | None = None,
    preprocessing_version: str | None = None,
    parent_sha256: str | None = None,
    source: str | None = None,
    created_by: str = "local",
) -> DatasetMetadata:
    """Attach lineage fields to hashed dataset metadata without recomputing hashes."""

    return replace(
        metadata,
        version_kind=version_kind,
        storage_uri=storage_uri,
        git_commit=git_commit if git_commit is not None else current_git_commit(),
        preprocessing_version=preprocessing_version,
        parent_sha256=parent_sha256,
        source=source or metadata.source,
        created_by=created_by,
    )
