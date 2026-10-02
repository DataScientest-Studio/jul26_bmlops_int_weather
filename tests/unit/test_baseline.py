import pandas as pd
import pytest

from weather_mlops.data.manifest import verify_processed_manifest


def _weather_frame(days: int = 300) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.date_range("2016-01-01", periods=days).repeat(2),
            "Location": ["Sydney", "Melbourne"] * days,
            "MinTemp": [float(index % 20) for index in range(days * 2)],
            "RainTomorrow": ["Yes" if index % 3 else "No" for index in range(days * 2)],
        }
    )


def test_prepare_baseline_splits_uses_full_history_for_selection_and_refit(tmp_path) -> None:
    from weather_mlops.models.baseline import prepare_baseline_splits

    raw_path = tmp_path / "weatherAUS.csv"
    _weather_frame().to_csv(raw_path, index=False)

    receipt = prepare_baseline_splits(
        raw_path=raw_path,
        selection_dir=tmp_path / "selection",
        refit_dir=tmp_path / "refit",
        validation_window_days=90,
        test_window_days=90,
    )

    selection_manifest = verify_processed_manifest(tmp_path / "selection")
    refit_manifest = verify_processed_manifest(tmp_path / "refit")

    # 300 calendar days x 2 locations: first 120 days tune, then 90 validation, 90 test.
    assert len(pd.read_csv(tmp_path / "selection" / "X_train.csv")) == 240
    assert len(pd.read_csv(tmp_path / "selection" / "X_validation.csv")) == 180
    assert len(pd.read_csv(tmp_path / "selection" / "X_test.csv")) == 180
    assert len(pd.read_csv(tmp_path / "refit" / "X_train.csv")) == 600
    assert selection_manifest["split"]["training_window_days"] is None
    assert refit_manifest["split"]["fit_scope"] == "all_kaggle_rows"
    assert refit_manifest["split"]["selection_manifest_sha256"] == selection_manifest["sha256"]
    assert receipt["selection_manifest_sha256"] == selection_manifest["sha256"]


def test_write_selected_parameters_keeps_search_result_out_of_versioned_params(tmp_path) -> None:
    from weather_mlops.models.baseline import write_selected_parameters

    selected_path = tmp_path / "selected_params.yaml"
    write_selected_parameters(
        selected_path,
        params={
            "n_estimators": 150,
            "max_depth": 3,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.9,
        },
        selection_manifest_sha256="selection-sha",
        selection_run_id="selection-run",
    )

    payload = selected_path.read_text(encoding="utf-8")
    assert "n_estimators: 150" in payload
    assert "selection_manifest_sha256: selection-sha" in payload
    assert "selection_run_id: selection-run" in payload


def test_random_search_records_each_validation_trial_and_selects_one() -> None:
    from weather_mlops.models.baseline import run_random_search

    frame = _weather_frame(days=120)
    X_train = frame.iloc[:160].drop(columns=["Date", "RainTomorrow"])
    y_train = (frame.iloc[:160]["RainTomorrow"] == "Yes").astype(int)
    X_validation = frame.iloc[160:].drop(columns=["Date", "RainTomorrow"])
    y_validation = (frame.iloc[160:]["RainTomorrow"] == "Yes").astype(int)

    result = run_random_search(
        X_train=X_train,
        y_train=y_train,
        X_validation=X_validation,
        y_validation=y_validation,
        search_space={
            "n_estimators": [5, 10],
            "max_depth": [2],
            "learning_rate": [0.1],
            "subsample": [1.0],
            "colsample_bytree": [1.0],
        },
        n_iter=2,
        random_state=7,
    )

    assert len(result["trials"]) == 2
    assert result["best_params"] in [trial["params"] for trial in result["trials"]]
    assert all("roc_auc" in trial["validation_metrics"] for trial in result["trials"])
    assert result["best_validation_metrics"] == max(
        (trial["validation_metrics"] for trial in result["trials"]),
        key=lambda metrics: (metrics["roc_auc"], metrics["recall"]),
    )


