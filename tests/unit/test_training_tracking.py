from weather_mlops.models import training


def test_optional_training_tracking_can_be_skipped(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(training, "log_training_run", lambda **kwargs: calls.append(kwargs))

    result = training._log_training_run_if_enabled(enabled=False, marker="demo")

    assert result is None
    assert calls == []


def test_training_tracking_remains_enabled_by_default(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        training,
        "log_training_run",
        lambda **kwargs: calls.append(kwargs) or {"run_id": "run-1"},
    )

    result = training._log_training_run_if_enabled(enabled=True, marker="release")

    assert result == {"run_id": "run-1"}
    assert calls == [{"marker": "release"}]
