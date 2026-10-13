"""Small, read-only Prometheus client used by the Streamlit demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class ApiTelemetry:
    """The four compact API figures shown beside a live prediction."""

    requests: float
    predictions: float
    error_rate: float
    average_latency_seconds: float


QUERIES = {
    "requests": "sum(increase(http_requests_total[5m])) or vector(0)",
    "predictions": (
        'sum(increase(http_requests_total{handler="/predict/live_data"}[5m])) or vector(0)'
    ),
    "error_rate": (
        '(sum(increase(http_requests_total{status=~"4xx|5xx"}[5m])) or vector(0)) '
        "/ clamp_min(sum(increase(http_requests_total[5m])), 1)"
    ),
    "average_latency_seconds": (
        'sum(increase(http_request_duration_seconds_sum{handler!="/train"}[5m])) '
        '/ clamp_min(sum(increase(http_request_duration_seconds_count{handler!="/train"}[5m])), 1)'
    ),
}


def scalar_result(payload: dict[str, Any]) -> float:
    """Extract the first instant-vector value, treating an empty result as zero."""

    if payload.get("status") != "success":
        raise ValueError("Prometheus did not return a successful query result.")
    result = payload.get("data", {}).get("result", [])
    if not result:
        return 0.0
    value = result[0].get("value", [None, 0])
    return float(value[1])


@dataclass(frozen=True)
class ModelTelemetry:
    """The batch figures on the Weather Model Grafana dashboard."""

    drift_detected: float | None
    drift_share: float | None
    delayed_recall: float | None
    delayed_roc_auc: float | None
    retrain_requested: float | None
    report_age_seconds: float | None


@dataclass(frozen=True)
class DagTask:
    task_id: str
    label: str


PIPELINE_TASKS = (
    DagTask("ingestion", "Ingest"),
    DagTask("preprocess", "Preprocess"),
    DagTask("register_dataset", "Version + persist"),
    DagTask("reconcile_outcomes", "Label outcomes"),
    DagTask("evidently_monitor", "Evidently"),
)
RETRAIN_TASKS = (
    DagTask("train", "Train"),
    DagTask("evaluation", "Evaluate"),
    DagTask("compare", "Compare"),
)

MODEL_QUERIES = {
    "drift_detected": "weather_evidently_feature_drift_detected",
    "drift_share": "weather_evidently_drifted_column_share",
    "delayed_recall": "weather_model_delayed_recall",
    "delayed_roc_auc": "weather_model_delayed_roc_auc",
    "retrain_requested": "weather_model_retrain_requested",
    "report_age_seconds": "time() - weather_evidently_report_timestamp_seconds",
}


def scalar_or_none(payload: dict[str, Any]) -> float | None:
    """Same instant-vector read as ``scalar_result``, with an empty series as missing."""

    if payload.get("status") != "success":
        raise ValueError("Prometheus did not return a successful query result.")
    result = payload.get("data", {}).get("result", [])
    if not result:
        return None
    value = result[0].get("value", [None, None])
    if value[1] is None:
        return None
    return float(value[1])


def load_api_telemetry(
    prometheus_url: str,
    *,
    get: Any = requests.get,
    timeout: float = 2,
) -> ApiTelemetry:
    """Read the same compact figures that back the API Grafana dashboard."""

    base_url = prometheus_url.rstrip("/")
    values = {}
    for name, query in QUERIES.items():
        response = get(
            f"{base_url}/api/v1/query",
            params={"query": query},
            timeout=timeout,
        )
        response.raise_for_status()
        values[name] = scalar_result(response.json())
    return ApiTelemetry(**values)


def _query_scalars(
    prometheus_url: str,
    queries: dict[str, str],
    *,
    get: Any,
    timeout: float,
    reader: Any,
) -> dict[str, float | None]:
    base_url = prometheus_url.rstrip("/")
    values: dict[str, float | None] = {}
    for name, query in queries.items():
        response = get(
            f"{base_url}/api/v1/query",
            params={"query": query},
            timeout=timeout,
        )
        response.raise_for_status()
        values[name] = reader(response.json())
    return values


def load_model_telemetry(
    prometheus_url: str,
    *,
    get: Any = requests.get,
    timeout: float = 2,
) -> ModelTelemetry:
    """Read the Evidently and retrain figures Grafana alerts on."""

    values = _query_scalars(
        prometheus_url,
        MODEL_QUERIES,
        get=get,
        timeout=timeout,
        reader=scalar_or_none,
    )
    return ModelTelemetry(**values)


def load_task_states(
    airflow_url: str,
    dag_id: str,
    *,
    run_id: str | None = None,
    auth: tuple[str, str] | None = None,
    get: Any = requests.get,
    timeout: float = 3,
) -> dict[str, str]:
    """Map task id to an Airflow run state, using the latest run when none is specified."""

    base_url = airflow_url.rstrip("/")
    if run_id is None:
        runs = get(
            f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
            params={"limit": 1, "order_by": "-start_date"},
            auth=auth,
            timeout=timeout,
        )
        runs.raise_for_status()
        dag_runs = runs.json().get("dag_runs") or []
        if not dag_runs:
            return {}
        run_id = str(dag_runs[0]["dag_run_id"])
    tasks = get(
        f"{base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances",
        auth=auth,
        timeout=timeout,
    )
    tasks.raise_for_status()
    return {
        item["task_id"]: str(item.get("state") or "none")
        for item in tasks.json().get("task_instances") or []
    }


def load_dag_run_state(
    airflow_url: str,
    dag_id: str,
    run_id: str,
    *,
    auth: tuple[str, str] | None = None,
    get: Any = requests.get,
    timeout: float = 3,
) -> str:
    """Read the exact manually-triggered Airflow run, never a later scheduled run."""

    response = get(
        f"{airflow_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns/{run_id}",
        auth=auth,
        timeout=timeout,
    )
    response.raise_for_status()
    state = response.json().get("state")
    if not state:
        raise ValueError("Airflow returned a DAG run without a state.")
    return str(state)


def trigger_dag_run(
    airflow_url: str,
    dag_id: str,
    *,
    conf: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    post: Any = requests.post,
    timeout: float = 10,
) -> str:
    """Create an Airflow DAG run and return its immutable run identifier."""

    response = post(
        f"{airflow_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns",
        json={"conf": conf or {}},
        auth=auth,
        timeout=timeout,
    )
    response.raise_for_status()
    run_id = response.json().get("dag_run_id")
    if not run_id:
        raise ValueError("Airflow accepted the trigger without returning a DAG run id.")
    return str(run_id)


def request_simulated_drift(
    api_url: str,
    *,
    auth: tuple[str, str] | None = None,
    post: Any = requests.post,
    timeout: float = 120,
    verify: bool = True,
) -> dict[str, Any]:
    """Ask the API to run the synthetic drift check and arm the retrain gate."""

    response = post(
        f"{api_url.rstrip('/')}/monitor/simulate",
        auth=auth,
        timeout=timeout,
        verify=verify,
    )
    response.raise_for_status()
    return response.json()