def test_random_search_rejects_more_trials_than_the_discrete_search_space() -> None:
    from weather_mlops.models.baseline import run_random_search

    frame = _weather_frame(days=20)
    X = frame.drop(columns=["Date", "RainTomorrow"])
    y = (frame["RainTomorrow"] == "Yes").astype(int)

    with pytest.raises(ValueError, match="at most 1"):
        run_random_search(
            X_train=X,
            y_train=y,
            X_validation=X,
            y_validation=y,
            search_space={
                "n_estimators": [5],
                "max_depth": [2],
                "learning_rate": [0.1],
                "subsample": [1.0],
                "colsample_bytree": [1.0],
            },
            n_iter=2,
            random_state=7,
        )


def test_log_hyperparameter_search_persists_parent_and_trial_evidence(
    tmp_path, monkeypatch
) -> None:
    from mlflow.tracking import MlflowClient

    from weather_mlops.models.baseline import log_hyperparameter_search

    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setattr("weather_mlops.models.baseline.settings.mlflow_tracking_uri", tracking_uri)
    monkeypatch.setattr(
        "weather_mlops.models.baseline.settings.mlflow_experiment_name",
        "baseline-test",
    )
    result = {
        "search_strategy": "randomized_discrete",
        "random_state": 7,
        "best_params": {"n_estimators": 10, "max_depth": 2},
        "best_validation_metrics": {"roc_auc": 0.88, "recall": 0.76},
        "trials": [
            {
                "trial": 1,
                "params": {"n_estimators": 10, "max_depth": 2},
                "validation_metrics": {"roc_auc": 0.88, "recall": 0.76},
            }
        ],
    }

    run_id = log_hyperparameter_search(
        search_result=result,
        selection_manifest={"sha256": "selection-sha", "split": {"test_end": "2017-06-25"}},
    )

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    assert run.data.tags["stage"] == "baseline_selection"
    assert run.data.tags["dataset_sha256"] == "selection-sha"
    assert run.data.params["best_n_estimators"] == "10"
    assert run.data.metrics["best_validation_roc_auc"] == 0.88
    assert {artifact.path for artifact in client.list_artifacts(run_id)} == {"selection"}
    child_runs = client.search_runs(
        experiment_ids=[run.info.experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{run_id}'",
    )
    assert len(child_runs) == 1
    assert child_runs[0].data.metrics["validation_roc_auc"] == 0.88


def test_run_baseline_refits_all_kaggle_rows_and_bootstraps_empty_registry(
    tmp_path, monkeypatch
) -> None:
    from mlflow.tracking import MlflowClient

    from weather_mlops.models import baseline, tracking

    raw_path = tmp_path / "weatherAUS.csv"
    _weather_frame(days=300).to_csv(raw_path, index=False)
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setattr(baseline.settings, "mlflow_tracking_uri", tracking_uri)
    monkeypatch.setattr(baseline.settings, "mlflow_experiment_name", "baseline-workflow-test")
    monkeypatch.setattr(baseline.settings, "mlflow_model_name", "baseline-workflow-model")
    monkeypatch.setattr(
        baseline.settings,
        "model_path",
        tmp_path / "models" / "rain_classifier.joblib",
    )
    monkeypatch.setattr(
        baseline.settings, "best_model_path", tmp_path / "models" / "champion.joblib"
    )
    monkeypatch.setattr(
        baseline.settings,
        "mlflow_run_metadata_path",
        tmp_path / "reports" / "mlflow_run.json",
    )
    monkeypatch.setattr(tracking, "current_git_commit", lambda: "test-commit")
    monkeypatch.setattr(baseline, "current_git_commit", lambda: "test-commit")
    monkeypatch.setattr(baseline.settings, "supabase_url", None)
    monkeypatch.setattr(baseline.settings, "supabase_key", None)

    receipt = baseline.run_baseline(
        raw_path=raw_path,
        selection_dir=tmp_path / "selection",
        refit_dir=tmp_path / "refit",
        selected_params_path=tmp_path / "reports" / "selected_params.yaml",
        model_output_path=baseline.settings.model_path,
        train_metrics_path=tmp_path / "reports" / "train.json",
        validation_metrics_path=tmp_path / "reports" / "validation.json",
        test_metrics_path=tmp_path / "reports" / "test.json",
        validation_window_days=90,
        test_window_days=90,
        search_space={
            "n_estimators": [5],
            "max_depth": [2],
            "learning_rate": [0.1],
            "subsample": [1.0],
            "colsample_bytree": [1.0],
        },
        n_iter=1,
        random_state=7,
        register_snapshots=False,
    )

    assert receipt["decision"] == "baseline_bootstrap"
    assert (tmp_path / "models" / "champion.joblib").read_bytes() == (
        tmp_path / "models" / "rain_classifier.joblib"
    ).read_bytes()
    assert (
        "selection_manifest_sha256" in (tmp_path / "reports" / "selected_params.yaml").read_text()
    )
    validation_report = pd.read_json(tmp_path / "reports" / "validation.json", typ="series")
    test_report = pd.read_json(tmp_path / "reports" / "test.json", typ="series")
    assert validation_report["validation_rows"] == 180
    assert test_report["test_rows"] == 180
    client = MlflowClient(tracking_uri=tracking_uri)
    champion = client.get_model_version_by_alias("baseline-workflow-model", "champion")
    assert champion.run_id == receipt["model_run_id"]


def test_load_baseline_config_reads_a_bounded_random_search(tmp_path) -> None:
    from weather_mlops.models.baseline import load_baseline_config

    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        """baseline:
  validation_window_days: 90
  test_window_days: 90
  search:
    n_iter: 2
    random_state: 7
    parameter_space:
      n_estimators: [10, 20]
      max_depth: [2]
      learning_rate: [0.1]
      subsample: [1.0]
      colsample_bytree: [1.0]
""",
        encoding="utf-8",
    )

    config = load_baseline_config(params_path)

    assert config["validation_window_days"] == 90
    assert config["test_window_days"] == 90
    assert config["n_iter"] == 2
    assert config["search_space"]["n_estimators"] == [10, 20]


