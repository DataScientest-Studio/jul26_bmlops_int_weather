import argparse
from pathlib import Path

import pandas as pd

from weather_mlops.config.settings import settings
from weather_mlops.data.weatheraus_schema import WEATHERAUS_COLUMNS


def discover_incremental_files(incremental_dir: Path) -> list[Path]:
    if not incremental_dir.exists():
        return []
    return sorted(path for path in incremental_dir.glob("*.csv") if path.is_file())


def _align_to_seed_columns(
    df: pd.DataFrame,
    seed_columns: list[str],
    source_path: Path,
) -> pd.DataFrame:
    missing_weather_columns = set(WEATHERAUS_COLUMNS) - set(df.columns)
    if missing_weather_columns:
        missing = ", ".join(sorted(missing_weather_columns))
        raise ValueError(f"{source_path} is missing required WeatherAUS columns: {missing}")

    aligned = df.copy()
    for column in seed_columns:
        if column not in aligned.columns:
            aligned[column] = pd.NA

    return aligned[seed_columns]


def merge_raw_datasets(
    seed_path: Path,
    incremental_dir: Path,
    output_path: Path,
) -> pd.DataFrame:
    seed = pd.read_csv(seed_path)
    seed_columns = seed.columns.tolist()
    frames = [_align_to_seed_columns(seed, seed_columns, seed_path)]

    for incremental_path in discover_incremental_files(incremental_dir):
        incremental = pd.read_csv(incremental_path)
        frames.append(_align_to_seed_columns(incremental, seed_columns, incremental_path))

    merged = pd.concat(frames, ignore_index=True)
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    merged = merged.dropna(subset=["Date", "Location"])
    merged = merged.drop_duplicates(subset=["Date", "Location"], keep="last")
    merged = merged.sort_values(["Date", "Location"]).reset_index(drop=True)
    merged["Date"] = merged["Date"].dt.strftime("%Y-%m-%d")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge seed WeatherAUS data with incremental snapshots."
    )
    parser.add_argument("--seed", type=Path, default=settings.seed_raw_data_path)
    parser.add_argument("--incremental-dir", type=Path, default=settings.raw_incremental_dir)
    parser.add_argument("--output", type=Path, default=settings.raw_data_path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    merged = merge_raw_datasets(args.seed, args.incremental_dir, args.output)
    print(f"Wrote {len(merged):,} merged rows to {args.output}")


if __name__ == "__main__":
    main()
