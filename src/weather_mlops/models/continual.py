"""Check each new Open-Meteo chunk, then fit a local candidate on the data before it.

The production champion is left in place. Candidates land under ``models/continual``
and the ledger remembers which chunks were already checked, so the next run
continues with the following chunk.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml

from weather_mlops.config.settings import PROJECT_ROOT, settings
from weather_mlops.data.preprocess import (
    build_preprocessor,
    clean_dataframe,
    split_features_target,
)
from weather_mlops.models.evaluation import evaluate_classifier
from weather_mlops.monitoring.drift import (
    _cap_frame,
    evaluate_feature_drift,
    performance_decision,
)

LEDGER_PATH = PROJECT_ROOT / "reports" / "continual" / "ledger.json"
CANDIDATE_DIR = PROJECT_ROOT / "models" / "continual"


@dataclass(frozen=True)
class ReadyBatch:
    batch_id: str
    start_date: date
    end_date: date
    csv_paths: tuple[Path, ...]


@dataclass(frozen=True)
class CandidateParams:
    n_estimators: int = 250
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.9
    colsample_bytree: float = 0.9


def discover_ready_batches(incremental_dir: Path) -> list[ReadyBatch]:
    """Return date chunks that have a full CSV on disk, oldest first.

    A ``.done`` marker lists every location shard. A legacy chunk is one CSV
    plus its JSON, with no ``_loc`` suffix. Incomplete shards are ignored.
    """

    incremental_dir = Path(incremental_dir)
    if not incremental_dir.exists():
        return []
    found: dict[str, ReadyBatch] = {}
    for done in sorted(incremental_dir.glob("open_meteo_backfill_*.done")):
        if done.name.count("_") != 4:
            continue
        payload = json.loads(done.read_text(encoding="utf-8"))
        csvs = tuple(incremental_dir / name for name in payload.get("csv_files", []))
        if not csvs or not all(path.is_file() for path in csvs):
            continue
        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])
        batch_id = f"{start:%Y%m%d}_{end:%Y%m%d}"
        found[batch_id] = ReadyBatch(batch_id, start, end, csvs)
    for csv_path in sorted(incremental_dir.glob("open_meteo_backfill_*.csv")):
        stem = csv_path.stem
        prefix = "open_meteo_backfill_"
        if not stem.startswith(prefix) or "_loc" in stem:
            continue
        start_text, end_text = stem.removeprefix(prefix).split("_", maxsplit=1)
        if len(start_text) != 8 or len(end_text) != 8 or not start_text.isdigit():
            continue
        if not end_text.isdigit():
            continue
        batch_id = f"{start_text}_{end_text}"
        if batch_id in found or not csv_path.with_suffix(".json").is_file():
            continue
        start = datetime.strptime(start_text, "%Y%m%d").date()
        end = datetime.strptime(end_text, "%Y%m%d").date()
        found[batch_id] = ReadyBatch(batch_id, start, end, (csv_path,))
    return sorted(found.values(), key=lambda batch: (batch.start_date, batch.end_date))


def empty_ledger() -> dict[str, Any]:
    return {"completed_batch_ids": [], "batches": []}


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("completed_batch_ids", [])
    payload.setdefault("batches", [])
    return payload


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def load_model_params(path: Path) -> CandidateParams:
    if not path.exists():
        return CandidateParams()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    model = payload.get("model") or {}
    defaults = CandidateParams()
    return CandidateParams(
        n_estimators=int(model.get("n_estimators", defaults.n_estimators)),
        max_depth=int(model.get("max_depth", defaults.max_depth)),
        learning_rate=float(model.get("learning_rate", defaults.learning_rate)),
        subsample=float(model.get("subsample", defaults.subsample)),
        colsample_bytree=float(model.get("colsample_bytree", defaults.colsample_bytree)),
    )


def score_weather_batch(model: Any, frame: pd.DataFrame) -> dict[str, float]:
    """Score a WeatherAUS-shaped frame that still contains RainTomorrow."""

    cleaned = clean_dataframe(frame)
    features, target = split_features_target(cleaned)
    if len(target) < 2 or target.nunique() < 2:
        raise ValueError("Batch needs at least two rows and both rain labels to score.")
    probabilities = model.predict_proba(features)[:, 1]
    predictions = model.predict(features)
    metrics = evaluate_classifier(target, predictions, probabilities)
    return {name: float(value) for name, value in metrics.items()}


def fit_candidate_model(
    history: pd.DataFrame,
    holdout: pd.DataFrame,
    output_path: Path,
    params: CandidateParams,
) -> dict[str, float]:
    """Fit on history only and score the untouched holdout chunk."""

    from sklearn.pipeline import Pipeline
    from xgboost import XGBClassifier

    cleaned = clean_dataframe(history)
    features, target = split_features_target(cleaned)
    negative_count = int((target == 0).sum())
    positive_count = int((target == 1).sum())
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0
    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(features)),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=params.n_estimators,
                    max_depth=params.max_depth,
                    learning_rate=params.learning_rate,
                    subsample=params.subsample,
                    colsample_bytree=params.colsample_bytree,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    scale_pos_weight=scale_pos_weight,
                    random_state=settings.random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(features, target)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)
    return score_weather_batch(pipeline, holdout)


def _default_drift(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[dict[str, Any], Any]:
    return evaluate_feature_drift(_cap_frame(reference), _cap_frame(current))


def _drift_summary(
    drift_fn: Callable[[pd.DataFrame, pd.DataFrame], Any],
    reference: pd.DataFrame,
    current: pd.DataFrame,
    report_path: Path,
) -> dict[str, Any]:
    result = drift_fn(reference, current)
    snapshot = None
    if isinstance(result, tuple):
        summary, snapshot = result
    elif isinstance(result, dict) and "snapshot" in result:
        snapshot = result.get("snapshot")
        summary = dict(result.get("summary") or {})
    else:
        summary = dict(result)
    if snapshot is not None and hasattr(snapshot, "save_html"):
        report_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot.save_html(str(report_path))
        summary = {**summary, "report_html_path": str(report_path)}
    return json.loads(json.dumps(summary, default=str))


def _read_frames(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    return pd.concat(frames, ignore_index=True)


def advance_model_versions(
    *,
    incremental_dir: Path,
    reference_features_path: Path,
    seed_path: Path,
    model_path: Path,
    ledger_path: Path,
    models_dir: Path,
    max_batches: int = 1,
    retrain: bool = True,
    champion_roc_auc: float | None = None,
    params: CandidateParams | None = None,
    drift_fn: Callable[[pd.DataFrame, pd.DataFrame], Any] = _default_drift,
    score_fn: Callable[[Any, pd.DataFrame], dict[str, float]] = score_weather_batch,
    train_fn: Callable[
        [pd.DataFrame, pd.DataFrame, Path, CandidateParams],
        dict[str, float],
    ] = fit_candidate_model,
    model_loader: Callable[[Path], Any] = joblib.load,
) -> dict[str, Any]:
    """Check the next unseen ready chunks and append them to the ledger."""

    if max_batches < 1:
        raise ValueError("max_batches must be positive.")
    params = params or CandidateParams()
    ready = discover_ready_batches(incremental_dir)
    ledger = load_ledger(ledger_path)
    seen = set(ledger["completed_batch_ids"])
    pending = [batch for batch in ready if batch.batch_id not in seen]
    selected = pending[:max_batches]
    if not selected:
        return {
            "processed": [],
            "remaining": 0,
            "ready": len(ready),
            "ledger_path": str(ledger_path),
        }
    if not reference_features_path.exists():
        raise FileNotFoundError(
            f"No reference features at {reference_features_path}. Train or dvc-pull first."
        )
    reference = pd.read_csv(reference_features_path)
    model = model_loader(model_path) if model_path.exists() else None
    reports_dir = ledger_path.parent
    processed: list[dict[str, Any]] = []

    for batch in selected:
        frame = _read_frames(list(batch.csv_paths))
        drift = _drift_summary(
            drift_fn,
            reference,
            frame,
            reports_dir / f"{batch.batch_id}_drift.html",
        )
        production_metrics = None
        performance = None
        score_error = None
        if model is not None:
            try:
                production_metrics = score_fn(model, frame)
                performance = performance_decision(
                    production_metrics,
                    champion_roc_auc=champion_roc_auc,
                )
            except ValueError as error:
                score_error = str(error)
        candidate_path = None
        candidate_metrics = None
        if retrain:
            earlier = [
                path
                for earlier_batch in ready
                if earlier_batch.end_date < batch.start_date
                for path in earlier_batch.csv_paths
            ]
            history_paths = [seed_path, *earlier]
            missing = [path for path in history_paths if not path.exists()]
            if missing:
                missing_list = ", ".join(str(path) for path in missing)
                raise FileNotFoundError(f"Retrain history is missing: {missing_list}")
            candidate_path = models_dir / f"rain_{batch.batch_id}.joblib"
            candidate_metrics = train_fn(
                _read_frames(history_paths),
                frame,
                candidate_path,
                params,
            )
        entry = {
            "batch_id": batch.batch_id,
            "start_date": batch.start_date.isoformat(),
            "end_date": batch.end_date.isoformat(),
            "rows": int(len(frame)),
            "feature_drift": drift,
            "production_metrics": production_metrics,
            "performance": performance,
            "score_error": score_error,
            "candidate_model": str(candidate_path) if candidate_path else None,
            "candidate_metrics": candidate_metrics,
        }
        ledger["completed_batch_ids"].append(batch.batch_id)
        ledger["batches"].append(entry)
        save_ledger(ledger_path, ledger)
        processed.append(entry)

    return {
        "processed": processed,
        "remaining": len(pending) - len(selected),
        "ready": len(ready),
        "ledger_path": str(ledger_path),
    }


def _champion_auc_from_file(path: Path) -> float | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("roc_auc", "validation_roc_auc"):
        if payload.get(key) is not None:
            return float(payload[key])
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Score the next completed Open-Meteo chunk with Evidently and the "
            "production model, then fit a local candidate on earlier data. "
            "Re-run to check the following chunk. Candidates are not promoted."
        )
    )
    parser.add_argument("--incremental-dir", type=Path, default=settings.raw_incremental_dir)
    parser.add_argument("--reference-features", type=Path, default=settings.x_train_path)
    parser.add_argument("--seed", type=Path, default=settings.seed_raw_data_path)
    parser.add_argument("--model", type=Path, default=settings.model_path)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--models-dir", type=Path, default=CANDIDATE_DIR)
    parser.add_argument("--params", type=Path, default=PROJECT_ROOT / "params.yaml")
    parser.add_argument("--validation-metrics", type=Path, default=settings.validation_metrics_path)
    parser.add_argument("--max-batches", type=int, default=1)
    parser.add_argument(
        "--champion-roc-auc",
        type=float,
        help="Production validation ROC-AUC. Defaults to reports/metrics/validation.json.",
    )
    parser.add_argument(
        "--no-retrain",
        action="store_true",
        help="Run Evidently and score the production model without fitting a candidate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    champion_roc_auc = (
        args.champion_roc_auc
        if args.champion_roc_auc is not None
        else _champion_auc_from_file(args.validation_metrics)
    )
    outcome = advance_model_versions(
        incremental_dir=args.incremental_dir,
        reference_features_path=args.reference_features,
        seed_path=args.seed,
        model_path=args.model,
        ledger_path=args.ledger,
        models_dir=args.models_dir,
        max_batches=args.max_batches,
        retrain=not args.no_retrain,
        champion_roc_auc=champion_roc_auc,
        params=load_model_params(args.params),
    )
    if not outcome["processed"]:
        print(
            "No new Open-Meteo chunks to check. "
            f"{outcome['ready']} ready, ledger at {outcome['ledger_path']}."
        )
        return
    for entry in outcome["processed"]:
        drift = entry["feature_drift"]
        production = entry.get("production_metrics") or {}
        candidate = entry.get("candidate_metrics") or {}
        print(
            f"{entry['batch_id']}: rows={entry['rows']} "
            f"drift={drift.get('drift_detected')} "
            f"production_auc={production.get('roc_auc')} "
            f"candidate_auc={candidate.get('roc_auc')} "
            f"retrain={bool((entry.get('performance') or {}).get('retrain'))}"
        )
    print(
        f"Checked {len(outcome['processed'])} chunk(s); "
        f"{outcome['remaining']} still waiting. Ledger: {outcome['ledger_path']}"
    )


if __name__ == "__main__":
    main()
