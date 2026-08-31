import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from weather_mlops.config.settings import settings


@lru_cache(maxsize=1)
def load_model() -> Pipeline:
    """Load the trained model from disk."""

    if not settings.model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {settings.model_path}. Run the training pipeline first."
        )

    return joblib.load(settings.model_path)


def predict(features: dict[str, Any]) -> dict[str, Any]:
    """Predict whether it will rain tomorrow."""

    model = load_model()

    dataframe = pd.DataFrame([features])

    predicted_class = int(model.predict(dataframe)[0])
    probability = float(model.predict_proba(dataframe)[0, 1])

    return {
        "rain_tomorrow": bool(predicted_class),
        "probability": probability,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rainfall prediction for one observation.")
    parser.add_argument(
        "--input-json",
        type=Path,
        required=True,
        help="Path to a JSON file containing one feature dictionary.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.sample_prediction_output_path,
        help="Path where the prediction JSON will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features: dict[str, Any] = json.loads(args.input_json.read_text(encoding="utf-8"))
    prediction = predict(features)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(prediction, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(prediction, indent=2))


if __name__ == "__main__":
    main()
