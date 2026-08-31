create table if not exists public.weather_observations (
    source_row_number integer primary key,
    date date,
    location text,
    min_temp double precision,
    max_temp double precision,
    rainfall double precision,
    evaporation double precision,
    sunshine double precision,
    wind_gust_dir text,
    wind_gust_speed double precision,
    wind_dir_9am text,
    wind_dir_3pm text,
    wind_speed_9am double precision,
    wind_speed_3pm double precision,
    humidity_9am double precision,
    humidity_3pm double precision,
    pressure_9am double precision,
    pressure_3pm double precision,
    cloud_9am double precision,
    cloud_3pm double precision,
    temp_9am double precision,
    temp_3pm double precision,
    rain_today text,
    rain_tomorrow text
);

create table if not exists public.dataset_versions (
    dataset_name text not null,
    path text not null,
    size_bytes bigint not null,
    md5 text not null,
    sha256 text not null,
    created_at timestamptz not null,
    primary key (dataset_name, sha256)
);

insert into storage.buckets (id, name, public)
values ('weather-mlops-dvc', 'weather-mlops-dvc', false)
on conflict (id) do nothing;
