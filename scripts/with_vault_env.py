"""Hydrate Vault secrets into the environment, then exec the remaining argv.

`make streamlit` copies basic auth into the demo container.
`make mlflow` copies S3 keys so the tracking server can write artifacts to
`s3://weather-mlops-mlflow`. Neither container receives SUPABASE_KEY.
"""

import os
import sys

from weather_mlops.security.vault import (
    AUTH_SETTINGS,
    S3_SETTINGS,
    hydrate_runtime_secrets,
)


def main() -> None:
    args = sys.argv[1:]
    hydrate_s3 = False
    if args and args[0] == "--s3":
        hydrate_s3 = True
        args = args[1:]
    if not args:
        raise SystemExit("Usage: python scripts/with_vault_env.py [--s3] <command> [args...]")

    if hydrate_s3:
        from weather_mlops.config.settings import settings

        hydrate_runtime_secrets(
            names=tuple(name for name, _attr in S3_SETTINGS),
            required=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
        )
        if settings.supabase_s3_endpoint:
            os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", settings.supabase_s3_endpoint)
    else:
        hydrate_runtime_secrets(
            names=tuple(name for name, _attr in AUTH_SETTINGS),
            required=("API_AUTH_USER", "API_AUTH_PASSWORD"),
        )
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
