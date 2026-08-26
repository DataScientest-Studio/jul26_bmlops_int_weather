import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from weather_mlops.config.settings import settings
from weather_mlops.data.download import load_raw_data
from weather_mlops.data.preprocessing import (
    build_preprocessor,
    temporal_train_test_split,
)
from weather_mlops.models.evaluation import evaluate_classifier


def train_model() -> tuple[Pipeline, dict[str, float]]:
    """Train and evaluate the baseline rainfall classifier."""

    print("Loading dataset...")
    df = load_raw_data()

    print(f"Dataset size: {len(df):,} rows")

    X_train, X_test, y_train, y_test = temporal_train_test_split(df)

    print(f"Training samples: {len(X_train):,}")
    print(f"Test samples:     {len(X_test):,}")

    preprocessor = build_preprocessor(X_train)

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", model),
        ]
    )

    print("Training baseline model...")
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    metrics = evaluate_classifier(
        y_true=y_test,
        y_pred=predictions,
        y_probability=probabilities,
    )

    print("\nEvaluation:")
    for name, value in metrics.items():
        print(f"  {name:<10}: {value:.4f}")

    settings.model_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(pipeline, settings.model_path)

    print(f"\nModel saved to: {settings.model_path}")

    return pipeline, metrics


if __name__ == "__main__":
    train_model()
