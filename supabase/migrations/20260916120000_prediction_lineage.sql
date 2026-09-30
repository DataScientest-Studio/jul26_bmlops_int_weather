-- Lineage columns for serving logs and the MLflow model mirror.
-- SQL stays here. Apply with: make supabase-migrate

create table if not exists public.schema_migrations (
    filename text primary key,
    applied_at timestamptz not null default now()
);

alter table public.schema_migrations enable row level security;

alter table public.model_versions
    add column if not exists feature_schema jsonb;

alter table public.predictions
    add column if not exists observation_date date;

alter table public.predictions
    add column if not exists location text;

alter table public.predictions
    add column if not exists endpoint text not null default 'predict';

alter table public.predictions
    add column if not exists observed_label text;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'predictions_endpoint_check'
    ) then
        alter table public.predictions
            add constraint predictions_endpoint_check
            check (endpoint in ('predict', 'live_data'));
    end if;
end$$;

create index if not exists idx_predictions_observation
    on public.predictions (observation_date, location);

create index if not exists idx_predictions_endpoint
    on public.predictions (endpoint, prediction_ts desc);
