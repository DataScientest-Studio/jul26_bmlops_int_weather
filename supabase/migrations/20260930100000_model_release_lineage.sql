-- Immutable MLflow release tuple mirrored for catalog queries and recovery.

alter table public.model_versions
    add column if not exists model_sha256 text,
    add column if not exists git_commit text,
    add column if not exists preprocessing_version text,
    add column if not exists split jsonb,
    add column if not exists artifact_verified_at timestamptz;
