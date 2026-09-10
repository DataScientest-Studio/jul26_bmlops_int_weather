"""Training must happen only through the API (POST /train).

Before, the Makefile could train directly and the trainer container trained on
every startup. These tests fail if either of those comes back.
"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAINING_MODULE = "weather_mlops.models.training"


def test_makefile_never_runs_the_training_module_directly():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    assert TRAINING_MODULE not in makefile, "the Makefile must not train directly"


def test_makefile_train_target_calls_the_api():
    makefile = (PROJECT_ROOT / "Makefile").read_text()

    train_target = makefile.split("\ntrain:\n", 1)[1].split("\n\n", 1)[0]

    assert "/train" in train_target
    assert "curl" in train_target


def test_no_docker_entrypoint_runs_the_training_module():
    entrypoints = sorted((PROJECT_ROOT / "docker").glob("*/entrypoint.sh"))

    assert entrypoints, "expected at least one docker entrypoint"

    offenders = [
        entrypoint.name for entrypoint in entrypoints if TRAINING_MODULE in entrypoint.read_text()
    ]
    assert offenders == [], f"these entrypoints still train on startup: {offenders}"


def test_compose_has_no_training_service():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())

    services = compose["services"]

    assert "trainer" not in services, "the trainer service was replaced by preprocess"
    assert set(services) == {"ingestion", "preprocess", "api"}


def test_compose_api_waits_for_preprocessing_only():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())

    api_depends_on = compose["services"]["api"]["depends_on"]

    assert set(api_depends_on) == {"preprocess"}
    assert api_depends_on["preprocess"]["condition"] == "service_completed_successfully"
