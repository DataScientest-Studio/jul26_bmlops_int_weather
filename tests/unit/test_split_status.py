"""The training split stays aligned with the newest DVC raw pointer."""

from pathlib import Path

from weather_mlops.data.versioning import hash_file

LOCK = {
    "stages": {
        "merge_raw": {
            "deps": [
                {"path": "data/raw/incremental", "md5": "old-raw.dir", "size": 10, "nfiles": 2},
            ]
        },
        "preprocess": {
            "outs": [
                {"path": "data/processed/X_train.csv", "md5": "train-md5", "size": 4},
                {"path": "data/processed/manifest.json", "md5": "manifest-md5", "size": 4},
            ]
        },
    }
}


def _processed(tmp_path: Path, contents: dict[str, str]) -> Path:
    processed = tmp_path / "processed"
    processed.mkdir()
    for name, text in contents.items():
        (processed / name).write_text(text)
    return processed


def test_split_is_stale_when_the_dvc_raw_pointer_is_newer_than_the_lock(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import assess_split

    processed = _processed(
        tmp_path,
        {"X_train.csv": "keep", "manifest.json": "keep"},
    )

    status = assess_split(LOCK, incremental_md5="new-raw.dir", processed_dir=processed)

    assert status.fresh is False
    assert status.raw_md5 == "new-raw.dir"
    assert status.locked_raw_md5 == "old-raw.dir"


def test_split_is_stale_when_processed_files_do_not_match_the_lock(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import assess_split

    processed = _processed(tmp_path, {"X_train.csv": "changed", "manifest.json": "keep"})
    lock = {
        "stages": {
            "merge_raw": LOCK["stages"]["merge_raw"],
            "preprocess": {
                "outs": [
                    {
                        "path": "data/processed/X_train.csv",
                        "md5": hash_file(processed / "X_train.csv", "md5"),
                        "size": 4,
                    },
                    {"path": "data/processed/manifest.json", "md5": "different", "size": 4},
                ]
            },
        }
    }

    status = assess_split(lock, incremental_md5="old-raw.dir", processed_dir=processed)

    assert status.fresh is False


def test_split_is_fresh_only_when_raw_and_processed_match_the_lock(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import assess_split

    processed = _processed(tmp_path, {"X_train.csv": "same", "manifest.json": "same"})
    lock = {
        "stages": {
            "merge_raw": LOCK["stages"]["merge_raw"],
            "preprocess": {
                "outs": [
                    {
                        "path": "data/processed/X_train.csv",
                        "md5": hash_file(processed / "X_train.csv", "md5"),
                        "size": 4,
                    },
                    {
                        "path": "data/processed/manifest.json",
                        "md5": hash_file(processed / "manifest.json", "md5"),
                        "size": 4,
                    },
                ]
            },
        }
    }

    status = assess_split(lock, incremental_md5="old-raw.dir", processed_dir=processed)

    assert status.fresh is True


def test_a_stale_split_is_rebuilt_from_raw_before_training(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import ensure_fresh_split

    calls = []
    processed = _processed(tmp_path, {"X_train.csv": "old", "manifest.json": "old"})

    result = ensure_fresh_split(
        lock=LOCK,
        incremental_md5="new-raw.dir",
        processed_dir=processed,
        merge=lambda: calls.append("merge"),
        preprocess=lambda: calls.append("preprocess"),
    )

    assert result.rebuilt is True
    assert calls == ["merge", "preprocess"]


def test_a_fresh_split_is_left_in_place_for_retraining(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import ensure_fresh_split

    processed = _processed(tmp_path, {"X_train.csv": "same", "manifest.json": "same"})
    lock = {
        "stages": {
            "merge_raw": LOCK["stages"]["merge_raw"],
            "preprocess": {
                "outs": [
                    {
                        "path": "data/processed/X_train.csv",
                        "md5": hash_file(processed / "X_train.csv", "md5"),
                        "size": 4,
                    },
                    {
                        "path": "data/processed/manifest.json",
                        "md5": hash_file(processed / "manifest.json", "md5"),
                        "size": 4,
                    },
                ]
            },
        }
    }
    calls = []

    result = ensure_fresh_split(
        lock=lock,
        incremental_md5="old-raw.dir",
        processed_dir=processed,
        merge=lambda: calls.append("merge"),
        preprocess=lambda: calls.append("preprocess"),
    )

    assert result.rebuilt is False
    assert calls == []


def test_rebuilt_split_stays_fresh_until_the_raw_pointer_changes(tmp_path: Path) -> None:
    from weather_mlops.data.split_status import ensure_fresh_split

    processed = _processed(tmp_path, {"X_train.csv": "old", "manifest.json": "old"})
    calls: list[str] = []

    def preprocess() -> None:
        calls.append("preprocess")
        (processed / "manifest.json").write_text("rebuilt")

    first = ensure_fresh_split(
        lock=LOCK,
        incremental_md5="new-raw.dir",
        processed_dir=processed,
        merge=lambda: calls.append("merge"),
        preprocess=preprocess,
    )
    second = ensure_fresh_split(
        lock=LOCK,
        incremental_md5="new-raw.dir",
        processed_dir=processed,
        merge=lambda: calls.append("merge"),
        preprocess=preprocess,
    )
    third = ensure_fresh_split(
        lock=LOCK,
        incremental_md5="newer-raw.dir",
        processed_dir=processed,
        merge=lambda: calls.append("merge-again"),
        preprocess=preprocess,
    )

    assert first.rebuilt is True
    assert second.rebuilt is False
    assert third.rebuilt is True
    assert calls == ["merge", "preprocess", "merge-again", "preprocess"]
