import json
from pathlib import Path

import pytest

from weather_mlops.demo.deck import render_slide
from weather_mlops.demo.presentation import (
    COMMIT,
    METRICS,
    SECTIONS,
    STAGES,
    TEAM,
    all_slides,
    source_url,
    total_minutes,
)

ROOT = Path(__file__).resolve().parents[2]


def test_talk_and_demo_fit_twenty_minutes():
    assert total_minutes() == 20


def test_every_member_presents_one_section():
    presenters = []
    for section in SECTIONS:
        presenters.append(section["presenter"])
    assert sorted(presenters) == sorted(TEAM)


def test_every_stage_is_on_exactly_one_slide():
    covered = []
    for section in SECTIONS:
        for slide in section["slides"]:
            covered = covered + slide["stages"]
    stage_ids = []
    for stage in STAGES:
        stage_ids.append(stage["id"])
    assert sorted(covered) == sorted(stage_ids)


def test_slides_stay_short():
    for section in SECTIONS:
        for slide in section["slides"]:
            limit = 3
            if slide["layout"] == "script":
                limit = 5
            assert len(slide["points"]) <= limit, slide["id"]


def test_every_link_opens_on_github():
    # data/, models/ and reports/ are kept by dvc, so github does not have them
    for section in SECTIONS:
        for slide in section["slides"]:
            for link in slide["links"]:
                path = link[1]
                assert (ROOT / path).exists(), path
                assert not path.startswith(("data/", "models/", "reports/")), path
                assert COMMIT in source_url(path)


def test_chart_matches_the_metric_files():
    files = {"Train": "train", "Validation": "validation", "Test": "evaluation"}
    prefixes = {"Train": "train", "Validation": "validation", "Test": "test"}
    keys = {"ROC-AUC": "roc_auc", "Recall": "recall", "Precision": "precision"}
    for metric, splits in METRICS.items():
        for split, shown in splits.items():
            path = ROOT / "reports" / "metrics" / (files[split] + ".json")
            if not path.exists():
                pytest.skip("metric files come from dvc, run make dvc-pull or make pipeline")
            values = json.loads(path.read_text())
            real = values[prefixes[split] + "_" + keys[metric]]
            assert round(real, 3) == shown, (metric, split)


def test_every_slide_has_notes():
    for section in SECTIONS:
        for slide in section["slides"]:
            assert len(slide["notes"]) > 0, slide["id"]


def test_notes_are_never_on_the_shared_slide():
    slides = all_slides()
    for index in range(len(slides)):
        slide = slides[index][1]
        html = render_slide(index)
        for note in slide["notes"]:
            assert note not in html, slide["id"]


def test_every_slide_shows_its_number():
    count = len(all_slides())
    for index in range(count):
        assert f"{index + 1} / {count}" in render_slide(index)


def test_every_note_has_one_focus_entry():
    for section in SECTIONS:
        for slide in section["slides"]:
            if "focus" in slide:
                assert len(slide["focus"]) == len(slide["notes"]), slide["id"]


def test_every_focus_target_is_on_the_slide():
    slides = all_slides()
    for index in range(len(slides)):
        slide = slides[index][1]
        html = render_slide(index)
        for targets in slide.get("focus", []):
            for target in targets:
                assert f'data-focus="{target}"' in html, (slide["id"], target)


def test_focus_lights_only_the_current_point():
    slides = all_slides()
    for index in range(len(slides)):
        slide = slides[index][1]
        if "focus" not in slide:
            continue
        assert "outline" not in render_slide(index, -1)
        for cue in range(len(slide["focus"])):
            html = render_slide(index, cue)
            for target in slide["focus"][cue]:
                assert f'.slide [data-focus="{target}"]' in html, (slide["id"], cue)
