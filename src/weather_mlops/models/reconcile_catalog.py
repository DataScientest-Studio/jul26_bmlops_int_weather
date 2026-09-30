"""Retry the Supabase lineage mirror without changing MLflow aliases."""

from __future__ import annotations

import argparse
from typing import Any

from weather_mlops.config.settings import settings
from weather_mlops.data.database import store_model_version


def reconcile_model_catalog(release: dict[str, Any], catalog_client: Any) -> None:
    """Idempotently mirror a verified MLflow release; aliases remain in MLflow."""

    store_model_version(
        {
            "mlflow_run_id": release["run_id"],
            "mlflow_model_version": str(release["model_version"]),
            "mlflow_model_uri": release["model_uri"],
            "artifact_path": release["artifact_uri"],
            "model_sha256": release["model_sha256"],
            "dataset_sha256": release["dataset_sha256"],
            "git_commit": release["git_commit"],
            "preprocessing_version": release["preprocessing_version"],
            "split": release["split"],
            "name": settings.mlflow_model_name,
            "stage": "candidate",
        },
        client=catalog_client,
    )


def sync_release_to_catalog(release: dict[str, Any], catalog_client: Any) -> str:
    """Return a retryable state instead of invalidating an MLflow release."""

    try:
        reconcile_model_catalog(release, catalog_client)
    except Exception:
        return "pending"
    return "synced"


def main() -> None:
    from weather_mlops.models.tracking import load_mlflow_run_metadata

    parser = argparse.ArgumentParser(description="Retry model-release catalog synchronisation.")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    metadata = load_mlflow_run_metadata()
    release = metadata.get("release")
    if not isinstance(release, dict):
        raise RuntimeError("No local MLflow release tuple is available.")
    if args.run_id and args.run_id != release.get("run_id"):
        raise RuntimeError("The requested run is not the locally recorded release.")
    state = sync_release_to_catalog(release, catalog_client=None)
    print(f"Catalog synchronisation: {state}")


if __name__ == "__main__":
    main()
