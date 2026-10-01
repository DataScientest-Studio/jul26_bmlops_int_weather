"""Immutable MLflow release metadata and verification helpers."""

from __future__ import annotations

from typing import Any

from weather_mlops.config.settings import settings

REQUIRED_RELEASE_ARTIFACTS = {
    "joblib/rain_classifier.joblib",
    "metrics/train.json",
    "dataset/manifest.json",
    "lineage/release.json",
}


def _list_artifact_paths(client: Any, run_id: str, path: str | None = None) -> set[str]:
    paths: set[str] = set()
    artifacts = (
        client.list_artifacts(run_id) if path is None else client.list_artifacts(run_id, path)
    )
    for artifact in artifacts:
        paths.add(artifact.path)
        if getattr(artifact, "is_dir", False):
            paths.update(_list_artifact_paths(client, run_id, artifact.path))
    return paths


def build_model_release(
    *,
    run_id: str,
    model_version: str,
    model_uri: str,
    artifact_uri: str,
    model_sha256: str,
    manifest: dict[str, Any],
    git_commit: str,
) -> dict[str, Any]:
    """Bind one registered model to its immutable code and data provenance."""

    return {
        "run_id": run_id,
        "model_version": model_version,
        "model_uri": model_uri,
        "artifact_uri": artifact_uri,
        "model_sha256": model_sha256,
        "dataset_sha256": str(manifest["sha256"]),
        "git_commit": git_commit,
        "preprocessing_version": str(manifest["preprocessing_version"]),
        "split": manifest.get("split") or {},
    }


def verify_model_release(release: dict[str, Any], client: Any) -> None:
    """Reject aliases unless their MLflow model/run/artifact identities agree."""

    if not release.get("git_commit") or str(release["git_commit"]).endswith("-dirty"):
        raise RuntimeError("release must have a clean git commit")

    version = client.get_model_version(settings.mlflow_model_name, str(release["model_version"]))
    if version.run_id != release["run_id"]:
        raise RuntimeError("registered model version belongs to a different run")

    paths = _list_artifact_paths(client, release["run_id"])
    missing = REQUIRED_RELEASE_ARTIFACTS - paths
    if missing:
        raise RuntimeError(f"release artifact missing: {sorted(missing)}")
