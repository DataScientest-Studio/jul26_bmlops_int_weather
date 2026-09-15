from weather_mlops.models.tracking import log_training_run, save_mlflow_run_metadata


def test_log_training_run_skips_when_tracking_uri_is_unset(monkeypatch) -> None:
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_tracking_uri",
        None,
    )

    run_id = log_training_run(
        pipeline=object(),
        metrics={"f1": 0.5},
        manifest={"sha256": "abc"},
        n_estimators=10,
        max_depth=2,
        learning_rate=0.1,
        subsample=1.0,
        colsample_bytree=1.0,
        train_rows=4,
        scale_pos_weight=1.0,
        negative_count=3,
        positive_count=1,
    )

    assert run_id is None


def test_save_mlflow_run_metadata_writes_json(tmp_path, monkeypatch) -> None:
    path = tmp_path / "mlflow_run.json"
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_run_metadata_path",
        path,
    )

    save_mlflow_run_metadata("run-1", "weather-rainfall-classifier", "3")

    assert path.read_text(encoding="utf-8")
    assert "run-1" in path.read_text(encoding="utf-8")
    assert '"model_version": "3"' in path.read_text(encoding="utf-8")
