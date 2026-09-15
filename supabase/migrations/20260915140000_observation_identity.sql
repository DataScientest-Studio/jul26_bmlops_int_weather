-- Observation identity is (date, location), not CSV row position.
-- source_row_number remains as a non-key column for debugging a specific file load.

alter table public.weather_observations
    drop constraint if exists weather_observations_pkey;

alter table public.weather_observations
    alter column date set not null;

alter table public.weather_observations
    alter column location set not null;

create unique index if not exists weather_observations_date_location_key
    on public.weather_observations (date, location);
