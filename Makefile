-include .env
export

LOCAL_ENV = UV_CACHE_DIR=.uv-cache
DVC_ENV = $(LOCAL_ENV) DVC_NO_ANALYTICS=1 DVC_SITE_CACHE_DIR=.dvc/tmp/cache-home XDG_CACHE_HOME=.dvc/tmp/cache-home
COMPOSE = docker compose

API_URL ?= http://api:8000
TRAIN_PARAMS ?= {}
ARGS ?=
SERVICE ?= api
GIT_SHA := $(shell git rev-parse HEAD 2>/dev/null)
GIT_DIRTY := $(shell if [ -n "$(GIT_SHA)" ] && [ -n "$$(git status --porcelain 2>/dev/null)" ]; then echo -dirty; fi)
GIT_COMMIT ?= $(GIT_SHA)$(GIT_DIRTY)
export GIT_COMMIT

.PHONY: dvc-check-env dvc-config dvc-pull dvc-push dvc-repro dvc-add-model dvc-commit \
	build up api gateway streamlit down logs test pipeline \
	train validate evaluate predict fetch-open-meteo merge-raw preprocess \
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
	$(COMPOSE) --profile gateway --profile streamlit --profile test build

up:
	$(COMPOSE) up -d --build

api:
	$(COMPOSE) up -d --build --no-deps api

gateway:
	$(COMPOSE) --profile gateway up -d --build

streamlit:
	$(COMPOSE) up -d --build --no-deps api
	$(LOCAL_ENV) uv run python scripts/with_vault_env.py $(COMPOSE) --profile streamlit up -d --build --no-deps streamlit

down:
	$(COMPOSE) --profile gateway --profile streamlit --profile test down --remove-orphans

logs:
	$(COMPOSE) logs -f $(SERVICE)

test:
	$(COMPOSE) --profile test run --rm --build test

pipeline: api
	$(MAKE) train
	$(MAKE) validate
	$(MAKE) evaluate

train:
	$(COMPOSE) run --rm --no-deps -e API_URL="$(API_URL)" -e TRAIN_PARAMS='$(TRAIN_PARAMS)' --entrypoint python api scripts/train_via_api.py

validate:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.evaluation --x-data data/processed/X_validation.csv --y-data data/processed/y_validation.csv --metrics-output reports/metrics/validation.json --split-name validation

evaluate:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.evaluation

predict:
	$(COMPOSE) run --rm --no-deps --entrypoint python api -m weather_mlops.models.predict --input-json sample_prediction.json

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
