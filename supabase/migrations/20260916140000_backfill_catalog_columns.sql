-- Init uses CREATE TABLE IF NOT EXISTS. Shared-project tables that already
-- existed skip that statement, so catalog columns defined only there never
-- appear. ADD COLUMN is the path that works on both empty and existing tables.

alter table public.predictions
    add column if not exists predicted_value numeric;

alter table public.predictions
    add column if not exists probability double precision;

alter table public.predictions
    add column if not exists request_id text;

alter table public.predictions
    add column if not exists latency_ms integer;

alter table public.model_versions
    add column if not exists mlflow_model_uri text;

alter table public.model_versions
    add column if not exists artifact_path text;

alter table public.model_versions
    add column if not exists dataset_sha256 text;

alter table public.model_versions
    add column if not exists tags jsonb;
