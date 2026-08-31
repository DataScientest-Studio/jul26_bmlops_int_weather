import argparse
import os
import subprocess
from pathlib import Path

from weather_mlops.config.settings import PROJECT_ROOT, settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure DVC to use Supabase Storage.")
    parser.add_argument("--remote-name", default=settings.dvc_remote_name)
    parser.add_argument("--remote-url", default=settings.dvc_remote_url)
    parser.add_argument("--endpoint-url", default=settings.supabase_s3_endpoint)
    parser.add_argument("--region", default=settings.aws_default_region)
    parser.add_argument("--access-key-id", default=settings.aws_access_key_id)
    parser.add_argument("--secret-access-key", default=settings.aws_secret_access_key)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.endpoint_url:
        raise ValueError(
            "SUPABASE_S3_ENDPOINT must be set, for example "
            "https://<project-ref>.storage.supabase.co/storage/v1/s3"
        )
    if not args.access_key_id or not args.secret_access_key:
        raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env.")

    env = os.environ.copy()
    env["DVC_NO_ANALYTICS"] = "1"
    env["DVC_SITE_CACHE_DIR"] = str(PROJECT_ROOT / ".dvc" / "tmp" / "cache-home")
    env["XDG_CACHE_HOME"] = str(PROJECT_ROOT / ".dvc" / "tmp" / "cache-home")

    if not Path(".dvc/config").exists():
        subprocess.run(["dvc", "init", "--no-scm"], check=True, env=env)
    subprocess.run(
        ["dvc", "remote", "add", "-d", "-f", args.remote_name, args.remote_url],
        check=True,
        env=env,
    )
    subprocess.run(
        ["dvc", "remote", "modify", args.remote_name, "endpointurl", args.endpoint_url],
        check=True,
        env=env,
    )
    subprocess.run(
        ["dvc", "remote", "modify", args.remote_name, "region", args.region],
        check=True,
        env=env,
    )
    subprocess.run(
        [
            "dvc",
            "remote",
            "modify",
            "--local",
            args.remote_name,
            "access_key_id",
            args.access_key_id,
        ],
        check=True,
        env=env,
    )
    subprocess.run(
        [
            "dvc",
            "remote",
            "modify",
            "--local",
            args.remote_name,
            "secret_access_key",
            args.secret_access_key,
        ],
        check=True,
        env=env,
    )

    print(f"Configured DVC remote {args.remote_name}: {args.remote_url}")
    print(f"Endpoint: {args.endpoint_url}")
    print("Stored Supabase S3 credentials in .dvc/config.local.")


if __name__ == "__main__":
    main()
