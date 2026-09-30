-- Compare upserts model_versions on mlflow_run_id. Init puts UNIQUE on the
-- CREATE TABLE; existing shared-project tables skipped that statement.

create unique index if not exists model_versions_mlflow_run_id_key
    on public.model_versions (mlflow_run_id);
