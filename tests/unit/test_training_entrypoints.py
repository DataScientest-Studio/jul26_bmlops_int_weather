"""Training must happen only through the API (POST /train).

Before, the Makefile could train directly and the trainer container trained on
every startup. These tests fail if either of those comes back.
"""

from pathlib import Path

# this file is tests/unit/<name>.py, so two folders up is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_MODULE = "weather_mlops.models.training"


def test_makefile_never_runs_the_training_module_directly():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert TRAINING_MODULE not in makefile, "the Makefile must not train directly"


def test_makefile_train_target_calls_the_api():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert 'curl -fsS -X POST "$(API_URL)/train"' in makefile


def test_no_docker_entrypoint_runs_the_training_module():
    entrypoints = sorted((PROJECT_ROOT / "docker").glob("*/entrypoint.sh"))

    assert entrypoints, "expected at least one docker entrypoint"

    for entrypoint in entrypoints:
        assert TRAINING_MODULE not in entrypoint.read_text(), (
            f"{entrypoint.name} still trains on startup"
        )
