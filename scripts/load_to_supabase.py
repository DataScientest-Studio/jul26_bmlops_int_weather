import argparse
from pathlib import Path

import pandas as pd

from weather_mlops.config.settings import settings
from weather_mlops.data.database import (
    expected_weather_columns,
    store_dataset_metadata,
    store_weather_observations,
)
from weather_mlops.data.versioning import build_dataset_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load weatherAUS.csv into Supabase Postgres.")
    parser.add_argument("--path", type=Path, default=settings.raw_data_path)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the CSV and hashes without writing to Supabase.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataframe = pd.read_csv(args.path)
    metadata = build_dataset_metadata(args.path)

    if args.dry_run:
        print(f"Validated {len(dataframe):,} rows from {args.path}.")
        print(f"Dataset sha256: {metadata.sha256}")
        print("Expected Supabase columns:")
        print(", ".join(expected_weather_columns()))
        return

    store_dataset_metadata(metadata)
    inserted_rows = store_weather_observations(dataframe, batch_size=args.batch_size)

    print(f"Stored {inserted_rows:,} weather observations in Supabase.")
    print("Stored dataset metadata in Supabase.")
    print(f"Dataset sha256: {metadata.sha256}")


if __name__ == "__main__":
    main()
