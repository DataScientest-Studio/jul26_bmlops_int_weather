# Australian Weather MLOps

Predict `RainTomorrow` from Australian weather data. FastAPI behind Nginx (TLS,
basic auth), MLflow tracking + registry, DVC for dataset blobs, Airflow for
scheduled retraining. Code in Git, data in Supabase Storage, lineage in Postgres.

> **Full docs live in the [wiki](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki).**
> This README only covers what you need to clone, configure, and bring the app up.
> For architecture, the API contract, data flow, model registry, the dataset
> catalog, the Nginx gateway, Airflow, and the Supabase schema, read the wiki
> pages linked below.

## Wiki map

| Topic | Page |
| --- | --- |
| First clone + `.env` | [Setup](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Setup) |
| Restore the baseline end-to-end | [Reproduction](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Reproduction) |
| Components, request path, Nginx, Streamlit | [Architecture](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Architecture) |
| Daily pipeline, `make pipeline` vs DAG | [Pipeline](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Pipeline) |
| Airflow stack, DAG, security boundary | [Airflow](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Airflow) |
| DVC + Postgres catalog + snapshots | [Data-versioning](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Data-versioning) |
| MLflow registry, `champion` alias | [Model-registry](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Model-registry) |
| XGBoost, splits, metrics | [Model](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Model) |
| Postgres tables, Vault, future | [Schema](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Schema) |
| Wiki index | [Home](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Home) |

## Quickstart

```bash
git clone https://github.com/DataScientest-Studio/jul26_bmlops_int_weather.git
cd jul26_bmlops_int_weather
uv sync
cp .env.example .env          # fill the required Supabase bootstrap values
make dvc-config
make dvc-pull
make test                     # ruff + pytest, including live Nginx
make api                      # API + Nginx, detached
curl -k https://127.0.0.1/health
```

## Commands

| You want | Command |
| --- | --- |
| Restore the shared baseline | `make dvc-config && make dvc-pull && make api` |
| Refresh data + serve over HTTPS | `make up` |
| Retrain, promote, evaluate | `make pipeline` |
| Streamlit demo (`127.0.0.1:8501`) | `make streamlit` |
| MLflow UI (`127.0.0.1:8080`) | `make mlflow` |
| Scheduled daily retrain | `make airflow-up` — see the [Airflow wiki](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Airflow) |
| Follow logs / stop everything | `make logs` / `make down` |

Full Makefile target table lives in the [wiki Setup page](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Setup).

## Local `.env`

Required in `.env`:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<supabase-service-role-or-sb_secret-key>
```

For `make monitoring`, add these local Compose credentials too:

```text
# Must equal AIRFLOW_ADMIN / AIRFLOW_PW in airflow/.env.
AIRFLOW_API_USER=<airflow-admin-name>
AIRFLOW_API_PASSWORD=<airflow-admin-password>
GF_SECURITY_ADMIN_USER=<grafana-admin-name>
GF_SECURITY_ADMIN_PASSWORD=<grafana-admin-password>
```

Grafana uses `AIRFLOW_API_*` only to authenticate the alert webhook that starts
`weather_retrain`. `PUSHGATEWAY_URL` is deliberately not configurable here:
the Airflow task uses the internal Compose address `http://pushgateway:9091`.

Supabase Vault contains the existing application secrets only:
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `API_AUTH_USER`,
`API_AUTH_PASSWORD`, and `SUPABASE_DB_URL`. This monitoring integration adds
**no new Supabase Vault secret**. **Do not put Vault values in `.env`** and do
not commit `.env`.

Rotate a Vault secret, then `make api` to restart the API container. Vault
hydration is a startup snapshot, not live reload.

`make dvc-config` writes S3 keys in plaintext to `.dvc/config.local` — keep
that file local and `chmod 600`.

## Repository layout

```text
src/weather_mlops/   FastAPI app, models, data, security, demo
docker/              One Dockerfile per service (api, nginx, ingestion, preprocess, mlflow, demo, test)
scripts/             DVC remote, catalog, loaders, train/predict helpers
supabase/            schema.sql + migrations
tests/unit/          Config and auth checks (nginx.conf, compose, Vault, catalog)
airflow/             Separate Compose stack: DAG, webserver, scheduler, docker-socket-proxy
```

## CI

On pushes and pull requests to `master` / `main`:

- Host: `uv sync --locked --all-groups`, ruff, pytest.
- Docker: build images, start API + Nginx, run `make test` (unit + live TLS/429).

## See also

- [Wiki Home](https://github.com/DataScientest-Studio/jul26_bmlops_int_weather/wiki/Home) — full architecture and how-to.
- [`supabase/schema.sql`](./supabase/schema.sql) — the canonical Postgres schema.
