import json

import mlflow

from weather_mlops.config.settings import settings

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

MLFLOW_MODEL_NAME = settings.mlflow_model_name
PRIMARY_METRIC = settings.mlflow_primary_metric


def load_mlflow_run_metadata() -> dict:
    """Load the MLflow run/model version created by training.py."""

    metadata_path = settings.mlflow_run_metadata_path

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def load_validation_metrics() -> dict[str, float]:

    metrics_path = settings.validation_metrics_path

    raw_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    return {
        key: float(value) for key, value in raw_metrics.items() if isinstance(value, (int, float))
    }


def get_registered_model_version(
    client: mlflow.MlflowClient,
    model_name: str,
    version: str,
):
    """Retrieve a specific registered model version."""

    try:
        return client.get_model_version(
            name=model_name,
            version=version,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not retrieve model {model_name} version {version}.") from exc


def get_best_model_version(
    client: mlflow.MlflowClient,
    model_name: str,
):
    """
    Find the currently tagged best model.

    Returns None if no model has been tagged as best yet.
    """

    versions = client.search_model_versions(filter_string=f"name = '{model_name}'")

    best_versions = [version for version in versions if version.tags.get("status") == "best"]

    if not best_versions:
        return None

    if len(best_versions) > 1:
        raise RuntimeError(
            f"More than one version of {model_name} is tagged as best: "
            + ", ".join(str(version.version) for version in best_versions)
        )

    return best_versions[0]


def get_run_metric(
    client: mlflow.MlflowClient,
    run_id: str,
    metric_name: str,
) -> float:
    """Retrieve a metric from an MLflow run."""

    run = client.get_run(run_id)

    if metric_name not in run.data.metrics:
        raise RuntimeError(f"Metric '{metric_name}' is not available in MLflow run {run_id}.")

    return float(run.data.metrics[metric_name])


def tag_model_version(
    client: mlflow.MlflowClient,
    model_name: str,
    version: str,
    status: str,
) -> None:
    """Set the status tag on a registered model version."""

    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="status",
        value=status,
    )


def clear_existing_best_tags(
    client: mlflow.MlflowClient,
    model_name: str,
    except_version: str,
) -> None:
    """
    Ensure only one model version is tagged as best.

    MLflow tags are mutable, so when a new model wins we remove the
    best status from all other versions.
    """

    versions = client.search_model_versions(filter_string=f"name = '{model_name}'")

    for version in versions:
        if str(version.version) != str(except_version) and version.tags.get("status") == "best":
            tag_model_version(
                client=client,
                model_name=model_name,
                version=str(version.version),
                status="previous_best",
            )


def compare_models() -> None:
    client = mlflow.MlflowClient()

    run_metadata = load_mlflow_run_metadata()

    run_id = run_metadata["run_id"]
    model_name = run_metadata["model_name"]
    new_version = str(run_metadata["model_version"])

    get_registered_model_version(
        client=client,
        model_name=model_name,
        version=new_version,
    )

    validation_metrics = load_validation_metrics()

    metric_name = PRIMARY_METRIC

    if metric_name not in validation_metrics:
        raise RuntimeError(
            f"Primary metric '{metric_name}' was not found in {settings.validation_metrics_path}."
        )

    new_score = validation_metrics[metric_name]

    print(f"New model: {model_name} v{new_version}")
    print(f"Validation metric: {metric_name} = {new_score:.4f}")

    validation_mlflow_metrics = {
        key: value for key, value in validation_metrics.items() if key.startswith("validation_")
    }

    if validation_mlflow_metrics:
        for key, value in validation_mlflow_metrics.items():
            client.log_metric(
                run_id=run_id,
                key=key,
                value=value,
            )

    # Find current best model
    current_best = get_best_model_version(
        client=client,
        model_name=model_name,
    )

    # First model
    if current_best is None:
        print(f"No existing best model found. Model v{new_version} becomes the best model.")

        clear_existing_best_tags(
            client=client,
            model_name=model_name,
            except_version=new_version,
        )

        tag_model_version(
            client=client,
            model_name=model_name,
            version=new_version,
            status="best",
        )

        return

    # Don't compare the model against itself.
    if str(current_best.version) == new_version:
        print(f"Model v{new_version} is already tagged as best. Nothing to compare.")
        return

    # Retrieve previous best score
    previous_best_score = get_run_metric(
        client=client,
        run_id=current_best.run_id,
        metric_name=metric_name,
    )

    print(f"Previous best: v{current_best.version}")
    print(f"Previous {metric_name}: {previous_best_score:.4f}")

    new_model_is_best = new_score > previous_best_score

    if new_model_is_best:
        print(f"New model v{new_version} is better. Promoting it to best.")

        # Remove "best" from any other version.
        clear_existing_best_tags(
            client=client,
            model_name=model_name,
            except_version=new_version,
        )

        tag_model_version(
            client=client,
            model_name=model_name,
            version=new_version,
            status="best",
        )

        tag_model_version(
            client=client,
            model_name=model_name,
            version=str(current_best.version),
            status="previous_best",
        )

        # Store comparison information on the new version.
        client.set_model_version_tag(
            name=model_name,
            version=new_version,
            key="previous_best_version",
            value=str(current_best.version),
        )

        client.set_model_version_tag(
            name=model_name,
            version=new_version,
            key="previous_best_score",
            value=f"{previous_best_score:.6f}",
        )

        print(f"Model v{new_version} is now the best model.")

    # Previous model remains best
    else:
        print(f"New model v{new_version} is not better. Keeping v{current_best.version} as best.")

        tag_model_version(
            client=client,
            model_name=model_name,
            version=new_version,
            status="candidate",
        )

        client.set_model_version_tag(
            name=model_name,
            version=new_version,
            key="compared_against_version",
            value=str(current_best.version),
        )

        client.set_model_version_tag(
            name=model_name,
            version=new_version,
            key="compared_against_score",
            value=f"{previous_best_score:.6f}",
        )


def main() -> None:
    compare_models()


if __name__ == "__main__":
    main()
