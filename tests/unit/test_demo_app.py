import inspect

from weather_mlops.demo.app import (
    _follow_deck,
    _grafana_embed_url,
    _grafana_panel_url,
    _render_demo,
)


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
