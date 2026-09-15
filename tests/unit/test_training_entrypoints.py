"""Training must happen only through the API (POST /train).

Before, the Makefile could train directly and the trainer container trained on
every startup. These tests fail if either of those comes back.
"""

from pathlib import Path

import pytest
import requests

# this file is tests/unit/<name>.py, so two folders up is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_MODULE = "weather_mlops.models.training"


def test_makefile_runtime_uses_compose():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert "uvicorn" not in makefile
    assert "COMPOSE = docker compose" in makefile
    assert "up -d --build" in makefile
    assert "--profile test run --rm --build test" in makefile
    assert "API_URL ?= http://api:8000" in makefile
    assert "\ndvc-pull:" in makefile
    assert "\nmlflow:" in makefile
    assert "\nstreamlit:" in makefile
    assert "\npipeline:" in makefile
    assert "\ncheck:" not in makefile
    assert "docker-up:" not in makefile
    assert "\ninstall:" not in makefile
    assert "\nsync:" not in makefile


def test_makefile_never_runs_the_training_module_directly():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert TRAINING_MODULE not in makefile, "the Makefile must not train directly"


def test_makefile_train_target_calls_the_api():
    makefile = (PROJECT_ROOT / "Makefile").read_text()
    trainer = (PROJECT_ROOT / "scripts" / "train_via_api.py").read_text()
    dvc = (PROJECT_ROOT / "dvc.yaml").read_text()

    assert "scripts/train_via_api.py" in makefile
    assert TRAINING_MODULE not in makefile
    assert 'f"{url}/train"' in trainer
    assert TRAINING_MODULE not in trainer
    assert "make api" in trainer
    assert TRAINING_MODULE not in dvc
    assert "manifest.json" in dvc
    assert "dvc repro version_raw preprocess" in makefile
    assert "dvc add models/rain_classifier.joblib" in makefile
    assert "dvc commit -f" in makefile
    assert "dvc add data/processed" not in makefile
    dvc_lines = dvc.splitlines()
    assert "  preprocess:" in dvc_lines
    assert "    preprocess:" not in dvc_lines
    assert "  train:" not in dvc_lines


def test_register_dataset_script_registers_processed_splits():
    source = (PROJECT_ROOT / "scripts" / "register_dataset_version.py").read_text()

    assert "register_processed_snapshot" in source
    assert "S3_SETTINGS" not in source


def test_load_db_does_not_write_catalog_rows():
    loader = (PROJECT_ROOT / "scripts" / "load_to_supabase.py").read_text()

    assert "store_dataset_metadata" not in loader


def test_no_docker_entrypoint_runs_the_training_module():
    entrypoints = sorted((PROJECT_ROOT / "docker").glob("*/entrypoint.sh"))

    assert entrypoints, "expected at least one docker entrypoint"

    for entrypoint in entrypoints:
        assert TRAINING_MODULE not in entrypoint.read_text(), (
            f"{entrypoint.name} still trains on startup"
        )


def test_train_via_api_explains_when_the_server_is_down(monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "train_via_api",
        PROJECT_ROOT / "scripts" / "train_via_api.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def boom(*_args, **_kwargs):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(module.requests, "post", boom)

    with pytest.raises(SystemExit, match="make api"):
        module.post_train("http://127.0.0.1:8000", "user", "pass", {})


def test_readme_publish_recipe_does_not_readd_pipeline_outputs() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "dvc add data/processed" not in readme
    assert "dvc add data/raw/weatherAUS_current.csv" not in readme
    assert "make dvc-add-model" in readme
    assert "models/rain_classifier.joblib.dvc" in readme
