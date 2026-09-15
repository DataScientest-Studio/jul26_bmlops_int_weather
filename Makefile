-include .env
export

LOCAL_ENV = UV_CACHE_DIR=.uv-cache
DVC_ENV = $(LOCAL_ENV) DVC_NO_ANALYTICS=1 DVC_SITE_CACHE_DIR=.dvc/tmp/cache-home XDG_CACHE_HOME=.dvc/tmp/cache-home
COMPOSE = docker compose

API_URL ?= https://nginx
TRAIN_PARAMS ?= {}
ARGS ?=
SERVICE ?= api
GIT_SHA := $(shell git rev-parse HEAD 2>/dev/null)
GIT_DIRTY := $(shell if [ -n "$(GIT_SHA)" ] && [ -n "$$(git status --porcelain 2>/dev/null)" ]; then echo -dirty; fi)
GIT_COMMIT ?= $(GIT_SHA)$(GIT_DIRTY)
export GIT_COMMIT

.PHONY: dvc-check-env dvc-config dvc-pull dvc-push dvc-repro dvc-add-model dvc-commit \
	build up serve api gateway streamlit mlflow down logs test test-gateway pipeline \
	train validate evaluate compare predict fetch-open-meteo merge-raw preprocess \
	load-db register-dataset

# --- DVC stays on the host (Git pointers + local cache). Everything else is Compose. ---

dvc-check-env:
	@test -n "$(SUPABASE_URL)" || (echo "Missing SUPABASE_URL in .env"; exit 1)
	@test -n "$(SUPABASE_KEY)" || (echo "Missing SUPABASE_KEY in .env"; exit 1)
	@case "$(SUPABASE_URL)$(SUPABASE_KEY)" in *\<*\>*) echo "Replace placeholder values in .env before running dvc-config"; exit 1;; esac

dvc-config: dvc-check-env
	$(LOCAL_ENV) uv run python scripts/configure_dvc_remote.py

dvc-pull:
	$(DVC_ENV) uv run dvc pull

dvc-push:
	$(DVC_ENV) uv run dvc push

dvc-repro:
	$(DVC_ENV) uv run dvc repro version_raw preprocess

dvc-add-model:
	$(DVC_ENV) uv run dvc add models/rain_classifier.joblib reports/metrics/train.json

dvc-commit:
	$(DVC_ENV) uv run dvc commit -f

# --- Compose: long-running services detach; jobs run and exit. ---

build:
	$(COMPOSE) --profile gateway --profile streamlit --profile test --profile mlflow build

up:
	$(MAKE) mlflow
	$(COMPOSE) --profile gateway up -d --build

serve:
	$(MAKE) mlflow
	$(COMPOSE) up -d --build --no-deps --wait api
	$(COMPOSE) --profile gateway up -d --build --force-recreate --no-deps nginx

api: serve
gateway: serve

streamlit: serve
	$(LOCAL_ENV) uv run python scripts/with_vault_env.py $(COMPOSE) --profile streamlit up -d --build --no-deps streamlit

mlflow:
	$(LOCAL_ENV) uv run python scripts/with_vault_env.py --s3 $(COMPOSE) --profile mlflow up -d --build --wait mlflow

down:
	$(COMPOSE) --profile gateway --profile streamlit --profile test --profile mlflow down --remove-orphans

logs:
	$(COMPOSE) logs -f $(SERVICE)

test:
	$(COMPOSE) up -d --build --no-deps api
	$(COMPOSE) --profile gateway up -d --build --force-recreate --no-deps nginx
	$(COMPOSE) --profile test run --rm --build -e GATEWAY_URL=https://nginx test

test-gateway:
	$(COMPOSE) up -d --build --no-deps api
	$(COMPOSE) --profile gateway up -d --build --force-recreate --no-deps nginx
	$(COMPOSE) --profile test run --rm --build -e GATEWAY_URL=https://nginx --entrypoint pytest test -v tests/integration/test_nginx_live.py

pipeline: train
	$(MAKE) validate
	$(MAKE) compare
	$(MAKE) evaluate

compare:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.comparison

train: serve
	$(COMPOSE) run --rm --no-deps -e API_URL="$(API_URL)" -e TRAIN_PARAMS='$(TRAIN_PARAMS)' --entrypoint python api scripts/train_via_api.py

validate:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.evaluation --x-data data/processed/X_validation.csv --y-data data/processed/y_validation.csv --metrics-output reports/metrics/validation.json --split-name validation

evaluate:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.evaluation

predict: serve
	$(COMPOSE) run --rm --no-deps \
		-e API_URL="$(API_URL)" \
		--volume ./sample_prediction.json:/app/sample_prediction.json:ro \
		--entrypoint python api scripts/predict_via_api.py --input-json sample_prediction.json

fetch-open-meteo:
	@test -n "$(OPEN_METEO_DATE)" || (echo "Usage: make fetch-open-meteo OPEN_METEO_DATE=2026-09-01"; exit 1)
	$(COMPOSE) run --rm --no-deps -e OPEN_METEO_DATE="$(OPEN_METEO_DATE)" --entrypoint python ingestion scripts/fetch_open_meteo_daily.py --date "$(OPEN_METEO_DATE)"

merge-raw:
	$(COMPOSE) run --rm --no-deps --entrypoint python ingestion -m weather_mlops.data.merge_raw

preprocess:
	$(COMPOSE) run --rm --no-deps --build preprocess

load-db:
	$(COMPOSE) run --rm --no-deps --entrypoint python api scripts/load_to_supabase.py $(ARGS)

register-dataset:
	$(COMPOSE) run --rm --no-deps --build --entrypoint python api scripts/register_dataset_version.py $(ARGS)
