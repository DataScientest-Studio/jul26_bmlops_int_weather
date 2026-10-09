from weather_mlops.demo.slides import SLIDES, slide_index


def test_deck_follows_the_defense_demo() -> None:
    ids = [slide.id for slide in SLIDES]

    assert ids == ["live", "health"]


def test_model_health_keeps_feature_drift_separate_from_promotion() -> None:
    health = SLIDES[slide_index("health")]

    assert any("Evidently" in note for note in health.notes)
    assert any("champion" in note for note in health.notes)


def test_live_slide_does_not_mention_service_role_usage() -> None:
    live = SLIDES[slide_index("live")]

    assert any("SUPABASE_KEY" in note for note in live.notes)
    assert any("Nginx" in note for note in live.notes)


def test_model_health_slide_explains_the_live_grafana_evidence() -> None:
    health = SLIDES[slide_index("health")]

    assert any("Grafana" in note for note in health.notes)
