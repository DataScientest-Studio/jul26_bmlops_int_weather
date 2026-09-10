"""Checks on docker-compose.yml, the file that wires the three containers together."""

from pathlib import Path

import yaml

# this file is tests/unit/<name>.py, so two folders up is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_services():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    return compose["services"]


def test_every_service_dockerfile_exists():
    for name, service in load_services().items():
        dockerfile = PROJECT_ROOT / service["build"]["dockerfile"]

        assert dockerfile.exists(), f"{name} points at a missing Dockerfile: {dockerfile}"


def test_the_three_expected_services_are_there():
    services = load_services()

    assert set(services) == {"ingestion", "preprocess", "api"}
    assert "trainer" not in services, "the trainer service was replaced by preprocess"


def test_preprocess_runs_after_ingestion():
    depends_on = load_services()["preprocess"]["depends_on"]

    assert set(depends_on) == {"ingestion"}
    assert depends_on["ingestion"]["condition"] == "service_completed_successfully"


def test_api_starts_after_preprocessing():
    depends_on = load_services()["api"]["depends_on"]

    assert set(depends_on) == {"preprocess"}
    assert depends_on["preprocess"]["condition"] == "service_completed_successfully"


def test_api_cannot_write_to_the_dataset():
    """The api saves models and reports, but it must never change data/."""
    volumes = load_services()["api"]["volumes"]

    assert "./data:/app/data:ro" in volumes
