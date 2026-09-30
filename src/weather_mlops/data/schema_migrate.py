"""Apply supabase/migrations/*.sql over a Postgres connection.

SQL files stay under supabase/. This module is the testable runner.
The one-shot CLI is scripts/apply_supabase_schema.py.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, unquote

from weather_mlops.config.settings import PROJECT_ROOT

MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"
_MIGRATION_NAME = re.compile(r"^[0-9]{14}_[a-z0-9_]+\.sql$")

ENSURE_MIGRATIONS_TABLE = """
create table if not exists public.schema_migrations (
    filename text primary key,
    applied_at timestamptz not null default now()
);

alter table public.schema_migrations enable row level security;
"""

TABLES_SQL = """
select table_name
  from information_schema.tables
 where table_schema = 'public'
   and table_type = 'BASE TABLE'
"""

COLUMNS_SQL = """
select table_name, column_name
  from information_schema.columns
 where table_schema = 'public'
"""

BUCKETS_SQL = """
select name from storage.buckets
"""

EXPECTED_TABLES = (
    "weather_observations",
    "dataset_versions",
    "ingestion_batches",
    "model_versions",
    "predictions",
    "drift_reports",
    "schema_migrations",
)

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "predictions": (
        "id",
        "prediction_ts",
        "model_version_id",
        "features",
        "predicted_class",
        "probability",
        "observation_date",
        "location",
        "endpoint",
        "observed_label",
    ),
    "model_versions": (
        "id",
        "mlflow_run_id",
        "dataset_sha256",
        "metrics",
        "params",
        "feature_schema",
        "stage",
        "mlflow_model_version",
    ),
}

EXPECTED_BUCKETS = (
    "weather-mlops-dvc",
    "weather-mlops-mlflow",
)


class SchemaConnection(Protocol):
    def execute_script(self, sql: str) -> None: ...

    def fetchall(self, sql: str) -> list[tuple]: ...


def list_migration_files(directory: Path) -> list[Path]:
    files = [
        path
        for path in directory.glob("*.sql")
        if path.is_file() and _MIGRATION_NAME.match(path.name)
    ]
    return sorted(files, key=lambda path: path.name)


def pending_migrations(files: list[Path], applied: set[str]) -> list[Path]:
    return [path for path in files if path.name not in applied]


def split_sql(script: str) -> list[str]:
    """Split a SQL file into statements, keeping $tag$ ... $tag$ blocks intact."""

    statements: list[str] = []
    buffer: list[str] = []
    index = 0
    length = len(script)
    in_single = False
    dollar_tag: str | None = None

    while index < length:
        char = script[index]
        if dollar_tag is not None:
            if script.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
                continue
            buffer.append(char)
            index += 1
            continue
        if in_single:
            buffer.append(char)
            if char == "'" and index + 1 < length and script[index + 1] == "'":
                buffer.append("'")
                index += 2
                continue
            if char == "'":
                in_single = False
            index += 1
            continue
        if char == "-" and index + 1 < length and script[index + 1] == "-":
            while index < length and script[index] != "\n":
                buffer.append(script[index])
                index += 1
            continue
        if char == "'":
            in_single = True
            buffer.append(char)
            index += 1
            continue
        if char == "$":
            tag_end = index + 1
            while tag_end < length and (script[tag_end].isalnum() or script[tag_end] == "_"):
                tag_end += 1
            if tag_end < length and script[tag_end] == "$":
                dollar_tag = script[index : tag_end + 1]
                buffer.append(dollar_tag)
                index = tag_end + 1
                continue
        if char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue
        buffer.append(char)
        index += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def applied_filenames(connection: SchemaConnection) -> set[str]:
    try:
        rows = connection.fetchall("select filename from public.schema_migrations")
    except Exception:
        return set()
    return {str(row[0]) for row in rows}


def apply_migrations(
    connection: SchemaConnection,
    directory: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    if not dry_run:
        connection.execute_script(ENSURE_MIGRATIONS_TABLE)
    pending = pending_migrations(list_migration_files(directory), applied_filenames(connection))
    names = [path.name for path in pending]
    if dry_run:
        return names
    for path in pending:
        connection.execute_script(path.read_text(encoding="utf-8"))
        connection.execute_script(
            "insert into public.schema_migrations (filename) "
            f"values ('{path.name}') "
            "on conflict (filename) do nothing"
        )
    return names


def verify_schema(connection: SchemaConnection) -> list[str]:
    missing: list[str] = []
    tables = {str(row[0]) for row in connection.fetchall(TABLES_SQL)}
    for table in EXPECTED_TABLES:
        if table not in tables:
            missing.append(f"table:{table}")

    columns = {(str(table), str(column)) for table, column in connection.fetchall(COLUMNS_SQL)}
    for table, required in EXPECTED_COLUMNS.items():
        for column in required:
            if (table, column) not in columns:
                missing.append(f"{table}.{column}")

    buckets = {str(row[0]) for row in connection.fetchall(BUCKETS_SQL)}
    for bucket in EXPECTED_BUCKETS:
        if bucket not in buckets:
            missing.append(f"bucket:{bucket}")
    return missing


def normalize_dsn(url: str) -> str:
    """Percent-encode the password and require SSL.

    Database passwords often contain [, ], @, #. urllib.urlparse treats
    brackets as IPv6, which breaks Supabase pooler URIs. Encode the
    password (everything after the first userinfo colon, up to the last @)
    instead of parsing the whole string as a URL.
    """

    url = url.strip()
    url = _encode_dsn_password(url)
    if "sslmode=" not in url.lower():
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def _encode_dsn_password(url: str) -> str:
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    userinfo, hostpart = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, password = userinfo.split(":", 1)
    encoded = quote(unquote(password), safe="")
    return f"{scheme}://{user}:{encoded}@{hostpart}"


def connection_error_hint(exc: BaseException) -> str | None:
    text = str(exc).lower()
    if "enotfound" in text or "tenant/user" in text or "tenant or user not found" in text:
        return (
            "The pooler host does not know this project. aws-0-... is not a safe default. "
            "Dashboard → Connect → Session pooler, copy the whole URI (host is often aws-1-...), "
            "then: make vault-put NAME=SUPABASE_DB_URL VALUE='<pasted-uri>'"
        )
    return None
