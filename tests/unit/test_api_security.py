"""The /predict, /predict/live_data and /train endpoints must require basic auth."""

import pytest
from fastapi.testclient import TestClient

from weather_mlops.api.main import app

GOOD_USER = "weather"
GOOD_PASS = "supersecret"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_AUTH_USER", GOOD_USER)
    monkeypatch.setenv("API_AUTH_PASSWORD", GOOD_PASS)
    return TestClient(app)


# --- /health is always open --------------------------------------------------


def test_health_is_open_without_auth(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "This API is running"


# --- /predict refuses unauthenticated calls ---------------------------------


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
        json={"location": "Sydney"},
        auth=(GOOD_USER, GOOD_PASS),
    )

    # Anything other than 401 means auth let the request in.
    assert response.status_code != 401


# --- /train is also protected ----------------------------------------------


def test_train_rejects_missing_credentials(client):
    response = client.post("/train", json={})

    assert response.status_code == 401


def test_train_passes_auth_when_credentials_match(client):
    response = client.post("/train", json={}, auth=(GOOD_USER, GOOD_PASS))

    # Anything other than 401 means auth let the request in.
    assert response.status_code != 401


# --- /predict/live_data is also protected ----------------------------------


def test_predict_live_data_rejects_missing_credentials(client):
    response = client.post("/predict/live_data", json={"location": "Sydney"})

    assert response.status_code == 401


# --- misconfiguration is loud, not silent ----------------------------------


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
