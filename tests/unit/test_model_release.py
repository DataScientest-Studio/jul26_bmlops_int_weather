import pytest

from weather_mlops.models.reconcile_catalog import sync_release_to_catalog
from weather_mlops.models.release import build_model_release, verify_model_release


class FakeClient:
    def __init__(self, artifacts: set[str]) -> None:
        self.artifacts = artifacts

    def get_model_version(self, _name: str, _version: str):
        return type("Version", (), {"run_id": "run-1"})()

    def list_artifacts(self, _run_id: str, path: str | None = None):
        return [type("Artifact", (), {"path": artifact})() for artifact in self.artifacts]


def _release() -> dict:
    return build_model_release(
        run_id="run-1",
        model_version="3",
        model_uri="models:/weather-rainfall-classifier/3",
        artifact_uri="runs:/run-1/model",
        model_sha256="model-sha",
        manifest={
            "sha256": "dataset-sha",
            "preprocessing_version": "2026.09.15",
            "split": {"test_end": "2025-12-31"},
        },
        git_commit="abc123",
    )


def test_build_model_release_binds_model_dataset_code_and_split() -> None:
    release = _release()

    assert release == {
        "run_id": "run-1",
        "model_version": "3",
        "model_uri": "models:/weather-rainfall-classifier/3",
        "artifact_uri": "runs:/run-1/model",
        "model_sha256": "model-sha",
        "dataset_sha256": "dataset-sha",
        "git_commit": "abc123",
        "preprocessing_version": "2026.09.15",
        "split": {"test_end": "2025-12-31"},
    }


def test_verify_model_release_requires_every_release_artifact() -> None:
    release = _release()
    client = FakeClient(
        {
            "model",
            "joblib/rain_classifier.joblib",
            "metrics/train.json",
            "dataset/manifest.json",
        }
    )

    with pytest.raises(RuntimeError, match="release artifact"):
        verify_model_release(release, client)


class FailingCatalog:
    def table(self, _name: str):
        raise ConnectionError("Supabase unavailable")


def test_catalog_sync_reports_pending_when_the_mirror_is_unavailable() -> None:
    assert sync_release_to_catalog(_release(), FailingCatalog()) == "pending"


def test_catalog_sync_reports_pending_when_supabase_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr("weather_mlops.data.database.settings.supabase_url", None)
    monkeypatch.setattr("weather_mlops.data.database.settings.supabase_key", None)

    assert sync_release_to_catalog(_release(), None) == "pending"
