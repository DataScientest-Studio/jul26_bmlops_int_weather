from weather_mlops.models import predict


def test_load_model_prefers_champion_joblib(tmp_path, monkeypatch) -> None:
    last_train = tmp_path / "rain_classifier.joblib"
    champion = tmp_path / "best_model.joblib"
    last_train.write_bytes(b"old")
    champion.write_bytes(b"champ")
    monkeypatch.setattr(predict.settings, "model_path", last_train)
    monkeypatch.setattr(predict.settings, "best_model_path", champion)
    monkeypatch.setattr(predict.settings, "mlflow_tracking_uri", None)
    monkeypatch.setattr(predict, "_load_champion_from_mlflow", lambda: None)
    predict.clear_model_cache()

    loaded = []

    def fake_joblib_load(path):
        loaded.append(path)
        return object()

    monkeypatch.setattr(predict.joblib, "load", fake_joblib_load)

    predict.load_model()

    assert loaded == [champion]
    assert predict.serving_model_info()["source"] == "best_model.joblib"
    assert predict.serving_model_info()["alias"] is None


def test_load_model_uses_mlflow_champion(tmp_path, monkeypatch) -> None:
    last_train = tmp_path / "rain_classifier.joblib"
    last_train.write_bytes(b"old")
    champion_model = object()
    info = {
        "name": "weather-rainfall-classifier",
        "alias": "champion",
        "version": "2",
        "source": "models:/weather-rainfall-classifier@champion",
        "dataset_sha256": "abc",
        "git_commit": "deadbeef",
    }
    monkeypatch.setattr(predict.settings, "model_path", last_train)
    monkeypatch.setattr(predict.settings, "best_model_path", tmp_path / "missing.joblib")
    monkeypatch.setattr(predict.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(predict, "_champion_metadata", lambda: info)
    monkeypatch.setattr(predict, "_load_champion_from_mlflow", lambda: (champion_model, info))
    predict.clear_model_cache()

    assert predict.load_model() is champion_model
    assert predict.serving_model_info() == info


def test_load_model_reloads_when_registry_recovers(tmp_path, monkeypatch) -> None:
    last_train = tmp_path / "rain_classifier.joblib"
    last_train.write_bytes(b"local")
    local_model = object()
    champion_model = object()
    info = {
        "name": "weather-rainfall-classifier",
        "alias": "champion",
        "version": "3",
        "source": "models:/weather-rainfall-classifier@champion",
        "dataset_sha256": None,
        "git_commit": None,
    }
    monkeypatch.setattr(predict.settings, "model_path", last_train)
    monkeypatch.setattr(predict.settings, "best_model_path", tmp_path / "missing.joblib")
    monkeypatch.setattr(predict.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(predict.joblib, "load", lambda _path: local_model)
    registry: dict = {"info": None}
    monkeypatch.setattr(predict, "_champion_metadata", lambda: registry["info"])
    monkeypatch.setattr(
        predict,
        "_load_champion_from_mlflow",
        lambda: (champion_model, info),
    )
    predict.clear_model_cache()

    assert predict.load_model() is local_model
    assert predict.serving_model_info()["alias"] is None

    registry["info"] = info
    assert predict.load_model() is champion_model
    assert predict.serving_model_info()["version"] == "3"


def test_load_model_reloads_when_champion_version_changes(tmp_path, monkeypatch) -> None:
    last_train = tmp_path / "rain_classifier.joblib"
    last_train.write_bytes(b"local")
    first = {
        "name": "weather-rainfall-classifier",
        "alias": "champion",
        "version": "1",
        "source": "models:/weather-rainfall-classifier@champion",
        "dataset_sha256": None,
        "git_commit": None,
    }
    second = {**first, "version": "2"}
    models = {"current": object(), "next": object()}
    state = {"info": first, "model": models["current"]}
    monkeypatch.setattr(predict.settings, "model_path", last_train)
    monkeypatch.setattr(predict.settings, "best_model_path", tmp_path / "missing.joblib")
    monkeypatch.setattr(predict.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(predict, "_champion_metadata", lambda: state["info"])
    monkeypatch.setattr(
        predict,
        "_load_champion_from_mlflow",
        lambda: (state["model"], state["info"]),
    )
    predict.clear_model_cache()

    assert predict.load_model() is models["current"]
    state["info"] = second
    state["model"] = models["next"]
    assert predict.load_model() is models["next"]


def test_champion_metadata_uses_request_timeout(monkeypatch) -> None:
    called: dict[str, float | None] = {}

    def fake_get(url, params=None, timeout=None):
        called["timeout"] = timeout
        called["url"] = url
        raise predict.requests.ConnectionError("down")

    monkeypatch.setattr(predict.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(predict.requests, "get", fake_get)

    assert predict._champion_metadata() is None
    assert called["timeout"] == 2
    assert called["url"].endswith("/api/2.0/mlflow/registered-models/alias")


def test_predict_cli_writes_output(tmp_path, monkeypatch) -> None:
    import json
    import sys

    inp = tmp_path / "in.json"
    out = tmp_path / "out.json"
    inp.write_text('{"Location": "Sydney"}\n', encoding="utf-8")
    monkeypatch.setattr(
        predict,
        "predict",
        lambda _features: {
            "rain_tomorrow": False,
            "probability": 0.1,
            "model": {"name": "weather-rainfall-classifier", "source": "local"},
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["predict", "--input-json", str(inp), "--output", str(out)],
    )

    predict.main()

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["rain_tomorrow"] is False
    assert payload["model"]["source"] == "local"


def test_champion_model_uri_uses_alias() -> None:
    assert predict.champion_model_uri().endswith("@champion")


def test_describe_serving_skips_mlflow_for_health_probes(monkeypatch) -> None:
    monkeypatch.setattr(predict, "serving_model_info", lambda: None)
    monkeypatch.setattr(predict, "_local_model_path", lambda: None)

    def boom() -> None:
        raise AssertionError("health must not call the MLflow registry")

    monkeypatch.setattr(predict, "_champion_metadata", boom)

    assert predict.describe_serving_model(probe_registry=False) is None
