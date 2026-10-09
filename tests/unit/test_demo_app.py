import inspect

from weather_mlops.demo.app import (
    _dag_markup,
    _follow_deck,
    _grafana_embed_url,
    _grafana_panel_url,
    _render_demo,
    _render_model_health,
    _render_presentation,
)
from weather_mlops.demo.observability import DagTask


def test_grafana_embed_url_keeps_configured_parameters_and_adds_kiosk_mode() -> None:
    url = _grafana_embed_url("http://127.0.0.1:3000/d/weather-api/weather-api?orgId=1")

    assert url == ("http://127.0.0.1:3000/d/weather-api/weather-api?orgId=1&kiosk=&theme=dark")


def test_grafana_panel_url_uses_the_real_solo_panel_for_the_last_five_minutes() -> None:
    url = _grafana_panel_url("http://127.0.0.1:3000/d/weather-api/weather-api", 3)

    assert url == (
        "http://127.0.0.1:3000/d-solo/weather-api/weather-api?"
        "kiosk=&theme=dark&panelId=3&from=now-5m&to=now"
    )


def test_projected_demo_keeps_speaker_notes_in_the_separate_notes_view() -> None:
    assert "talk-notes" not in inspect.getsource(_render_demo)
    assert "speaker-notes" in inspect.getsource(_follow_deck)


def test_presentation_hands_off_to_the_demo_tab_without_rendering_it_twice() -> None:
    assert "_render_live(" not in inspect.getsource(_render_presentation)


def test_model_health_uses_airflow_lifecycle_not_synthetic_drift() -> None:
    health = inspect.getsource(_render_model_health)

    assert "Simulate drift" not in health
    assert "Refresh prepared data" in health
    assert "Train candidate and compare" in health
    assert "MLflow" in health


def test_model_health_keeps_manual_retraining_separate_from_drift_and_refresh_success() -> None:
    health = inspect.getsource(_render_model_health)

    assert "can_retrain = configured" in health
    assert "can_retrain = pipeline_state ==" not in health
    assert "No-drift runs do not block a manual retrain" in health
    assert "You can train now on the last completed" in health
    assert "Automatic retraining remains separate" in health


def test_airflow_task_flow_is_rendered_as_a_connected_dag() -> None:
    markup = _dag_markup((), {})
    success_markup = _dag_markup(
        (DagTask("ingest", "Ingest"),),
        {"ingest": "success"},
    )

    assert 'class="dag"' in markup
    assert 'class="dag__node success"' in success_markup
    assert "dag__marker" in success_markup
