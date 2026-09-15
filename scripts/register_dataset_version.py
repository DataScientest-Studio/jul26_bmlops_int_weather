import argparse
from pathlib import Path

from weather_mlops.config.settings import settings
from weather_mlops.data.snapshots import register_local_snapshot, register_processed_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload an immutable snapshot and register it in dataset_versions."
    )
    parser.add_argument("--path", type=Path, default=None)
    parser.add_argument("--kind", choices=("raw", "processed", "all"), default="all")
    parser.add_argument("--created-by", default="local")
    parser.add_argument("--source", default="weatherAUS")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the catalog record without uploading or writing to Supabase.",
    )
    return parser.parse_args()


def _print_record(kind: str, metadata, dry_run: bool) -> None:
    print(f"--- {kind} ---")
    print(f"dataset_name: {metadata.dataset_name}")
    print(f"version_kind: {metadata.version_kind}")
    print(f"sha256:       {metadata.sha256}")
    print(f"storage_uri:  {metadata.storage_uri}")
    print(f"git_commit:   {metadata.git_commit}")
    if dry_run:
        print("Dry run: nothing uploaded or stored.")
        return
    print("Uploaded snapshot (or it already existed) and stored dataset_versions.")


def main() -> None:
    args = parse_args()
    if args.path is not None and args.kind == "all":
        raise SystemExit("Pass --path only with --kind raw or --kind processed.")
    if not args.dry_run and (not settings.supabase_url or not settings.supabase_key):
        raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env.")

    kinds = ("raw", "processed") if args.kind == "all" else (args.kind,)
    for kind in kinds:
        if kind == "processed":
            metadata = register_processed_snapshot(
                args.path,
                created_by=args.created_by,
                source=args.source,
                dry_run=args.dry_run,
            )
        else:
            path = args.path or settings.raw_data_path
            if not path.exists():
                raise SystemExit(f"Missing raw snapshot at {path}")
            metadata = register_local_snapshot(
                path,
                kind="raw",
                created_by=args.created_by,
                source=args.source,
                dry_run=args.dry_run,
            )
        _print_record(kind, metadata, args.dry_run)


if __name__ == "__main__":
    main()
