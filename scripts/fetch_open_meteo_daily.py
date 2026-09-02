import argparse
from datetime import date
from pathlib import Path

from weather_mlops.config.settings import settings
from weather_mlops.data.open_meteo import (
    OpenMeteoError,
    fetch_open_meteo_daily_payload,
    normalize_open_meteo_payloads,
    read_locations,
    write_open_meteo_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch one day of Open-Meteo data and normalize it to WeatherAUS columns."
    )
    parser.add_argument("--date", required=True, help="Observation date in YYYY-MM-DD format.")
    parser.add_argument("--locations", type=Path, default=settings.weather_locations_path)
    parser.add_argument("--output-dir", type=Path, default=settings.raw_incremental_dir)
    parser.add_argument("--limit", type=int, help="Fetch only the first N locations.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    observation_date = date.fromisoformat(args.date)
    locations = read_locations(args.locations)
    if args.limit is not None:
        locations = locations[: args.limit]

    try:
        payloads = [
            fetch_open_meteo_daily_payload(location, observation_date) for location in locations
        ]
    except OpenMeteoError as error:
        raise SystemExit(str(error)) from error

    normalized = normalize_open_meteo_payloads(payloads)
    json_path, csv_path = write_open_meteo_snapshot(
        payloads,
        normalized,
        args.output_dir,
        observation_date,
    )

    print(f"Wrote raw Open-Meteo JSON to {json_path}")
    print(f"Wrote {len(normalized):,} normalized rows to {csv_path}")


if __name__ == "__main__":
    main()
