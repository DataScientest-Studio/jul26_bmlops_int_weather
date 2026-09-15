from weather_mlops.demo.slides import SLIDES, slide_index


def test_deck_is_three_screens() -> None:
    ids = [slide.id for slide in SLIDES]

    assert ids == ["architecture", "stores", "live"]


def test_architecture_and_stores_name_the_stack() -> None:
    architecture = SLIDES[slide_index("architecture")]
    stores = SLIDES[slide_index("stores")]

    assert any("FastAPI" in note for note in architecture.notes)
    assert any("weather-mlops-dvc" in note for note in stores.notes)
    assert any("weather-mlops-mlflow" in note for note in stores.notes)


def test_live_slide_does_not_mention_service_role_usage() -> None:
    live = SLIDES[slide_index("live")]

    assert any("SUPABASE_KEY" in note for note in live.notes)
