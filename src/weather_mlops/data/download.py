import zipfile
from pathlib import Path

import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

from weather_mlops.config.settings import settings

KAGGLE_DATASET = "jsphyg/weather-dataset-rattle-package"


def download_dataset(destination: Path | None = None) -> Path:
    """Download and extract the Australian weather dataset from Kaggle."""

    destination = destination or settings.raw_data_path.parent
    destination.mkdir(parents=True, exist_ok=True)

    target_file = destination / "weatherAUS.csv"

    if target_file.exists():
        print(f"Dataset already exists: {target_file}")
        return target_file

    print("Authenticating with Kaggle...")

    api = KaggleApi()
    api.authenticate()

    print(f"Downloading dataset: {KAGGLE_DATASET}")

    api.dataset_download_files(
        KAGGLE_DATASET,
        path=destination,
        unzip=False,
    )

    zip_path = destination / "weather-dataset-rattle-package.zip"

    if not zip_path.exists():
        raise FileNotFoundError(f"Expected Kaggle archive was not found at: {zip_path}")

    print("Extracting dataset...")

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(destination)

    zip_path.unlink()

    if not target_file.exists():
        raise FileNotFoundError("Dataset was downloaded, but weatherAUS.csv was not found.")

    print(f"Dataset downloaded to: {target_file}")

    return target_file


def load_raw_data(path: Path | None = None) -> pd.DataFrame:
    """Load the Australian weather dataset."""

    dataset_path = path or settings.raw_data_path

    if not dataset_path.exists():
        print("Dataset not found locally. Downloading from Kaggle...")
        dataset_path = download_dataset(dataset_path.parent)

    dataframe = pd.read_csv(dataset_path)

    if dataframe.empty:
        raise ValueError("Dataset is empty.")

    if "RainTomorrow" not in dataframe.columns:
        raise ValueError("Expected target column 'RainTomorrow' was not found.")

    return dataframe


if __name__ == "__main__":
    df = load_raw_data()

    print()
    print(f"Loaded {len(df):,} observations")
    print(f"Columns: {len(df.columns)}")
    print()
    print(df.head())
