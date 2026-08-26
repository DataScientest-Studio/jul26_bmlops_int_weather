.PHONY: install sync lint format format-check test test-cov api train check lock

install:
	uv sync

sync:
	uv sync

lock:
	uv lock

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=weather_mlops --cov-report=term-missing

api:
	uv run uvicorn weather_mlops.api.main:app \
		--app-dir src \
		--reload \
		--port 8000

train:
	uv run python -m weather_mlops.models.training

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest