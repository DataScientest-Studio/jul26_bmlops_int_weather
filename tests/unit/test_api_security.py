"""The /predict, /predict/live_data and /train endpoints must require basic auth."""

import pytest
from fastapi.testclient import TestClient

from weather_mlops.api.main import app

GOOD_USER = "weather"
GOOD_PASS = "supersecret"
PREDICT_METRICS = {
    "rain_tomorrow": False,
    "probability": 0.12,
    "model": {
        "name": "weather-rainfall-classifier",
        "alias": "champion",
        "version": "3",
        "source": "models:/weather-rainfall-classifier@champion",
        "dataset_sha256": "abc",
        "git_commit": "deadbeef",
    },
}
TRAIN_METRICS = {
    "accuracy": 0.8,
    "precision": 0.8,
    "recall": 0.8,
    "f1": 0.8,
    "roc_auc": 0.8,
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_AUTH_USER", GOOD_USER)
    monkeypatch.setenv("API_AUTH_PASSWORD", GOOD_PASS)

    def fake_locations():
        return ["Sydney"]

    fake_locations.cache_clear = lambda: None
    monkeypatch.setattr("weather_mlops.api.main.get_locations", fake_locations)
    monkeypatch.setattr(
        "weather_mlops.api.main.predict",
        lambda _features: PREDICT_METRICS,
    )
    monkeypatch.setattr(
        "weather_mlops.api.main.train_model",
        lambda **_kwargs: (None, TRAIN_METRICS),
    )
    with TestClient(app) as test_client:
        yield test_client


def test_health_is_open_without_auth(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "This API is running"
    assert response.json()["auth_configured"] is True
    assert "model" in response.json()


def test_predict_rejects_missing_credentials(client):
    response = client.post("/predict", json={"location": "Sydney"})

    assert response.status_code == 401
    assert response.headers.get("www-authenticate", "").lower().startswith("basic")


def test_predict_rejects_wrong_password(client):
    response = client.post(
        "/predict",
        json={"location": "Sydney"},
        auth=(GOOD_USER, "wrong-password"),
    )

    assert response.status_code == 401


def test_predict_passes_auth_when_credentials_match(client):
    response = client.post(
        "/predict",
        json={"location": "Sydney", "rainfall": 0.0, "humidity_3pm": 30.0, "pressure_3pm": 1015.0},
        auth=(GOOD_USER, GOOD_PASS),
    )

    assert response.status_code == 200
    assert response.json()["rain_tomorrow"] is False
    assert response.json()["model"]["alias"] == "champion"
    assert response.json()["model"]["version"] == "3"


def test_train_rejects_missing_credentials(client):
    response = client.post("/train", json={})

    assert response.status_code == 401


def test_train_passes_auth_when_credentials_match(client):
    response = client.post("/train", json={}, auth=(GOOD_USER, GOOD_PASS))

    assert response.status_code == 200
    assert response.json()["roc_auc"] == 0.8


def test_predict_live_data_rejects_missing_credentials(client):
    response = client.post("/predict/live_data", json={"location": "Sydney"})

    assert response.status_code == 401


def test_missing_env_returns_503(client, monkeypatch):
    monkeypatch.delenv("API_AUTH_USER", raising=False)
    monkeypatch.delenv("API_AUTH_PASSWORD", raising=False)

    response = client.post("/predict", json={"location": "Sydney"}, auth=("any", "any"))

    assert response.status_code == 503


def test_empty_env_returns_503(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_USER", "")
    monkeypatch.setenv("API_AUTH_PASSWORD", "")

    response = client.post("/predict", json={"location": "Sydney"}, auth=("", ""))

    assert response.status_code == 503
