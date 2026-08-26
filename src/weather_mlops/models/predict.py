from functools import lru_cache
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
