"""POST /train using basic auth hydrated from Vault."""

import json
import os
import sys

import requests

from weather_mlops.security.vault import AUTH_SETTINGS, hydrate_runtime_secrets


def post_train(url: str, user: str, password: str, payload: dict) -> str:
    train_url = f"{url}/train"
    try:
        response = requests.post(
            train_url,
            json=payload,
            auth=(user, password),
            timeout=120,
        )
    except requests.ConnectionError:
        raise SystemExit(
            f"Nothing is listening at {url}. Start the API first with "
            "`make api` or `make up`, then retry `make train`."
        ) from None
    except requests.Timeout:
        raise SystemExit(f"Timed out waiting for {train_url}.") from None
    if not response.ok:
        print(response.text, file=sys.stderr)
        raise SystemExit(response.status_code)
    return response.text


def main() -> None:
    hydrate_runtime_secrets(
        names=tuple(name for name, _attr in AUTH_SETTINGS),
        required=("API_AUTH_USER", "API_AUTH_PASSWORD"),
    )
    user = os.environ.get("API_AUTH_USER")
    password = os.environ.get("API_AUTH_PASSWORD")
    if not user or not password:
        raise SystemExit("API_AUTH_USER / API_AUTH_PASSWORD missing from Vault (and .env).")

    url = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        payload = json.loads(os.environ.get("TRAIN_PARAMS") or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"TRAIN_PARAMS is not valid JSON: {exc}") from exc

    print(post_train(url, user, password, payload))


if __name__ == "__main__":
    main()
