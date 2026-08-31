-- =========================================================
--  Weather MLOps — Supabase schema
--  Project: jul26_bmlops_int_weather
--  Source: GUIDELINES.md (Phase 1 + Phase 4 mandates)
--
--  Apply in Supabase SQL Editor, or via:
--    psql "$SUPABASE_DB_URL" -f supabase/schema.sql
--  Re-runnable: drops everything in `public` before recreating.
-- =========================================================

create extension if not exists "uuid-ossp";

-- ---------- Phase 1: raw data ingestion ----------
-- One-time load via a Python script (per mentor brief).
-- Generic shape so Ziad can adapt columns to whichever
-- Weather dataset the team picks. Extra columns are fine.
create table if not exists public.weather_observations (
    id                bigserial    primary key,
    observed_at       timestamptz  not null,
    location          text         not null,         -- e.g. "Paris,FR" or station id
    latitude          numeric(9,6),
    longitude         numeric(9,6),
    temperature_c     numeric(6,2),
    humidity_pct      numeric(5,2),
    pressure_hpa      numeric(7,2),
    wind_speed_ms     numeric(6,2),
    precipitation_mm  numeric(6,2),
    cloud_cover_pct   numeric(5,2),
    weather_code      text,                          -- provider-specific code
    raw_payload       jsonb,                         -- original API/CSV row, untouched
    ingested_at       timestamptz  not null default now(),
    source            text         not null default 'unknown'
);

create index if not exists idx_weather_obs_time
    on public.weather_observations (observed_at desc);

create index if not exists idx_weather_obs_location
    on public.weather_observations (location, observed_at desc);

-- Unique on (source, location, observed_at) so re-runs of the
-- one-time ingestion script don't duplicate rows.
create unique index if not exists uq_weather_obs_source_loc_time
    on public.weather_observations (source, location, observed_at);

-- ---------- MLOps glue: MLflow-synced model registry mirror ----------
-- MLflow is the source of truth; this is a local mirror for
-- joins with the predictions table and audit.
-- Defined BEFORE predictions because predictions.model_version_id FKs into it.
create table if not exists public.model_versions (
    id                 bigserial    primary key,
    mlflow_run_id      text         not null unique,
    mlflow_model_uri   text,
    name               text         not null,        -- e.g. "weather_baseline"
    stage              text         not null default 'None',  -- None|Staging|Production|Archived
    metrics            jsonb,
    params             jsonb,
    tags               jsonb,
    registered_at      timestamptz  not null default now()
);

-- ---------- Phase 4: predictions log (drift detection source) ----------
-- Mentor brief: "Store each prediction along with its features in the database."
-- Evidently's drift DAG reads from here.
create table if not exists public.predictions (
    id                  uuid         primary key default uuid_generate_v4(),
    prediction_ts       timestamptz  not null default now(),
    model_version_id    bigint,                      -- FK added below (ALTER to dodge ordering)
    features            jsonb        not null,        -- exact features fed to the model
    predicted_value     numeric,                     -- regression target (e.g. temp_c)
    predicted_class     text,                        -- or classification label
    request_id          text,                        -- API correlation id
    latency_ms          integer
);

-- FK on predictions -> model_versions. Safe on re-runs (idempotent).
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'predictions_model_version_fk'
    ) then
        alter table public.predictions
            add constraint predictions_model_version_fk
            foreign key (model_version_id)
            references public.model_versions(id)
            on delete set null;
    end if;
end$$;

create index if not exists idx_predictions_ts
    on public.predictions (prediction_ts desc);

create index if not exists idx_predictions_model_version
    on public.predictions (model_version_id, prediction_ts desc);

-- GIN index on features so drift tooling can query feature drift efficiently.
create index if not exists idx_predictions_features_gin
    on public.predictions using gin (features);

-- ---------- Phase 4: drift reports ----------
create table if not exists public.drift_reports (
    id                 bigserial    primary key,
    generated_at       timestamptz  not null default now(),
    scope              text         not null,        -- 'training' | 'prediction'
    reference_dataset  text,                        -- name or path of reference dataset
    current_dataset    text,                        -- name or path of current dataset
    drift_detected     boolean      not null,
    metrics            jsonb        not null,        -- Evidently summary metrics
    report_html_path   text,                        -- file path or Supabase storage URL
    mlflow_run_id      text                         -- if logged to MLflow
);

create index if not exists idx_drift_reports_generated_at
    on public.drift_reports (generated_at desc);

-- =========================================================
--  Row-Level Security
--  Default: deny all to anon/authenticated. Open only
--  what the API service role needs (via service_role key).
-- =========================================================
alter table public.weather_observations enable row level security;
alter table public.predictions         enable row level security;
alter table public.model_versions      enable row level security;
alter table public.drift_reports       enable row level security;

-- Service-role bypasses RLS automatically. No public policies
-- are granted — the FastAPI server uses the service_role key.
-- Ziad is granted access via Supabase Authentication
-- (Dashboard → Authentication → Users), not via a Postgres role.

-- =========================================================
--  Supabase Auth users — read/write via RLS
-- =========================================================
-- For every user signed in via Supabase Authentication
-- (Dashboard → Authentication → Users → Invite).
-- The `authenticated` role is the Postgres role Supabase
-- assigns to every logged-in user; `auth.uid()` identifies them.

drop policy if exists auth_write_weather_obs on public.weather_observations;
create policy auth_write_weather_obs
    on public.weather_observations for all
    to authenticated
    using (true) with check (true);

drop policy if exists auth_write_predictions on public.predictions;
create policy auth_write_predictions
    on public.predictions for all
    to authenticated
    using (true) with check (true);

drop policy if exists auth_write_model_ver on public.model_versions;
create policy auth_write_model_ver
    on public.model_versions for all
    to authenticated
    using (true) with check (true);

drop policy if exists auth_write_drift_rep on public.drift_reports;
create policy auth_write_drift_rep
    on public.drift_reports for all
    to authenticated
    using (true) with check (true);
