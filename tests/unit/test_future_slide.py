from weather_mlops.demo.deck import render_slide
from weather_mlops.demo.presentation import all_slides


def _future_slide():
    for index, (section, slide) in enumerate(all_slides()):
        if slide["id"] == "next-steps":
            return index, section, slide
    raise AssertionError("future-work slide missing")


def test_ziad_closes_on_future_work_with_icons() -> None:
    index, section, slide = _future_slide()

    assert section["presenter"] == "Ziad"
    assert slide["title"] == "Future work"
    assert slide["layout"] == "future"
    assert len(slide["focus"]) == len(slide["notes"])

    html = render_slide(index)
    assert "layout-future" in html
    assert "Scale on Kubernetes" in html
    assert "Jev and transformers" in html
    assert "System One classifier" in html
    assert html.count("<img ") == 6
    assert "data:image/svg+xml" in html
    assert "data:image/png" in html
    assert "data:image/jpeg" in html
    assert "Canary release" in html
    assert "Tomorrow's forecast" in html
    assert "Tuned cut-off" in html
    assert "Shadow, then rollback" in html
