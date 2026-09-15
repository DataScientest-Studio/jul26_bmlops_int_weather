"""Hydrate Vault secrets into the environment, then exec the remaining argv.

`make streamlit` uses this so Compose can pass API basic auth into Streamlit
without storing those values in .env. Streamlit still never gets SUPABASE_KEY.
"""

import os
import sys

from weather_mlops.security.vault import AUTH_SETTINGS, hydrate_runtime_secrets


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/with_vault_env.py <command> [args...]")
    hydrate_runtime_secrets(
        names=tuple(name for name, _attr in AUTH_SETTINGS),
        required=("API_AUTH_USER", "API_AUTH_PASSWORD"),
    )
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
