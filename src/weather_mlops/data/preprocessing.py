import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COLUMN = "RainTomorrow"
DATE_COLUMN = "Date"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Perform basic dataset cleaning."""

    df = df.copy()

    if DATE_COLUMN not in df.columns:
        raise ValueError(f"Missing required column: {DATE_COLUMN}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing required target column: {TARGET_COLUMN}")

    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")

    # A supervised model cannot train on rows without a target/date.
    df = df.dropna(subset=[DATE_COLUMN, TARGET_COLUMN])

    df[TARGET_COLUMN] = df[TARGET_COLUMN].map(
        {
            "No": 0,
            "Yes": 1,
        }
    )

    df = df.dropna(subset=[TARGET_COLUMN])
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    return df.sort_values(DATE_COLUMN).reset_index(drop=True)


def temporal_train_test_split(
    df: pd.DataFrame,
    train_fraction: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split observations chronologically to avoid future-to-past leakage."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")

    df = clean_dataframe(df)

    split_index = int(len(df) * train_fraction)

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    feature_columns = [
        column for column in df.columns if column not in {TARGET_COLUMN, DATE_COLUMN}
    ]

    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df[feature_columns]
    y_test = test_df[TARGET_COLUMN]

    return X_train, X_test, y_train, y_test


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
