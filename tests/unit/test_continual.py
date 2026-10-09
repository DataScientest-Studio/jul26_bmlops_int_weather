import json
from pathlib import Path

import pandas as pd

from weather_mlops.models.continual import (
    advance_model_versions,
    discover_ready_batches,
)


def _write_legacy_batch(directory: Path, start: str, end: str, row: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"open_meteo_backfill_{start}_{end}"
    (directory / f"{stem}.csv").write_text(
        "Date,Location,Humidity3pm,RainTomorrow\n" + row + "\n",
        encoding="utf-8",
    )
    (directory / f"{stem}.json").write_text("{}\n", encoding="utf-8")


def test_discover_ready_batches_reads_a_finished_location_shard_marker(tmp_path) -> None:
    shard_names = [
        "open_meteo_backfill_20170627_20170628_loc000.csv",
        "open_meteo_backfill_20170627_20170628_loc001.csv",
    ]
    for name in shard_names:
        (tmp_path / name).write_text("Date,Location\n2017-06-27,Sydney\n", encoding="utf-8")
    (tmp_path / "open_meteo_backfill_20170627_20170628.done").write_text(
        json.dumps(
            {
                "start_date": "2017-06-27",
                "end_date": "2017-06-28",
                "csv_files": shard_names,
            }
        ),
        encoding="utf-8",
    )

    ready = discover_ready_batches(tmp_path)

    assert [batch.batch_id for batch in ready] == ["20170627_20170628"]
    assert [path.name for path in ready[0].csv_paths] == shard_names


def test_discover_ready_batches_ignores_incomplete_location_shards(tmp_path) -> None:
    _write_legacy_batch(tmp_path, "20170627", "20170628", "2017-06-27,Sydney,40,No")
    (tmp_path / "open_meteo_backfill_20170701_20170702_loc000.csv").write_text(
        "Date,Location\n2017-07-01,Sydney\n",
        encoding="utf-8",
    )
    (tmp_path / "open_meteo_backfill_20170703_20170704.csv").write_text(
        "Date,Location\n2017-07-03,Sydney\n",
        encoding="utf-8",
    )

    ready = discover_ready_batches(tmp_path)

    assert [batch.batch_id for batch in ready] == ["20170627_20170628"]


def test_advance_walks_ready_chunks_and_remembers_them(tmp_path) -> None:
    incremental = tmp_path / "incremental"
    _write_legacy_batch(incremental, "20170627", "20170628", "2017-06-27,Sydney,40,No")
    _write_legacy_batch(incremental, "20170629", "20170630", "2017-06-29,Sydney,80,Yes")
    reference = tmp_path / "X_train.csv"
    reference.write_text("Humidity3pm,Location\n55,Sydney\n", encoding="utf-8")
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "Date,Location,Humidity3pm,RainTomorrow\n2016-01-01,Sydney,50,No\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "reports" / "ledger.json"
    trained: list[int] = []
    saved: list[str] = []

    class Snapshot:
        def save_html(self, path: str) -> None:
            saved.append(path)
            Path(path).write_text("report", encoding="utf-8")

    def drift(_reference: pd.DataFrame, _current: pd.DataFrame):
        return {"drift_detected": False, "share": 0.0, "drifted_columns": []}, Snapshot()

    def train(history, _holdout, output_path, _params):
        trained.append(len(history))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("candidate", encoding="utf-8")
        return {"roc_auc": 0.81, "recall": 0.8}

    kwargs = {
        "incremental_dir": incremental,
        "reference_features_path": reference,
        "seed_path": seed,
        "model_path": tmp_path / "missing.joblib",
        "ledger_path": ledger,
        "models_dir": tmp_path / "models",
        "max_batches": 1,
        "retrain": True,
        "drift_fn": drift,
        "train_fn": train,
    }
    first = advance_model_versions(**kwargs)
    second = advance_model_versions(**kwargs)
    third = advance_model_versions(**kwargs)

    assert first["processed"][0]["batch_id"] == "20170627_20170628"
    assert first["remaining"] == 1
    assert second["processed"][0]["batch_id"] == "20170629_20170630"
    assert second["processed"][0]["candidate_metrics"]["roc_auc"] == 0.81
    assert second["remaining"] == 0
    assert third["processed"] == []
    assert trained == [1, 2]
    assert saved
    stored = json.loads(ledger.read_text(encoding="utf-8"))
    assert stored["completed_batch_ids"] == ["20170627_20170628", "20170629_20170630"]


def test_low_production_recall_on_a_new_batch_requests_retrain(tmp_path) -> None:
    incremental = tmp_path / "incremental"
    _write_legacy_batch(incremental, "20170627", "20170628", "2017-06-27,Sydney,90,Yes")
    reference = tmp_path / "X_train.csv"
    reference.write_text("Humidity3pm,Location\n40,Sydney\n", encoding="utf-8")
    model_path = tmp_path / "model.joblib"
    model_path.write_text("not-a-model", encoding="utf-8")

    def drift(_reference, _current):
        return {"drift_detected": True, "share": 0.4, "drifted_columns": ["Humidity3pm"]}

    def score(_model, _frame):
        return {"recall": 0.4, "roc_auc": 0.7}

    outcome = advance_model_versions(
        incremental_dir=incremental,
        reference_features_path=reference,
        seed_path=tmp_path / "unused.csv",
        model_path=model_path,
        ledger_path=tmp_path / "ledger.json",
        models_dir=tmp_path / "models",
        retrain=False,
        champion_roc_auc=0.9,
        drift_fn=drift,
        score_fn=score,
        model_loader=lambda _path: object(),
    )

    performance = outcome["processed"][0]["performance"]
    assert performance["retrain"] is True
    assert performance["recall_failed"] is True
    assert outcome["processed"][0]["candidate_model"] is None
