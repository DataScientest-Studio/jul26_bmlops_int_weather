"""Download Singapore weather from Open-Meteo, one csv per year."""

import argparse
from pathlib import Path

import requests

from weather_mlops.data.open_meteo import (
    ARCHIVE_URL,
    DAILY_VARIABLES,
    HOURLY_VARIABLES,
    normalize_open_meteo_payloads,
)

SINGAPORE = {
    "location": "Singapore",
    "latitude": 1.3521,
    "longitude": 103.8198,
    "timezone": "Asia/Singapore",
}


def download_year(year):
    params = {
        "latitude": SINGAPORE["latitude"],
        "longitude": SINGAPORE["longitude"],
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(HOURLY_VARIABLES),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": SINGAPORE["timezone"],
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def save_year(year, output_dir):
    data = download_year(year)
    days = data["daily"]["time"]

    # one payload per day, like the australian ingestion
    # the last day is skiped because we dont know the rain of tomorow
    payloads = []
    for day in days[:-1]:
        payloads.append(
            {
                "provider": "open-meteo",
                "location": SINGAPORE,
                "date": day,
                "response": data,
            }
        )

    df = normalize_open_meteo_payloads(payloads)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    csv_path = Path(output_dir) / f"open_meteo_Singapore_{year}.csv"
    df.to_csv(csv_path, index=False)
    print(year, ":", len(df), "rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2014)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--output-dir", default="data/raw/open_meteo_Singapore")
    args = parser.parse_args()

    for year in range(args.start, args.end + 1):
        save_year(year, args.output_dir)


if __name__ == "__main__":
    main()
