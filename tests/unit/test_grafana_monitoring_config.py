import json
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


def test_weather_model_dashboard_includes_evidently_batch_metrics() -> None:
    dashboard = json.loads(
        (ROOT / "docker/grafana/dashboards/grafana_model.json").read_text(encoding="utf-8")
    )
    expressions = {
        target.get("expr", "")
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    }

    assert {
        "time() - weather_evidently_report_timestamp_seconds",
        "weather_evidently_drifted_column_share",
        "weather_model_labeled_predictions",
        "weather_model_delayed_recall",
        "weather_model_delayed_roc_auc",
        "weather_model_retrain_requested",
    } <= expressions


def test_evidently_airflow_task_receives_monitoring_and_supabase_environment() -> None:
    dag = (ROOT / "airflow/dags/weather_dag.py").read_text(encoding="utf-8")
    task_start = dag.index('task_id="evidently_monitor"')
    task = dag[task_start : dag.index("with DAG(", task_start)]

    assert '"PUSHGATEWAY_URL": "http://pushgateway:9091"' in task
    assert '"SUPABASE_URL": os.environ.get("SUPABASE_URL")' in task
    assert '"SUPABASE_KEY": os.environ.get("SUPABASE_KEY")' in task


def test_monitoring_and_airflow_hydrate_operational_credentials_from_vault() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    airflow = (ROOT / "airflow/docker-compose.yml").read_text(encoding="utf-8")

    assert "with_vault_env.py --monitoring" in makefile
    assert "up -d prometheus pushgateway grafana" in makefile
    assert "_AIRFLOW_WWW_USER_USERNAME: ${AIRFLOW_API_USER}" in airflow
    assert "_AIRFLOW_WWW_USER_PASSWORD: ${AIRFLOW_API_PASSWORD}" in airflow
