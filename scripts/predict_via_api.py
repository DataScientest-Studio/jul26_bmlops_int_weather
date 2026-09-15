"""POST /predict through the Nginx gateway using basic auth from Vault."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

from weather_mlops.api.http import tls_verify
from weather_mlops.security.vault import AUTH_SETTINGS, hydrate_runtime_secrets


def pascal_to_snake(key: str) -> str:
    if "_" in key:
        return key
    out = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", key)
    out = re.sub(r"(?<=[A-Za-z])(?=\d)", "_", out)
    return out.lower().strip("_")


def features_for_api(raw: dict) -> dict:
    return {pascal_to_snake(str(key)): value for key, value in raw.items()}


def post_predict(url: str, user: str, password: str, features: dict) -> str:
    predict_url = f"{url}/predict"
    try:
        response = requests.post(
            predict_url,
            json=features,
            auth=(user, password),
            timeout=40,
            verify=tls_verify(url),
        )
    except requests.ConnectionError:
        raise SystemExit(
            f"Nothing is listening at {url}. Start the gateway with "
            "`make api` or `make up`, then retry `make predict`."
        ) from None
    except requests.Timeout:
        raise SystemExit(f"Timed out waiting for {predict_url}.") from None
    if not response.ok:
        print(response.text, file=sys.stderr)
        raise SystemExit(response.status_code)
    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(description="POST one prediction through Nginx.")
    parser.add_argument(
        "--input-json",
        type=Path,
        default=Path("sample_prediction.json"),
        help="Feature dict (CSV PascalCase or API snake_case).",
    )
    args = parser.parse_args()

    hydrate_runtime_secrets(
        names=tuple(name for name, _attr in AUTH_SETTINGS),
        required=("API_AUTH_USER", "API_AUTH_PASSWORD"),
    )
    user = os.environ.get("API_AUTH_USER")
    password = os.environ.get("API_AUTH_PASSWORD")
    if not user or not password:
        raise SystemExit("API_AUTH_USER / API_AUTH_PASSWORD missing from Vault (and .env).")

    url = os.environ.get("API_URL", "https://nginx").rstrip("/")
    features = features_for_api(json.loads(args.input_json.read_text(encoding="utf-8")))
    print(post_predict(url, user, password, features))


if __name__ == "__main__":
    main()
