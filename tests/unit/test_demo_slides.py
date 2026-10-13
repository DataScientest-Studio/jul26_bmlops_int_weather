from weather_mlops.demo.slides import SLIDES, slide_index


def test_deck_follows_the_defense_demo() -> None:
    ids = [slide.id for slide in SLIDES]

    assert ids == ["live", "train"]


def test_training_screen_explains_the_single_live_action() -> None:
    training = SLIDES[slide_index("train")]

    assert any("POST /train" in note for note in training.notes)
    assert any("Recall" in note and "ROC-AUC" in note for note in training.notes)


def test_live_slide_does_not_mention_service_role_usage() -> None:
    live = SLIDES[slide_index("live")]

    assert any("SUPABASE_KEY" in note for note in live.notes)
    assert any("Nginx" in note for note in live.notes)


def test_training_screen_does_not_repeat_the_model_health_story() -> None:
    training = SLIDES[slide_index("train")]

    assert all("Evidently" not in note for note in training.notes)
    assert all("drift" not in note.lower() for note in training.notes)
