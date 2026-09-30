"""Apply supabase/migrations over Postgres. One-shot host runner.

Needs SUPABASE_DB_URL (direct or session-mode, port 5432). Store it in Vault
or export it for this command. The service-role key cannot run DDL.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from weather_mlops.config.settings import settings
from weather_mlops.data.schema_migrate import (
    MIGRATIONS_DIR,
    apply_migrations,
    connection_error_hint,
    list_migration_files,
    normalize_dsn,
    split_sql,
    verify_schema,
)
from weather_mlops.security.vault import hydrate_runtime_secrets


class PsycopgConnection:
    def __init__(self, dsn: str) -> None:
        import psycopg

        self._conn = psycopg.connect(dsn, autocommit=True)

    def execute_script(self, sql: str) -> None:
        for statement in split_sql(sql):
            self._conn.execute(statement)

    def fetchall(self, sql: str) -> list[tuple]:
        return list(self._conn.execute(sql))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply or verify the Supabase SQL migrations.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--migrations-dir", type=Path, default=MIGRATIONS_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hydrate_runtime_secrets(names=("SUPABASE_DB_URL",))
    url = settings.supabase_db_url
    if args.dry_run and not url:
        names = [path.name for path in list_migration_files(args.migrations_dir)]
        print("Dry run (no SUPABASE_DB_URL); would apply:")
        for name in names:
            print(f"  {name}")
        return
    if not url:
        raise SystemExit(
            "Set SUPABASE_DB_URL in Vault or the environment. "
            "Use the direct or session-mode URI on port 5432, not transaction mode 6543."
        )
    if ":6543" in url:
        print(
            "warning: port 6543 is the transaction pooler; migrations need 5432.",
            file=sys.stderr,
        )

    try:
        connection = PsycopgConnection(normalize_dsn(url))
    except Exception as exc:
        hint = connection_error_hint(exc)
        if hint:
            raise SystemExit(f"{exc}\n{hint}") from exc
        raise
    if not args.verify_only:
        applied = apply_migrations(connection, args.migrations_dir, dry_run=args.dry_run)
        label = "Would apply" if args.dry_run else "Applied"
        print(f"{label}:")
        if not applied:
            print("  (none pending)")
        for name in applied:
            print(f"  {name}")
        if args.dry_run:
            return

    missing = verify_schema(connection)
    if missing:
        print("Schema verify failed:")
        for item in missing:
            print(f"  missing {item}")
        raise SystemExit(1)
    print("Schema verify ok.")


if __name__ == "__main__":
    main()
