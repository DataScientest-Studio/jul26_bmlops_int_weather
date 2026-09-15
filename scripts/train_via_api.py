"""POST /train using basic auth hydrated from Vault."""

import json
import os
import sys
import time

import requests

from weather_mlops.api.http import tls_verify
from weather_mlops.security.vault import AUTH_SETTINGS, hydrate_runtime_secrets

_STARTUP_RETRIES = 8
_STARTUP_WAIT_SECONDS = 1


def post_train(url: str, user: str, password: str, payload: dict) -> str:
    train_url = f"{url}/train"
    last_response = None
    for attempt in range(_STARTUP_RETRIES):
        try:
            response = requests.post(
                train_url,
                json=payload,
                auth=(user, password),
                timeout=120,
                verify=tls_verify(url),
            )
        except requests.ConnectionError:
            raise SystemExit(
                f"Nothing is listening at {url}. Start the gateway first with "
                "`make api` or `make up`, then retry `make train`."
            ) from None
        except requests.Timeout:
            raise SystemExit(f"Timed out waiting for {train_url}.") from None
        if response.status_code != 502:
            if not response.ok:
                print(response.text, file=sys.stderr)
                raise SystemExit(response.status_code)
            return response.text
        last_response = response
        if attempt + 1 < _STARTUP_RETRIES:
            time.sleep(_STARTUP_WAIT_SECONDS)

    if last_response is not None:
        print(last_response.text, file=sys.stderr)
    raise SystemExit(
        f"{url} returned 502 from Nginx. The API was not ready; retry `make train`."
    )


def main() -> None:
    hydrate_runtime_secrets(
        names=tuple(name for name, _attr in AUTH_SETTINGS),
        required=("API_AUTH_USER", "API_AUTH_PASSWORD"),
    )
    user = os.environ.get("API_AUTH_USER")
    password = os.environ.get("API_AUTH_PASSWORD")
    if not user or not password:
        raise SystemExit("API_AUTH_USER / API_AUTH_PASSWORD missing from Vault (and .env).")

    url = os.environ.get("API_URL", "https://nginx").rstrip("/")
    try:
        payload = json.loads(os.environ.get("TRAIN_PARAMS") or "{}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"TRAIN_PARAMS is not valid JSON: {exc}") from exc

    print(post_train(url, user, password, payload))


if __name__ == "__main__":
    main()
