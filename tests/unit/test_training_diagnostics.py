from weather_mlops.config.settings import Settings


def test_mlflow_recall_guardrail_defaults_to_production_threshold(monkeypatch) -> None:
    monkeypatch.delenv("MLFLOW_MIN_RECALL", raising=False)

    assert Settings().mlflow_min_recall == 0.75


def test_mlflow_recall_guardrail_can_be_overridden_for_local_demonstrations(monkeypatch) -> None:
    monkeypatch.setenv("MLFLOW_MIN_RECALL", "0.60")

    assert Settings().mlflow_min_recall == 0.60
