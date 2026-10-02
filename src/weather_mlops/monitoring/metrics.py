"""Publish compact batch-monitoring summaries to Prometheus Pushgateway."""

from __future__ import annotations

import time
from typing import Any

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


def push_monitoring_metrics(
    result: dict[str, Any],
    *,
    gateway_url: str,
    registry: CollectorRegistry | None = None,
) -> None:
    """Push only numeric Evidently summaries; detailed reports stay as artifacts."""

    registry = registry or CollectorRegistry()
    feature = result.get("feature_drift") or {}
    performance = result.get("performance") or {}
    performance_metrics = performance.get("metrics") or {}
    labeled = float(performance.get("labeled_predictions") or 0)

    feature_drift = Gauge(
        "weather_evidently_feature_drift_detected", "Feature drift detected", registry=registry
    )
    feature_drift.set(float(bool(feature.get("drift_detected"))))
    drift_share = Gauge(
        "weather_evidently_drifted_column_share", "Share of drifted columns", registry=registry
    )
    drift_share.set(float(feature.get("share") or 0))
    labeled_predictions = Gauge(
        "weather_model_labeled_predictions", "Labelled prediction count", registry=registry
    )
    labeled_predictions.set(labeled)
    Gauge("weather_model_delayed_recall", "Delayed labelled recall", registry=registry).set(
        float(performance_metrics.get("recall") or 0)
    )
    Gauge("weather_model_delayed_roc_auc", "Delayed labelled ROC-AUC", registry=registry).set(
        float(performance_metrics.get("roc_auc") or 0)
    )
    retrain_requested = Gauge(
        "weather_model_retrain_requested", "Delayed-performance retrain request", registry=registry
    )
    retrain_requested.set(float(bool(performance.get("retrain"))))
    report_timestamp = Gauge(
        "weather_evidently_report_timestamp_seconds", "Latest report time", registry=registry
    )
    report_timestamp.set(time.time())
    push_to_gateway(gateway_url, job="weather_monitoring", registry=registry)