def test_project_baseline_configuration_is_a_bounded_search() -> None:
    from weather_mlops.config.settings import PROJECT_ROOT
    from weather_mlops.models.baseline import load_baseline_config

    config = load_baseline_config(PROJECT_ROOT / "params.yaml")

    assert config["n_iter"] == 12
    assert config["validation_window_days"] == 90
    assert config["test_window_days"] == 90
    assert config["n_iter"] < 3 * 3 * 2 * 2 * 2


def test_register_baseline_snapshots_registers_raw_selection_and_refit(
    monkeypatch, tmp_path
) -> None:
    from weather_mlops.models import baseline

    calls = []
    monkeypatch.setattr(
        baseline,
        "register_local_snapshot",
        lambda path, **kwargs: calls.append(("raw", path, kwargs)),
    )
    monkeypatch.setattr(
        baseline,
        "register_processed_snapshot",
        lambda path, **kwargs: calls.append(("processed", path, kwargs)),
    )

    baseline.register_baseline_snapshots(
        raw_path=tmp_path / "weatherAUS.csv",
        selection_dir=tmp_path / "selection",
        refit_dir=tmp_path / "refit",
    )

    assert calls == [
        ("raw", tmp_path / "weatherAUS.csv", {"source": "weatherAUS-kaggle"}),
        ("processed", tmp_path / "selection", {"source": "weatherAUS-kaggle-selection"}),
        ("processed", tmp_path / "refit", {"source": "weatherAUS-kaggle-full-refit"}),
    ]
