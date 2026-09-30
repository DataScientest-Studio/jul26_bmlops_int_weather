"""Create or rotate a named secret in Supabase Vault.

Uses SUPABASE_URL + SUPABASE_KEY from .env. Does not need SUPABASE_DB_URL.
The Supabase CLI `secrets` command is for Edge Functions, not Vault.
"""

from __future__ import annotations

import argparse
import sys

from weather_mlops.config.settings import settings
from weather_mlops.security.vault import ALLOWED_SECRET_NAMES, put_app_secret


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a secret into Supabase Vault.")
    parser.add_argument("name", choices=sorted(ALLOWED_SECRET_NAMES))
    parser.add_argument(
        "--value",
        default=None,
        help="Secret value. If omitted, the value is read from stdin.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not settings.supabase_url or not settings.supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env.")
    value = args.value if args.value is not None else sys.stdin.read().strip()
    if not value:
        raise SystemExit("Secret value is empty. Pass --value or pipe it on stdin.")
    put_app_secret(args.name, value)
    print(f"Stored {args.name} in Vault.")


if __name__ == "__main__":
    main()
