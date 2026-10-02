"""Merge the yearly Singapore csv files into one file."""

import argparse
from pathlib import Path

import pandas as pd

from weather_mlops.data.weatheraus_schema import WEATHERAUS_COLUMNS


def merge_files(input_dir, output_path):
    files = sorted(Path(input_dir).glob("*.csv"))
    if len(files) == 0:
        raise SystemExit(f"No csv files in {input_dir}")

    frames = []
    for file in files:
        df = pd.read_csv(file)
        frames.append(df[WEATHERAUS_COLUMNS])

    merged = pd.concat(frames, ignore_index=True)

    # clean dates and remove duplicats
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    merged = merged.dropna(subset=["Date", "Location"])
    merged = merged.drop_duplicates(subset=["Date", "Location"], keep="last")
    merged = merged.sort_values(["Date", "Location"]).reset_index(drop=True)
    merged["Date"] = merged["Date"].dt.strftime("%Y-%m-%d")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/raw/open_meteo_Singapore")
    parser.add_argument("--output", default="data/raw/weatherSingapore_current.csv")
    args = parser.parse_args()

    merged = merge_files(args.input_dir, args.output)
    rain_ratio = (merged["RainTomorrow"] == "Yes").mean() * 100
    print("rows:", len(merged))
    print("from", merged["Date"].min(), "to", merged["Date"].max())
    print(f"rainy days: {rain_ratio:.1f}%")


if __name__ == "__main__":
    main()
