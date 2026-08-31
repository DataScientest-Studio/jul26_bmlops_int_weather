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

    return df.sort_values(DATE_COLUMN).reset_index(drop=True)


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
    train_end = int(len(cleaned) * train_fraction)
    validation_end = int(len(cleaned) * (train_fraction + validation_fraction))

    train_df = cleaned.iloc[:train_end]
    validation_df = cleaned.iloc[train_end:validation_end]
    test_df = cleaned.iloc[validation_end:]

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
    parser.add_argument("--train-fraction", type=float, default=settings.train_fraction)
    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=settings.validation_fraction,
    )
    return parser.parse_args()


def main() -> None:
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


if __name__ == "__main__":
    main()
