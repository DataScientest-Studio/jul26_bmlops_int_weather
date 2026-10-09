from weather_mlops.demo.observability import (
    PIPELINE_TASKS,
    RETRAIN_TASKS,
    ApiTelemetry,
    ModelTelemetry,
    load_api_telemetry,
    load_model_telemetry,
    load_task_states,
    request_simulated_drift,
    scalar_or_none,
    scalar_result,
)


def test_scalar_result_reads_prometheus_instant_vector() -> None:
    assert scalar_result({"status": "success", "data": {"result": [{"value": [0, "2.5"]}]}}) == 2.5


def test_scalar_result_uses_zero_for_no_series() -> None:
    assert scalar_result({"status": "success", "data": {"result": []}}) == 0.0


def test_load_api_telemetry_queries_all_dashboard_figures() -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "success", "data": {"result": [{"value": [0, "3"]}]}}

    calls = []

    def fake_get(url: str, **kwargs) -> Response:
        calls.append((url, kwargs["params"]["query"]))
        return Response()

    telemetry = load_api_telemetry("http://prometheus:9090", get=fake_get)

    assert telemetry == ApiTelemetry(3.0, 3.0, 3.0, 3.0)
    assert len(calls) == 4
    assert all(url == "http://prometheus:9090/api/v1/query" for url, _ in calls)


def test_scalar_or_none_distinguishes_a_missing_series() -> None:
    assert scalar_or_none({"status": "success", "data": {"result": []}}) is None
    assert scalar_or_none({"status": "success", "data": {"result": [{"value": [0, "1"]}]}}) == 1.0


def test_load_model_telemetry_reads_the_retrain_gate() -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "success", "data": {"result": [{"value": [0, "1"]}]}}

    telemetry = load_model_telemetry(
        "http://prometheus:9090",
        get=lambda *args, **kwargs: Response(),
    )

    assert telemetry == ModelTelemetry(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)


def test_load_task_states_reads_the_latest_run() -> None:
    calls = []

    class Response:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    def fake_get(url: str, **kwargs):
        calls.append(url)
        if url.endswith("/dagRuns"):
            return Response({"dag_runs": [{"dag_run_id": "manual__1"}]})
        return Response({"task_instances": [{"task_id": "train", "state": "success"}]})

    states = load_task_states(
        "http://airflow-webserver:8080",
        "weather_retrain",
        auth=("admin", "secret"),
        get=fake_get,
    )

    assert states == {"train": "success"}
    assert calls[0].endswith("/dags/weather_retrain/dagRuns")
    assert [task.task_id for task in PIPELINE_TASKS] == [
        "ingestion",
        "preprocess",
        "reconcile_outcomes",
        "evidently_monitor",
    ]
    assert [task.task_id for task in RETRAIN_TASKS] == ["train", "evaluation", "compare"]


def test_request_simulated_drift_posts_to_the_api() -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"retrain": True}

    calls = []

    def fake_post(url: str, **kwargs):
        calls.append((url, kwargs["auth"], kwargs["verify"]))
        return Response()

    body = request_simulated_drift(
        "https://nginx",
        auth=("weather", "secret"),
        post=fake_post,
        verify=False,
    )

    assert body == {"retrain": True}
    assert calls == [("https://nginx/monitor/simulate", ("weather", "secret"), False)]
