"""Checks on docker-compose.yml, the file that wires the containers together."""

from pathlib import Path

import yaml

# this file is tests/unit/<name>.py, so two folders up is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_IMAGES = ("ingestion", "preprocess", "api")


def load_compose():
    return yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())


def load_services():
    return load_compose()["services"]


def test_every_built_service_dockerfile_exists():
    for name, service in load_services().items():
        if "build" not in service:
            continue
        dockerfile = PROJECT_ROOT / service["build"]["dockerfile"]

        assert dockerfile.exists(), f"{name} points at a missing Dockerfile: {dockerfile}"


def test_core_pipeline_services_are_there():
    services = load_services()

    assert {"api", "ingestion", "preprocess", "streamlit", "test", "mlflow"} <= set(services)
    assert "trainer" not in services, "the trainer service was replaced by preprocess"
    assert "nginx" in services
    assert "minio" not in services


def test_nginx_is_an_opt_in_profile():
    assert load_services()["nginx"]["profiles"] == ["gateway"]


def test_demo_and_test_are_opt_in_profiles():
    assert load_services()["streamlit"]["profiles"] == ["streamlit"]
    assert load_services()["test"]["profiles"] == ["test"]
    assert load_services()["mlflow"]["profiles"] == ["mlflow"]


def test_demo_does_not_receive_the_service_role_key():
    env = load_services()["streamlit"]["environment"]

    assert "SUPABASE_KEY" not in env
    assert env["DEMO_API_URL"] == "http://api:8000"
    assert env["API_AUTH_USER"] == "${API_AUTH_USER:-}"
    assert env["API_AUTH_PASSWORD"] == "${API_AUTH_PASSWORD:-}"


def test_preprocess_runs_after_ingestion():
    depends_on = load_services()["preprocess"]["depends_on"]

    assert list(depends_on) == ["ingestion"]
    assert depends_on["ingestion"]["condition"] == "service_completed_successfully"


def test_api_starts_after_preprocessing():
    depends_on = load_services()["api"]["depends_on"]

    assert list(depends_on) == ["preprocess"]
    assert depends_on["preprocess"]["condition"] == "service_completed_successfully"


def test_api_cannot_write_to_the_dataset():
    """The api saves models and reports, but it must never change data/."""
    volumes = load_services()["api"]["volumes"]

    assert "./data:/app/data:ro" in volumes


def test_api_port_is_bound_to_localhost():
    assert "127.0.0.1:8000:8000" in load_services()["api"]["ports"]


def test_mlflow_port_is_bound_to_localhost():
    assert "127.0.0.1:8080:8080" in load_services()["mlflow"]["ports"]


def test_api_only_receives_supabase_bootstrap_env():
    env = load_services()["api"]["environment"]

    assert {
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GIT_COMMIT",
        "MLFLOW_TRACKING_URI",
    } == set(env)
    assert "API_AUTH_PASSWORD" not in env


def test_api_image_records_git_commit():
    dockerfile = (PROJECT_ROOT / "docker" / "api" / "Dockerfile").read_text()

    assert "ARG GIT_COMMIT=" in dockerfile
    assert "ENV GIT_COMMIT=$GIT_COMMIT" in dockerfile
    assert load_services()["api"]["build"]["args"]["GIT_COMMIT"] == "${GIT_COMMIT:-}"


def test_preprocess_job_receives_git_commit():
    env = load_services()["preprocess"]["environment"]

    assert env["GIT_COMMIT"] == "${GIT_COMMIT:-}"


def test_preprocess_image_does_not_install_xgboost():
    requirements = (PROJECT_ROOT / "docker" / "preprocess" / "requirements.txt").read_text()

    assert "xgboost" not in requirements.lower()


def test_release_workflow_pushes_application_images():
    """release.yml lists the app images by hand, so it can drift from compose."""
    release = (PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert "for service in ingestion preprocess api;" in release
    for name in APP_IMAGES:
        assert name in release


def test_test_service_runs_ruff_and_pytest():
    command = load_services()["test"]["command"]

    assert command[-1] == "ruff check . && ruff format --check . && pytest -v"
