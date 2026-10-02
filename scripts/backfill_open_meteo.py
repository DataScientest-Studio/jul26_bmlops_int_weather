"""Resumably fill the Australian gap after the Kaggle WeatherAUS seed data."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from weather_mlops.config.settings import settings
from weather_mlops.data.open_meteo import (
    WeatherLocation,
    chunk_date_range,
    ensure_australian_locations,
    fetch_open_meteo_range_payloads,
    normalize_open_meteo_range_payloads,
    read_locations,
)


def _snapshot_paths(output_dir: Path, start_date: date, end_date: date) -> tuple[Path, Path]:
    stem = f"open_meteo_backfill_{start_date:%Y%m%d}_{end_date:%Y%m%d}"
    return output_dir / f"{stem}.json", output_dir / f"{stem}.csv"


def backfill_range(
    *,
    locations: list[WeatherLocation],
    start_date: date,
    end_date: date,
    chunk_days: int,
    output_dir: Path,
    fetch_payloads: Callable[[list[WeatherLocation], date, date], list[dict[str, Any]]] = (
        fetch_open_meteo_range_payloads
    ),
    normalize_payloads: Callable[[list[dict[str, Any]]], pd.DataFrame] = (
        normalize_open_meteo_range_payloads
    ),
) -> list[dict[str, str | int]]:
    """Write each complete range chunk once; completed JSON/CSV pairs are skipped."""

    ensure_australian_locations(locations)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str | int]] = []
    for chunk_start, chunk_end in chunk_date_range(
        start_date,
        end_date,
        chunk_days=chunk_days,
    ):
        json_path, csv_path = _snapshot_paths(output_dir, chunk_start, chunk_end)
        if json_path.exists() and csv_path.exists():
            results.append(
                {
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "status": "skipped",
                    "rows": len(pd.read_csv(csv_path)),
                }
            )
            continue
        payloads = fetch_payloads(locations, chunk_start, chunk_end)
        normalized = normalize_payloads(payloads)
        json_path.write_text(json.dumps(payloads, indent=2) + "\n", encoding="utf-8")
        normalized.to_csv(csv_path, index=False)
        results.append(
            {
                "start_date": chunk_start.isoformat(),
                "end_date": chunk_end.isoformat(),
                "status": "written",
                "rows": len(normalized),
            }
        )
    return results


def _default_start_date(seed_path: Path) -> date:
    dates = pd.read_csv(seed_path, usecols=["Date"])["Date"]
    latest = pd.to_datetime(dates, errors="coerce").max()
    if pd.isna(latest):
        raise ValueError(f"{seed_path} has no valid Date values.")
    return latest.date() + timedelta(days=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resumably backfill Australian Open-Meteo archive data after WeatherAUS."
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start_date = args.start or _default_start_date(args.seed)
    if args.end < start_date:
        raise SystemExit("--end must be on or after --start.")
    results = backfill_range(
        locations=read_locations(args.locations),
        start_date=start_date,
        end_date=args.end,
        chunk_days=args.chunk_days,
        output_dir=args.output_dir,
    )
    written = sum(1 for result in results if result["status"] == "written")
    skipped = len(results) - written
    print(f"Open-Meteo backfill complete: {written} chunks written, {skipped} chunks resumed.")


if __name__ == "__main__":
    main()
