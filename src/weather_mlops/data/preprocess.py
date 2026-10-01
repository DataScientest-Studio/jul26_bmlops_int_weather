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
    if pd.api.types.is_numeric_dtype(df[TARGET_COLUMN]):
        df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    else:
        df[TARGET_COLUMN] = df[TARGET_COLUMN].map({"No": 0, "Yes": 1})
    df = df.dropna(subset=[TARGET_COLUMN])
    df = df[df[TARGET_COLUMN].isin([0, 1])]
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
    *,
    training_window_days: int | None = settings.training_window_days,
    validation_window_days: int = settings.validation_window_days,
    test_window_days: int = settings.test_window_days,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Split whole dates chronologically, retaining only the configured windows."""

    cleaned = clean_dataframe(df)
    train_dates, validation_dates, test_dates = _rolling_date_partitions(
        cleaned,
        training_window_days=training_window_days,
        validation_window_days=validation_window_days,
        test_window_days=test_window_days,
    )

    train_df = cleaned[cleaned[DATE_COLUMN].isin(train_dates)]
    validation_df = cleaned[cleaned[DATE_COLUMN].isin(validation_dates)]
    test_df = cleaned[cleaned[DATE_COLUMN].isin(test_dates)]

    X_train, y_train = split_features_target(train_df)
    X_validation, y_validation = split_features_target(validation_df)
    X_test, y_test = split_features_target(test_df)

    return X_train, X_validation, X_test, y_train, y_validation, y_test


def build_split_metadata(
    cleaned: pd.DataFrame,
    *,
    training_window_days: int | None,
    validation_window_days: int,
    test_window_days: int,
) -> dict[str, str | int | None]:
    """Describe the exact rolling date windows used for a processed split."""

    train_dates, validation_dates, test_dates = _rolling_date_partitions(
        cleaned,
        training_window_days=training_window_days,
        validation_window_days=validation_window_days,
        test_window_days=test_window_days,
    )

    return {
        "train_start": _date_string(train_dates[0]),
        "train_end": _date_string(train_dates[-1]),
        "validation_start": _date_string(validation_dates[0]),
        "validation_end": _date_string(validation_dates[-1]),
        "test_start": _date_string(test_dates[0]),
        "test_end": _date_string(test_dates[-1]),
        "training_window_days": training_window_days,
        "validation_window_days": validation_window_days,
        "test_window_days": test_window_days,
    }


def _rolling_date_partitions(
    cleaned: pd.DataFrame,
    *,
    training_window_days: int | None,
    validation_window_days: int,
    test_window_days: int,
) -> tuple[list[pd.Timestamp], list[pd.Timestamp], list[pd.Timestamp]]:
    if training_window_days is not None and training_window_days < 1:
        raise ValueError("training_window_days must be at least 1 or None.")
    if validation_window_days < 1:
        raise ValueError("validation_window_days must be at least 1.")
    if test_window_days < 1:
        raise ValueError("test_window_days must be at least 1.")

    unique_dates = list(cleaned[DATE_COLUMN].drop_duplicates().sort_values())
    minimum_dates = (
        validation_window_days
        + test_window_days
        + (training_window_days if training_window_days is not None else 1)
    )
    if len(unique_dates) < minimum_dates:
        raise ValueError(
            "Not enough distinct dates to form requested rolling windows "
            f"(requires {minimum_dates} distinct dates)."
        )

    test_dates = unique_dates[-test_window_days:]
    validation_start = len(unique_dates) - test_window_days - validation_window_days
    validation_dates = unique_dates[validation_start : len(unique_dates) - test_window_days]
    available_train_dates = unique_dates[:validation_start]
    train_dates = (
        available_train_dates
        if training_window_days is None
        else available_train_dates[-training_window_days:]
    )
    return train_dates, validation_dates, test_dates


def _date_string(value: pd.Timestamp) -> str:
    return value.date().isoformat()


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
    parser.add_argument(
        "--training-window-days",
        type=int,
        default=settings.training_window_days,
    )
    parser.add_argument(
        "--validation-window-days",
        type=int,
        default=settings.validation_window_days,
    )
    parser.add_argument("--test-window-days", type=int, default=settings.test_window_days)
    return parser.parse_args()


def main() -> None:
    from weather_mlops.data.manifest import build_processed_manifest, write_processed_manifest
    from weather_mlops.data.versioning import hash_file

    args = parse_args()
    dataframe = pd.read_csv(args.input)
    cleaned = clean_dataframe(dataframe)
    X_train, X_validation, X_test, y_train, y_validation, y_test = (
        temporal_train_validation_test_split(
            cleaned,
            training_window_days=args.training_window_days,
            validation_window_days=args.validation_window_days,
            test_window_days=args.test_window_days,
        )
    )
    split = build_split_metadata(
        cleaned,
        training_window_days=args.training_window_days,
        validation_window_days=args.validation_window_days,
        test_window_days=args.test_window_days,
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
        split=split,
    )
    manifest_path = write_processed_manifest(manifest, args.output_dir / "manifest.json")
    print(f"Wrote processed manifest {manifest_path} sha256={manifest['sha256']}")


if __name__ == "__main__":
    main()
