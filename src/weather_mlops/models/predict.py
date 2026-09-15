"""Serve the registered champion, with a local joblib fallback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import requests

from weather_mlops.config.settings import settings

_MODEL: Any | None = None
_MODEL_KEY: tuple | None = None
_SERVING: dict[str, Any] | None = None

REGISTRY_TIMEOUT_SECONDS = 2


def champion_model_uri() -> str:
    return f"models:/{settings.mlflow_model_name}@{settings.mlflow_champion_alias}"


def _registry_get(path: str, params: dict[str, str]) -> dict[str, Any] | None:
    uri = settings.mlflow_tracking_uri
    if not uri:
        return None
    try:
        response = requests.get(
            f"{uri.rstrip('/')}{path}",
            params=params,
            timeout=REGISTRY_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _champion_metadata() -> dict[str, Any] | None:
    if not settings.mlflow_tracking_uri:
        return None
    payload = _registry_get(
        "/api/2.0/mlflow/registered-models/alias",
        {
            "name": settings.mlflow_model_name,
            "alias": settings.mlflow_champion_alias,
        },
    )
    if not payload:
        return None
    version = payload.get("model_version") or {}
    if not version.get("version"):
        return None
    run_id = version.get("run_id")
    tags: dict[str, str] = {}
    if run_id:
        run_payload = _registry_get("/api/2.0/mlflow/runs/get", {"run_id": str(run_id)})
        raw_tags = ((run_payload or {}).get("run") or {}).get("data", {}).get("tags") or []
        tags = {item.get("key"): item.get("value") for item in raw_tags if item.get("key")}
    return {
        "name": version.get("name") or settings.mlflow_model_name,
        "alias": settings.mlflow_champion_alias,
        "version": version.get("version"),
        "source": champion_model_uri(),
        "dataset_sha256": tags.get("dataset_sha256"),
        "git_commit": tags.get("git_commit"),
    }


def _load_champion_from_mlflow() -> tuple[Any, dict[str, Any]] | None:
    info = _champion_metadata()
    if info is None:
        return None
    import mlflow.sklearn

    model = mlflow.sklearn.load_model(champion_model_uri())
    return model, info


def _local_model_path() -> Path | None:
    for path in (settings.best_model_path, settings.model_path):
        if path.exists():
            return path
    return None


def _local_model_key() -> tuple | None:
    path = _local_model_path()
    if path is None:
        return None
    return (str(path), path.stat().st_mtime)


def _can_reuse_cache(registry_info: dict[str, Any] | None, local_key: tuple | None) -> bool:
    if _MODEL is None or _SERVING is None:
        return False
    if registry_info is not None:
        return _SERVING.get("version") == registry_info.get("version")
    if _SERVING.get("alias"):
        return True
    return local_key is not None and local_key == _MODEL_KEY


def load_model():
    """Load the champion from MLflow, else the local fallback joblib."""
    global _MODEL, _MODEL_KEY, _SERVING

    try:
        registry_info = _champion_metadata()
    except Exception:
        registry_info = None

    local_key = _local_model_key()
    if _can_reuse_cache(registry_info, local_key):
        return _MODEL

    if registry_info is not None:
        try:
            loaded = _load_champion_from_mlflow()
        except Exception:
            loaded = None
        if loaded is not None:
            model, info = loaded
            _MODEL = model
            _SERVING = info
            _MODEL_KEY = local_key
            return _MODEL

    path = _local_model_path()
    if path is None:
        raise FileNotFoundError(
            f"No model at {settings.best_model_path} or {settings.model_path}. Train first."
        )
    _MODEL = joblib.load(path)
    _SERVING = {
        "name": settings.mlflow_model_name,
        "alias": None,
        "version": None,
        "source": path.name,
        "dataset_sha256": None,
        "git_commit": None,
    }
    _MODEL_KEY = local_key
    return _MODEL


def serving_model_info() -> dict[str, Any] | None:
    return dict(_SERVING) if _SERVING else None


def describe_serving_model(*, probe_registry: bool = True) -> dict[str, Any] | None:
    """Return cached serving info, optionally the live champion, else the local file."""
    cached = serving_model_info()
    if cached:
        return cached
    if probe_registry:
        info = _champion_metadata()
        if info:
            return info
    path = _local_model_path()
    if path is None:
        return None
    return {
        "name": settings.mlflow_model_name,
        "alias": None,
        "version": None,
        "source": path.name,
        "dataset_sha256": None,
        "git_commit": None,
    }


def clear_model_cache() -> None:
    global _MODEL, _MODEL_KEY, _SERVING
    _MODEL = None
    _MODEL_KEY = None
    _SERVING = None


def predict_from_features(features: pd.DataFrame) -> tuple[int, float]:
    """
    Generate a rain prediction from a feature DataFrame.

    Returns:
        A tuple of (predicted class, probability of rain).
        The class is 1 if rain is predicted, 0 otherwise.
    """
    model = load_model()
    prediction = int(model.predict(features)[0])
    probability = float(model.predict_proba(features)[0][1])
    return prediction, probability


def predict(features: dict[str, Any]) -> dict[str, Any]:
    """Predict whether it will rain tomorrow from one feature dict."""
    predicted_class, probability = predict_from_features(pd.DataFrame([features]))
    serving = serving_model_info() or describe_serving_model(probe_registry=False)
    if serving is None:
        raise FileNotFoundError("No serving model is available.")
    return {
        "rain_tomorrow": bool(predicted_class),
        "probability": probability,
        "model": serving,
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


load_model.cache_clear = clear_model_cache


if __name__ == "__main__":
    main()
