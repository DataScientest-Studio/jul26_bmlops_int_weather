from prometheus_client import CollectorRegistry

from weather_mlops.monitoring.metrics import push_monitoring_metrics


def _metric_value(registry: CollectorRegistry, name: str) -> float:
    for family in registry.collect():
        if family.name == name:
            return float(family.samples[0].value)
    raise AssertionError(f"Metric {name} not found")


def test_push_monitoring_metrics_exports_insufficient_history(monkeypatch) -> None:
    registry = CollectorRegistry()
    monkeypatch.setattr(
        "weather_mlops.monitoring.metrics.push_to_gateway", lambda *args, **kwargs: None
    )

    push_monitoring_metrics(
        {"feature_drift": {"share": 0.0, "drift_detected": False}, "performance": None},
        gateway_url="http://pushgateway:9091",
        registry=registry,
    )

    assert _metric_value(registry, "weather_model_labeled_predictions") == 0
    assert _metric_value(registry, "weather_model_retrain_requested") == 0
