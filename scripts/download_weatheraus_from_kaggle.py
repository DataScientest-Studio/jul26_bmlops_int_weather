import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-time helper used to download the original weatherAUS.csv file."
    )
    parser.add_argument(
        "--dataset",
        default="jsphyg/weather-dataset-rattle-package",
        help="Kaggle dataset slug.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise SystemExit(
            "The Kaggle package is intentionally not part of the project runtime. "
            "Run this helper with: "
            "uv run --with kaggle python scripts/download_weatheraus_from_kaggle.py"
        ) from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(
        args.dataset,
        path=args.output_dir,
        unzip=True,
        force=args.force,
    )

    dataset_path = args.output_dir / "weatherAUS.csv"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Expected {dataset_path} after download.")

    print(f"Downloaded {dataset_path}")
    print("Next step for a new raw dataset: uv run dvc add data/raw/weatherAUS.csv")


if __name__ == "__main__":
    main()
