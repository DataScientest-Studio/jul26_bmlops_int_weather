from pathlib import Path

from weather_mlops.data.schema_migrate import (
    MIGRATIONS_DIR,
    apply_migrations,
    connection_error_hint,
    list_migration_files,
    normalize_dsn,
    pending_migrations,
    split_sql,
    verify_schema,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeConnection:
    def __init__(
        self,
        *,
        applied: tuple[str, ...] = (),
        tables: tuple[str, ...] = (),
        columns: dict[str, tuple[str, ...]] | None = None,
        buckets: tuple[str, ...] = (),
    ) -> None:
        self.scripts: list[str] = []
        self.applied = set(applied)
        self.tables = set(tables)
        self.columns = {table: set(names) for table, names in (columns or {}).items()}
        self.buckets = set(buckets)

    def execute_script(self, sql: str) -> None:
        self.scripts.append(sql)
        if "schema_migrations" in sql and "insert" in sql.lower():
            for token in sql.split("'"):
                if token.endswith(".sql"):
                    self.applied.add(token)

    def fetchall(self, sql: str) -> list[tuple]:
        if "schema_migrations" in sql and "filename" in sql:
            return [(name,) for name in sorted(self.applied)]
        if "information_schema.tables" in sql:
            return [(name,) for name in sorted(self.tables)]
        if "information_schema.columns" in sql:
            rows: list[tuple] = []
            for table, names in self.columns.items():
                rows.extend((table, name) for name in sorted(names))
            return rows
        if "storage.buckets" in sql:
            return [(name,) for name in sorted(self.buckets)]
        raise AssertionError(f"unexpected query: {sql}")


def test_list_migration_files_is_sorted_by_filename(tmp_path: Path) -> None:
    later = tmp_path / "20260911080000_lineage.sql"
    earlier = tmp_path / "20260831090000_init.sql"
    later.write_text("select 2;", encoding="utf-8")
    earlier.write_text("select 1;", encoding="utf-8")

    names = [path.name for path in list_migration_files(tmp_path)]

    assert names == ["20260831090000_init.sql", "20260911080000_lineage.sql"]


def test_pending_migrations_skips_already_applied_filenames(tmp_path: Path) -> None:
    first = tmp_path / "20260831090000_init.sql"
    second = tmp_path / "20260911080000_lineage.sql"
    first.write_text("select 1;", encoding="utf-8")
    second.write_text("select 2;", encoding="utf-8")

    pending = pending_migrations(list_migration_files(tmp_path), {"20260831090000_init.sql"})

    assert [path.name for path in pending] == ["20260911080000_lineage.sql"]


def test_apply_migrations_runs_pending_files_and_records_them(tmp_path: Path) -> None:
    first = tmp_path / "20260831090000_init.sql"
    second = tmp_path / "20260911080000_lineage.sql"
    first.write_text("create table a;", encoding="utf-8")
    second.write_text("alter table a add column b int;", encoding="utf-8")
    connection = FakeConnection(applied=("20260831090000_init.sql",))

    applied = apply_migrations(connection, tmp_path)

    assert applied == ["20260911080000_lineage.sql"]
    assert any("alter table a add column b int" in script for script in connection.scripts)
    assert "20260911080000_lineage.sql" in connection.applied


def test_apply_migrations_dry_run_does_not_execute_sql(tmp_path: Path) -> None:
    migration = tmp_path / "20260916120000_prediction_lineage.sql"
    migration.write_text(
        "alter table public.predictions add column endpoint text;",
        encoding="utf-8",
    )
    connection = FakeConnection()

    applied = apply_migrations(connection, tmp_path, dry_run=True)

    assert applied == ["20260916120000_prediction_lineage.sql"]
    assert connection.scripts == []
    assert connection.applied == set()


def test_verify_schema_reports_missing_prediction_columns() -> None:
    connection = FakeConnection(
        tables=("predictions", "model_versions"),
        columns={
            "predictions": ("id", "features"),
            "model_versions": ("id", "metrics"),
        },
        buckets=("weather-mlops-dvc",),
    )

    missing = verify_schema(connection)

    assert "predictions.observation_date" in missing
    assert "predictions.location" in missing
    assert "predictions.endpoint" in missing
    assert "predictions.observed_label" in missing
    assert "model_versions.feature_schema" in missing
    assert "bucket:weather-mlops-mlflow" in missing


def test_verify_schema_is_empty_when_catalog_matches() -> None:
    connection = FakeConnection(
        tables=(
            "weather_observations",
            "dataset_versions",
            "ingestion_batches",
            "model_versions",
            "predictions",
            "drift_reports",
            "schema_migrations",
        ),
        columns={
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
        },
        buckets=("weather-mlops-dvc", "weather-mlops-mlflow"),
    )

    assert verify_schema(connection) == []


def test_split_sql_keeps_dollar_quoted_function_bodies() -> None:
    sql_path = PROJECT_ROOT / "supabase/migrations/20260911080000_dataset_lineage_and_vault.sql"
    sql = sql_path.read_text(encoding="utf-8")

    statements = split_sql(sql)

    assert any("get_app_secret" in statement for statement in statements)
    assert any("$$" in statement and "begin" in statement.lower() for statement in statements)


def test_repo_migrations_include_prediction_lineage_columns() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in list_migration_files(MIGRATIONS_DIR)
    )

    for column in ("observation_date", "endpoint", "observed_label", "feature_schema"):
        assert column in combined
    assert "predictions" in combined
    assert "put_app_secret" in combined
    assert "weather-mlops-dvc" in combined
    assert "weather-mlops-mlflow" in combined


def test_repo_migrations_alter_in_verify_columns_when_create_table_is_a_noop() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in list_migration_files(MIGRATIONS_DIR)
    ).lower()

    assert "add column if not exists probability" in combined
    assert "add column if not exists dataset_sha256" in combined
    assert "add column if not exists mlflow_model_version" in combined
    assert "model_versions_mlflow_run_id_key" in combined


def test_normalize_dsn_accepts_pooler_url_when_password_has_brackets() -> None:
    raw = (
        "postgresql://postgres.fgxgenjxslytnqygpefk:p[ass]word"
        "@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    )

    normalized = normalize_dsn(raw)

    assert "aws-0-eu-west-1.pooler.supabase.com" in normalized
    assert "p%5Bass%5Dword" in normalized
    assert "sslmode=require" in normalized


def test_normalize_dsn_does_not_double_encode_or_drop_sslmode() -> None:
    raw = "postgresql://postgres:secret%40x@db.example.supabase.co:5432/postgres?sslmode=require"

    assert normalize_dsn(raw) == raw


def test_connection_error_hint_explains_pooler_tenant_miss() -> None:
    hint = connection_error_hint(
        RuntimeError("FATAL: (ENOTFOUND) tenant/user postgres.abc not found")
    )

    assert hint is not None
    assert "aws-0" in hint
    assert "Connect" in hint
    assert connection_error_hint(RuntimeError("password authentication failed")) is None
