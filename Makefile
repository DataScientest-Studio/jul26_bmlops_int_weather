-include .env
export

LOCAL_ENV = UV_CACHE_DIR=.uv-cache
DVC_ENV = $(LOCAL_ENV) DVC_NO_ANALYTICS=1 DVC_SITE_CACHE_DIR=.dvc/tmp/cache-home XDG_CACHE_HOME=.dvc/tmp/cache-home

.PHONY: install sync lint format format-check test test-cov dvc-check-env dvc-config pull push repro train validate evaluate predict load-db check lock

install:
	$(LOCAL_ENV) uv sync

sync:
	$(LOCAL_ENV) uv sync

lock:
	$(LOCAL_ENV) uv lock

lint:
	$(LOCAL_ENV) uv run ruff check .

format:
	$(LOCAL_ENV) uv run ruff format .

format-check:
	$(LOCAL_ENV) uv run ruff format --check .

test:
	$(LOCAL_ENV) uv run pytest -v

test-cov:
	$(LOCAL_ENV) uv run pytest --cov=weather_mlops --cov-report=term-missing

dvc-check-env:
	@test -n "$(SUPABASE_S3_ENDPOINT)" || (echo "Missing SUPABASE_S3_ENDPOINT in .env"; exit 1)
	@test -n "$(AWS_ACCESS_KEY_ID)" || (echo "Missing AWS_ACCESS_KEY_ID in .env"; exit 1)
	@test -n "$(AWS_SECRET_ACCESS_KEY)" || (echo "Missing AWS_SECRET_ACCESS_KEY in .env"; exit 1)
	@test -n "$(AWS_DEFAULT_REGION)" || (echo "Missing AWS_DEFAULT_REGION in .env"; exit 1)
	@case "$(SUPABASE_S3_ENDPOINT)$(AWS_ACCESS_KEY_ID)$(AWS_SECRET_ACCESS_KEY)" in *\<*\>*) echo "Replace placeholder values in .env before running dvc-config"; exit 1;; esac

dvc-config: dvc-check-env
	$(LOCAL_ENV) uv run python scripts/configure_dvc_remote.py

pull:
	$(DVC_ENV) uv run dvc pull

push:
	$(DVC_ENV) uv run dvc push

repro:
	$(DVC_ENV) uv run dvc repro

train:
	$(LOCAL_ENV) uv run python -m weather_mlops.models.training

validate:
	$(LOCAL_ENV) uv run python -m weather_mlops.models.evaluation --x-data data/processed/X_validation.csv --y-data data/processed/y_validation.csv --metrics-output reports/metrics/validation.json --split-name validation

evaluate:
	$(LOCAL_ENV) uv run python -m weather_mlops.models.evaluation

predict:
	$(LOCAL_ENV) uv run python -m weather_mlops.models.predict --input-json sample_prediction.json

load-db:
	$(LOCAL_ENV) uv run python scripts/load_to_supabase.py

check:
	$(LOCAL_ENV) uv run ruff check .
	$(LOCAL_ENV) uv run ruff format --check .
	$(LOCAL_ENV) uv run pytest
