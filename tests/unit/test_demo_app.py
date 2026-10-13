import inspect

import weather_mlops.demo.app as demo_app
from weather_mlops.demo.app import (
    _follow_deck,
    _grafana_embed_url,
    _grafana_panel_url,
    _render_demo,
    _render_live_activity,
    _render_presentation,
)
from weather_mlops.demo.presentation import all_slides


def test_grafana_embed_url_keeps_configured_parameters_and_adds_kiosk_mode() -> None:
    url = _grafana_embed_url("http://127.0.0.1:3000/d/weather-api/weather-api?orgId=1")

    assert url == ("http://127.0.0.1:3000/d/weather-api/weather-api?orgId=1&kiosk=&theme=dark")


def test_grafana_panel_url_uses_the_real_solo_panel_for_the_last_five_minutes() -> None:
    url = _grafana_panel_url("http://127.0.0.1:3000/d/weather-api/weather-api", 3)

    assert url == (
        "http://127.0.0.1:3000/d-solo/weather-api/weather-api?"
        "kiosk=&theme=dark&panelId=3&from=now-5m&to=now&refresh=5s"
    )


def test_live_prediction_shows_request_and_latency_without_error_rate() -> None:
    activity = inspect.getsource(_render_live_activity)

    assert "(1, 3)" in activity
    assert "(1, 2, 3)" not in activity
    assert "error" not in activity.lower()


def test_projected_demo_keeps_speaker_notes_in_the_separate_notes_view() -> None:
    assert "talk-notes" not in inspect.getsource(_render_demo)
    assert "speaker-notes" in inspect.getsource(_follow_deck)


def test_presentation_hands_off_to_the_demo_tab_without_rendering_it_twice() -> None:
    assert "_render_live(" not in inspect.getsource(_render_presentation)


def test_model_training_posts_to_the_real_api_boundary() -> None:
    assert hasattr(demo_app, "_request_model_training")
    calls = []
    payload = {
        "train": {"accuracy": 0.91, "precision": 0.8, "recall": 0.84, "f1": 0.82, "roc_auc": 0.93},
        "validation": {
            "accuracy": 0.86,
            "precision": 0.74,
            "recall": 0.78,
            "f1": 0.76,
            "roc_auc": 0.88,
        },
    }

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return payload

    def fake_post(url: str, **kwargs) -> Response:
        calls.append((url, kwargs))
        return Response()

    result = demo_app._request_model_training(
        "https://nginx",
        auth=("weather", "secret"),
        post=fake_post,
    )

    assert result == payload
    assert calls == [
        (
            "https://nginx/train",
            {
                "json": {"track_run": False},
                "auth": ("weather", "secret"),
                "timeout": 120,
                "verify": False,
            },
        )
    ]


def test_training_result_makes_validation_quality_the_visible_outcome() -> None:
    assert hasattr(demo_app, "_training_result_markup")
    payload = {
        "train": {"accuracy": 0.91, "precision": 0.8, "recall": 0.84, "f1": 0.82, "roc_auc": 0.93},
        "validation": {
            "accuracy": 0.86,
            "precision": 0.74,
            "recall": 0.78,
            "f1": 0.76,
            "roc_auc": 0.88,
        },
    }

    markup = demo_app._training_result_markup(payload, elapsed_seconds=3.24)

    assert "Training complete" in markup
    assert "3.2 seconds" in markup
    assert "Validation recall" in markup
    assert "78.0%" in markup
    assert "Validation ROC-AUC" in markup
    assert "88.0%" in markup
    assert "Validation accuracy" in markup
    assert "86.0%" in markup


def test_training_activity_is_rendered_before_the_blocking_train_action(monkeypatch) -> None:
    events = []
    slots = 0

    class Slot:
        def __init__(self, name: str) -> None:
            self.name = name

        def button(self, *args, **kwargs) -> bool:
            events.append("button")
            return False

        def markdown(self, *args, **kwargs) -> None:
            events.append(f"{self.name}-markup")

    class FakeStreamlit:
        session_state = {}

        def markdown(self, *args, **kwargs) -> None:
            return None

        def caption(self, *args, **kwargs) -> None:
            return None

        def empty(self) -> Slot:
            nonlocal slots
            slots += 1
            name = "action" if slots == 1 else "result"
            events.append(f"{name}-placeholder")
            return Slot(name)

        def button(self, *args, **kwargs) -> bool:
            events.append("button")
            return False

    monkeypatch.setattr(demo_app, "st", FakeStreamlit())
    monkeypatch.setattr(
        demo_app,
        "_render_grafana_panels",
        lambda dashboard_url, panel_ids, **kwargs: events.append(
            ("grafana", dashboard_url, panel_ids, kwargs["height"])
        ),
    )

    demo_app._render_model_training("https://nginx")

    assert events == [
        "action-placeholder",
        "result-placeholder",
        ("grafana", demo_app.GRAFANA_API_URL, (1, 3), 190),
        "button",
    ]


def test_returning_from_demo_resumes_on_the_live_demo_slide() -> None:
    assert hasattr(demo_app, "_menu_navigation_state")
    live_demo_index = next(
        index for index, (_, slide) in enumerate(all_slides()) if slide["id"] == "demo"
    )

    assert demo_app._menu_navigation_state("Presentations") == {
        "deck": live_demo_index,
        "cue": -1,
    }
    assert demo_app._menu_navigation_state("Demo") == {"slide": 0}


def test_starting_a_new_demo_clears_the_previous_training_result() -> None:
    assert hasattr(demo_app, "_apply_menu_navigation")
    state = {
        "menu": "Demo",
        "slide": 1,
        "training_result": {"payload": {}, "elapsed_seconds": 10.5},
    }

    demo_app._apply_menu_navigation(state)

    assert state["slide"] == 0
    assert "training_result" not in state
