-- Dataset lineage catalog, snapshot buckets, and Vault helper.
-- Apply after 20260831090000_init.sql on the shared Supabase project.

alter table public.dataset_versions add column if not exists version_kind text not null default 'raw';
alter table public.dataset_versions add column if not exists storage_uri text;
alter table public.dataset_versions add column if not exists git_commit text;
alter table public.dataset_versions add column if not exists preprocessing_version text;
alter table public.dataset_versions add column if not exists parent_sha256 text;
alter table public.dataset_versions add column if not exists source text not null default 'weatherAUS';
alter table public.dataset_versions add column if not exists created_by text not null default 'local';

create index if not exists idx_dataset_versions_kind
    on public.dataset_versions (version_kind, created_at desc);

create table if not exists public.ingestion_batches (
    id uuid primary key default uuid_generate_v4(),
    batch_date date not null,
    location_count integer,
    storage_uri text not null,
    sha256 text not null,
    source text not null default 'open-meteo',
    git_commit text,
    created_at timestamptz not null default now(),
    unique (batch_date, sha256)
);

create index if not exists idx_ingestion_batches_date
    on public.ingestion_batches (batch_date desc);

alter table public.ingestion_batches enable row level security;

drop policy if exists auth_write_ingestion_batches on public.ingestion_batches;
create policy auth_write_ingestion_batches
    on public.ingestion_batches for all
    to authenticated
    using (true) with check (true);

insert into storage.buckets (id, name, public)
values ('weather-mlops-mlflow', 'weather-mlops-mlflow', false)
on conflict (id) do nothing;

do $$
begin
    create extension if not exists supabase_vault;
exception
    when others then
        raise notice 'supabase_vault extension not available: %', sqlerrm;
end$$;

create or replace function public.get_app_secret(secret_name text)
returns text
language plpgsql
security definer
set search_path = vault, pg_temp
as $$
declare
    value text;
begin
    if coalesce(auth.role(), current_user) not in ('service_role', 'postgres', 'supabase_admin') then
        raise exception 'not authorized to read vault secrets';
    end if;

    select decrypted_secret
      into value
      from vault.decrypted_secrets
     where name = secret_name
     limit 1;

    return value;
end;
$$;

revoke all on function public.get_app_secret(text) from public, anon, authenticated;
grant execute on function public.get_app_secret(text) to service_role, postgres;
