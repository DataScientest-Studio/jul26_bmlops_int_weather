"""Decide whether the processed split still matches the newest DVC raw data."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from weather_mlops.config.settings import settings
from weather_mlops.data.versioning import hash_file

INCREMENTAL_DEP = "data/raw/incremental"
SPLIT_SOURCE_NAME = "split_source.json"


@dataclass(frozen=True)
class SplitStatus:
    fresh: bool
    raw_md5: str | None
    locked_raw_md5: str | None
    reason: str


@dataclass(frozen=True)
class SplitPreparation:
    rebuilt: bool
    status: SplitStatus


def locked_incremental_md5(lock: dict[str, Any]) -> str | None:
    deps = lock.get("stages", {}).get("merge_raw", {}).get("deps", [])
    for dep in deps:
        if dep.get("path") == INCREMENTAL_DEP:
            value = dep.get("md5")
            return value if isinstance(value, str) else None
    return None


def assess_split(
    lock: dict[str, Any],
    incremental_md5: str | None,
    processed_dir: Path,
) -> SplitStatus:
    """Compare the current raw pointer with the lock and the split on disk."""

    locked_raw_md5 = locked_incremental_md5(lock)
    recorded = _recorded_incremental_md5(processed_dir)
    if (
        incremental_md5
        and recorded == incremental_md5
        and (processed_dir / "manifest.json").is_file()
    ):
        return SplitStatus(
            True,
            incremental_md5,
            locked_raw_md5,
            "split was rebuilt from the current DVC raw pointer",
        )
    if incremental_md5 == locked_raw_md5 and _processed_matches_lock(lock, processed_dir):
        return SplitStatus(
            True,
            incremental_md5,
            locked_raw_md5,
            "split matches the DVC lock",
        )
    if incremental_md5 != locked_raw_md5:
        return SplitStatus(
            False,
            incremental_md5,
            locked_raw_md5,
            "raw pointer is newer than the DVC lock",
        )
    return SplitStatus(
        False,
        incremental_md5,
        locked_raw_md5,
        "processed split does not match the DVC lock",
    )


def ensure_fresh_split(
    *,
    lock: dict[str, Any],
    incremental_md5: str | None,
    processed_dir: Path,
    merge: Callable[[], None] | None = None,
    preprocess: Callable[[], None] | None = None,
) -> SplitPreparation:
    """Rebuild from the raw files only when the processed split is stale."""

    status = assess_split(lock, incremental_md5, processed_dir)
    if status.fresh:
        return SplitPreparation(False, status)
    if merge is None or preprocess is None:
        rebuild_processed_split()
    else:
        merge()
        preprocess()
    if incremental_md5:
        _write_split_source(processed_dir, incremental_md5)
    return SplitPreparation(True, status)


def rebuild_processed_split() -> None:
    """Merge the seed with the incremental snapshots, then write the split."""

    from weather_mlops.data.merge_raw import merge_raw_datasets
    from weather_mlops.data.preprocess import write_processed_split

    merge_raw_datasets(
        settings.seed_raw_data_path,
        settings.raw_incremental_dir,
        settings.raw_data_path,
    )
    write_processed_split(settings.raw_data_path, settings.processed_data_dir)


def load_dvc_lock(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} did not contain a DVC lock.")
    return document


def incremental_pointer_md5(path: Path) -> str:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    outs = document.get("outs") if isinstance(document, dict) else None
    if not outs or not isinstance(outs[0], dict) or not isinstance(outs[0].get("md5"), str):
        raise ValueError(f"{path} has no incremental md5.")
    return outs[0]["md5"]


def _processed_matches_lock(lock: dict[str, Any], processed_dir: Path) -> bool:
    outs = lock.get("stages", {}).get("preprocess", {}).get("outs", [])
    if not outs:
        return False
    for item in outs:
        name = Path(str(item.get("path", ""))).name
        expected = item.get("md5")
        path = processed_dir / name
        if not name or not isinstance(expected, str) or not path.is_file():
            return False
        if hash_file(path, "md5") != expected:
            return False
    return True


def _recorded_incremental_md5(processed_dir: Path) -> str | None:
    path = processed_dir / SPLIT_SOURCE_NAME
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("incremental_md5") if isinstance(payload, dict) else None
    return value if isinstance(value, str) else None


def _write_split_source(processed_dir: Path, incremental_md5: str) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    payload = {"incremental_md5": incremental_md5}
    (processed_dir / SPLIT_SOURCE_NAME).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
