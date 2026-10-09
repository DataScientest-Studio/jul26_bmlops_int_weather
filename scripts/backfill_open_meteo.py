"""Resumably fill the Australian gap after the Kaggle WeatherAUS seed data.

Finished date chunks are skipped. A rate limit stops the run after saving
whatever completed, and the next invocation continues from the first missing
part. Keep ``--chunk-days`` and ``--location-batch-size`` stable across runs.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from weather_mlops.config.settings import settings
from weather_mlops.data.open_meteo import (
    OpenMeteoRateLimitError,
    WeatherLocation,
    chunk_date_range,
    ensure_australian_locations,
    fetch_open_meteo_range_payloads,
    normalize_open_meteo_range_payloads,
    read_locations,
)


def _snapshot_paths(
    output_dir: Path,
    start_date: date,
    end_date: date,
    batch_index: int | None = None,
) -> tuple[Path, Path]:
    stem = f"open_meteo_backfill_{start_date:%Y%m%d}_{end_date:%Y%m%d}"
    if batch_index is not None:
        stem = f"{stem}_loc{batch_index:03d}"
    return output_dir / f"{stem}.json", output_dir / f"{stem}.csv"


def _done_path(output_dir: Path, start_date: date, end_date: date) -> Path:
    return output_dir / f"open_meteo_backfill_{start_date:%Y%m%d}_{end_date:%Y%m%d}.done"


def _write_done_marker(
    output_dir: Path,
    start_date: date,
    end_date: date,
    csv_paths: list[Path],
) -> None:
    payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "csv_files": [path.name for path in csv_paths],
    }
    _done_path(output_dir, start_date, end_date).write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _csv_row_count(path: Path) -> int:
    with path.open("rb") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _location_batches(
    locations: list[WeatherLocation],
    batch_size: int,
) -> list[tuple[int, list[WeatherLocation]]]:
    if batch_size < 1:
        raise ValueError("location_batch_size must be positive.")
    return [
        (index // batch_size, locations[index : index + batch_size])
        for index in range(0, len(locations), batch_size)
    ]


def exit_code_for_stop(stopped_reason: str | None) -> int:
    """75 means the quota stopped the run and the same command should be repeated."""

    if stopped_reason == "rate_limit":
        return 75
    return 0


def backfill_range(
    *,
    locations: list[WeatherLocation],
    start_date: date,
    end_date: date,
    chunk_days: int,
    output_dir: Path,
    location_batch_size: int = 8,
    max_requests: int | None = None,
    pause_seconds: float = 0.0,
    fetch_payloads: Callable[[list[WeatherLocation], date, date], list[dict[str, Any]]] = (
        fetch_open_meteo_range_payloads
    ),
    normalize_payloads: Callable[[list[dict[str, Any]]], pd.DataFrame] = (
        normalize_open_meteo_range_payloads
    ),
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Write each finished part once. A rate limit or request budget ends the run."""

    ensure_australian_locations(locations)
    if max_requests is not None and max_requests < 1:
        raise ValueError("max_requests must be positive.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    batches = _location_batches(locations, location_batch_size)
    use_shards = len(batches) > 1
    chunks = chunk_date_range(start_date, end_date, chunk_days=chunk_days)
    results: list[dict[str, Any]] = []
    stopped_reason: str | None = None
    requests = 0
    chunks_complete = 0

    for chunk_start, chunk_end in chunks:
        legacy_json, legacy_csv = _snapshot_paths(output_dir, chunk_start, chunk_end)
        if legacy_json.exists() and legacy_csv.exists():
            # A finished single-file chunk stays finished if batch size changes later.
            _write_done_marker(output_dir, chunk_start, chunk_end, [legacy_csv])
            results.append(
                {
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "status": "skipped",
                    "rows": _csv_row_count(legacy_csv),
                }
            )
            chunks_complete += 1
            continue

        part_csvs: list[Path] = []
        chunk_complete = True
        for batch_index, batch_locations in batches:
            stored_index = batch_index if use_shards else None
            json_path, csv_path = _snapshot_paths(
                output_dir,
                chunk_start,
                chunk_end,
                stored_index,
            )
            part_csvs.append(csv_path)
            if json_path.exists() and csv_path.exists():
                results.append(
                    {
                        "start_date": chunk_start.isoformat(),
                        "end_date": chunk_end.isoformat(),
                        "location_batch": batch_index,
                        "status": "skipped",
                        "rows": _csv_row_count(csv_path),
                    }
                )
                continue
            if max_requests is not None and requests >= max_requests:
                stopped_reason = "request_budget"
                chunk_complete = False
                break
            try:
                payloads = fetch_payloads(batch_locations, chunk_start, chunk_end)
            except OpenMeteoRateLimitError as error:
                results.append(
                    {
                        "start_date": chunk_start.isoformat(),
                        "end_date": chunk_end.isoformat(),
                        "location_batch": batch_index,
                        "status": "rate_limited",
                        "rows": 0,
                        "scope": error.scope,
                        "detail": str(error),
                    }
                )
                stopped_reason = "rate_limit"
                chunk_complete = False
                break
            normalized = normalize_payloads(payloads)
            json_path.write_text(json.dumps(payloads, indent=2) + "\n", encoding="utf-8")
            normalized.to_csv(csv_path, index=False)
            requests += 1
            results.append(
                {
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "location_batch": batch_index,
                    "status": "written",
                    "rows": len(normalized),
                }
            )
            if pause_seconds > 0:
                sleeper(pause_seconds)
        if chunk_complete:
            _write_done_marker(output_dir, chunk_start, chunk_end, part_csvs)
            chunks_complete += 1
        if stopped_reason:
            break

    outcome = {
        "results": results,
        "stopped_reason": stopped_reason,
        "requests": requests,
        "chunks_total": len(chunks),
        "chunks_complete": chunks_complete,
    }
    progress_path = output_dir / "backfill_progress.json"
    progress_path.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    outcome["progress_path"] = str(progress_path)
    return outcome


def _default_start_date(seed_path: Path) -> date:
    dates = pd.read_csv(seed_path, usecols=["Date"])["Date"]
    latest = pd.to_datetime(dates, errors="coerce").max()
    if pd.isna(latest):
        raise ValueError(f"{seed_path} has no valid Date values.")
    return latest.date() + timedelta(days=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resumably backfill Australian Open-Meteo archive data after WeatherAUS. "
            "Re-run the same command after a rate limit to continue."
        )
    )
    parser.add_argument("--seed", type=Path, default=settings.seed_raw_data_path)
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        help="First observation day. Defaults to one day after the latest seed date.",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=2),
        help="Last observation day; default leaves one following day for labels.",
    )
    parser.add_argument("--locations", type=Path, default=settings.weather_locations_path)
    parser.add_argument("--output-dir", type=Path, default=settings.raw_incremental_dir)
    parser.add_argument("--chunk-days", type=int, default=90)
    parser.add_argument(
        "--location-batch-size",
        type=int,
        default=8,
        help="Locations per archive request. Keep this value the same on every resume.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        help="Stop after this many new archive requests so a later run can continue.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Wait between successful archive requests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start_date = args.start or _default_start_date(args.seed)
    if args.end < start_date:
        raise SystemExit("--end must be on or after --start.")
    outcome = backfill_range(
        locations=read_locations(args.locations),
        start_date=start_date,
        end_date=args.end,
        chunk_days=args.chunk_days,
        output_dir=args.output_dir,
        location_batch_size=args.location_batch_size,
        max_requests=args.max_requests,
        pause_seconds=args.pause_seconds,
    )
    results = outcome["results"]
    written = sum(1 for result in results if result["status"] == "written")
    skipped = sum(1 for result in results if result["status"] == "skipped")
    print(
        "Open-Meteo backfill: "
        f"{written} archive requests written, {skipped} parts already on disk, "
        f"{outcome['chunks_complete']}/{outcome['chunks_total']} date chunks complete."
    )
    print(f"Progress file: {outcome['progress_path']}")
    if outcome["stopped_reason"] == "rate_limit":
        print(
            "Open-Meteo rate limit reached. Finished chunks stay on disk. "
            "Re-run the same command to continue."
        )
    elif outcome["stopped_reason"] == "request_budget":
        print("Request budget reached. Re-run the same command to continue.")
    elif outcome["chunks_complete"] == outcome["chunks_total"]:
        print("Open-Meteo backfill complete.")
    raise SystemExit(exit_code_for_stop(outcome["stopped_reason"]))


if __name__ == "__main__":
    main()
