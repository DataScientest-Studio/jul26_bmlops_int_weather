from weather_mlops.demo.deck import render_slide
from weather_mlops.demo.presentation import all_slides


def _future_slide():
    for index, (section, slide) in enumerate(all_slides()):
        if slide["id"] == "next-steps":
            return index, section, slide
    raise AssertionError("future-work slide missing")


def test_future_work_has_four_mlop_next_steps() -> None:
    index, section, slide = _future_slide()

    assert section["presenter"] == "Ziad"
    assert slide["title"] == "Future work"
    assert slide["layout"] == "future"
    assert len(slide["focus"]) == len(slide["notes"])

    html = render_slide(index)
    assert "layout-future" in html
    assert "Scale on Kubernetes" in html
    assert "Jev and transformers" in html
    assert "current XGBoost baseline" in html
    assert len(slide["cards"]) == 4
    assert html.count("<img ") == 2
    assert "data:image/svg+xml" in html
    assert "data:image/png" in html
    assert "future-index" in html
    assert "Canary release" in html
    assert "Shadow evaluation and rollback" in html
    assert "Tomorrow's forecast" not in html
    assert "Tuned cut-off" not in html


def test_live_demo_uses_only_the_visual_and_title() -> None:
    for index, (_, slide) in enumerate(all_slides()):
        if slide["id"] == "demo":
            break
    else:
        raise AssertionError("live-demo slide missing")

    html = render_slide(index)

    assert 'class="demo-hero"' in html
    assert "live_demo_hero.png" in html
    assert 'class="live-cues"' not in html
    assert "Pick a station." not in html
    assert "Show the nightly DAG in Airflow." not in html


def test_future_work_and_questions_have_distinct_closing_treatments() -> None:
    slides = {slide["id"]: (index, slide) for index, (_, slide) in enumerate(all_slides())}

    future_html = render_slide(slides["next-steps"][0])
    questions_html = render_slide(slides["questions"][0])

    assert future_html.count("future-card is-lead") == 2
    assert future_html.count("future-card is-compact") == 2
    assert 'class="questions-closing"' in questions_html
    assert "Thank you" in questions_html
    assert "All nine lifecycle stages are in place." not in questions_html


def test_speaker_notes_explain_the_live_demo_and_safe_model_promotion() -> None:
    slides = {slide["id"]: slide for _, slide in all_slides()}

    live_demo_notes = " ".join(slides["demo"]["notes"])
    future_work_notes = " ".join(slides["next-steps"]["notes"])
    questions_notes = " ".join(slides["questions"]["notes"])

    assert "About 4 minutes." in live_demo_notes
    assert "user-facing path" in live_demo_notes
    assert "repeatable pipeline" in live_demo_notes
    assert "About 1 minute." in future_work_notes
    assert "without returning its prediction to users" in future_work_notes
    assert "solid MLOps base" in questions_notes
