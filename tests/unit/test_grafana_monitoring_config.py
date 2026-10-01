from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _alerts() -> list[dict]:
    payload = yaml.safe_load(
        (ROOT / "docker/grafana/provisioning/alerting/alerts.yml").read_text(encoding="utf-8")
    )
    return [rule for group in payload["groups"] for rule in group["rules"]]


def test_rain_rate_alert_is_notification_only() -> None:
    rain_rate = next(rule for rule in _alerts() if rule["uid"] == "model-rain-rate-unusual")

    assert rain_rate["notification_settings"]["receiver"] != "airflow-retrain"


def test_airflow_receiver_targets_the_retraining_dag() -> None:
    contacts = yaml.safe_load(
        (ROOT / "docker/grafana/provisioning/alerting/contact-points.yml").read_text(
            encoding="utf-8"
        )
    )
    url = contacts["contactPoints"][0]["receivers"][0]["settings"]["url"]

    assert "/dags/weather_retrain/dagRuns" in url


def test_only_delayed_performance_gate_can_request_retraining() -> None:
    retrain = next(rule for rule in _alerts() if rule["uid"] == "model-retrain-requested")
    query = retrain["data"][0]["model"]["expr"]

    assert "weather_model_retrain_requested" in query
    assert retrain["notification_settings"]["receiver"] == "airflow-retrain"
