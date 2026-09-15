import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from weather_mlops.config.settings import settings

TARGET_COLUMN = "RainTomorrow"
DATE_COLUMN = "Date"
LOCATION_COLUMN = "Location"
PREPROCESS_VERSION = "2026.09.15"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw weather rows before splitting into model-ready datasets."""

    df = df.copy()

    if DATE_COLUMN not in df.columns:
        raise ValueError(f"Missing required column: {DATE_COLUMN}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing required target column: {TARGET_COLUMN}")

    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")

    # A supervised model cannot train on rows without a valid timestamp/target.
    df = df.dropna(subset=[DATE_COLUMN, TARGET_COLUMN])
    df[TARGET_COLUMN] = df[TARGET_COLUMN].map({"No": 0, "Yes": 1})
    df = df.dropna(subset=[TARGET_COLUMN])
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    sort_columns = [DATE_COLUMN]
    if LOCATION_COLUMN in df.columns:
        sort_columns.append(LOCATION_COLUMN)
    return df.sort_values(sort_columns).reset_index(drop=True)


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    feature_columns = [
        column for column in df.columns if column not in {TARGET_COLUMN, DATE_COLUMN}
    ]
    return df[feature_columns], df[TARGET_COLUMN].rename(TARGET_COLUMN)


def temporal_train_validation_test_split(
    df: pd.DataFrame,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Split observations chronologically to avoid future-to-past leakage."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")
    if not 0 <= validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train_fraction + validation_fraction must be less than 1.")

    cleaned = clean_dataframe(df)
    unique_dates = list(cleaned[DATE_COLUMN].drop_duplicates().sort_values())
    n_dates = len(unique_dates)
    train_n = int(n_dates * train_fraction)
    validation_n = int(n_dates * validation_fraction)
    if train_n < 1 or validation_n < 1 or train_n + validation_n >= n_dates:
        raise ValueError("Not enough distinct dates to form train, validation, and test splits.")

    train_dates = set(unique_dates[:train_n])
    validation_dates = set(unique_dates[train_n : train_n + validation_n])
    test_dates = set(unique_dates[train_n + validation_n :])

    train_df = cleaned[cleaned[DATE_COLUMN].isin(train_dates)]
    validation_df = cleaned[cleaned[DATE_COLUMN].isin(validation_dates)]
    test_df = cleaned[cleaned[DATE_COLUMN].isin(test_dates)]

    X_train, y_train = split_features_target(train_df)
    X_validation, y_validation = split_features_target(validation_df)
    X_test, y_test = split_features_target(test_df)

    return X_train, X_validation, X_test, y_train, y_validation, y_test


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Create preprocessing pipelines based on input column types."""

    numeric_features = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_features = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess weatherAUS.csv for modeling.")
    parser.add_argument("--input", type=Path, default=settings.raw_data_path)
    parser.add_argument("--output-dir", type=Path, default=settings.processed_data_dir)
    parser.add_argument("-t", "--train-fraction", type=float, default=settings.train_fraction)
    parser.add_argument(
        "-v",
        "--validation-fraction",
        type=float,
        default=settings.validation_fraction,
    )
    return parser.parse_args()


def main() -> None:
    from weather_mlops.data.manifest import build_processed_manifest, write_processed_manifest
    from weather_mlops.data.versioning import hash_file

    args = parse_args()
    dataframe = pd.read_csv(args.input)
    X_train, X_validation, X_test, y_train, y_validation, y_test = (
        temporal_train_validation_test_split(
            dataframe,
            train_fraction=args.train_fraction,
            validation_fraction=args.validation_fraction,
        )
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "X_train.csv": X_train,
        "X_validation.csv": X_validation,
        "X_test.csv": X_test,
        "y_train.csv": y_train.to_frame(),
        "y_validation.csv": y_validation.to_frame(),
        "y_test.csv": y_test.to_frame(),
    }

    for filename, output in outputs.items():
        output_path = args.output_dir / filename
        output.to_csv(output_path, index=False)
        print(f"Wrote {len(output):,} rows to {output_path}")

    parent_sha256 = hash_file(args.input, "sha256") if args.input.exists() else None
    manifest = build_processed_manifest(
        args.output_dir,
        parent_sha256=parent_sha256,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    manifest_path = write_processed_manifest(manifest, args.output_dir / "manifest.json")
    print(f"Wrote processed manifest {manifest_path} sha256={manifest['sha256']}")


if __name__ == "__main__":
    main()
