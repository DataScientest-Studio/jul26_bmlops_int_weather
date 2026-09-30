-- Registry lookup key: MLflow version string on the catalog row.

alter table public.model_versions
    add column if not exists mlflow_model_version text;
