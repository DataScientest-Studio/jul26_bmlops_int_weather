import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from weather_mlops.config.settings import PROJECT_ROOT, settings


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_name: str
    path: str
    size_bytes: int
    md5: str
    sha256: str
    created_at: str | None = None


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def display_path(path: Path) -> str:
    resolved_path = path.resolve()

    try:
        return str(resolved_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved_path)


def build_dataset_metadata(
    path: Path | None = None,
    dataset_name: str = "weatherAUS",
) -> DatasetMetadata:
    dataset_path = path or settings.raw_data_path

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    return DatasetMetadata(
        dataset_name=dataset_name,
        path=display_path(dataset_path),
        size_bytes=dataset_path.stat().st_size,
        md5=_hash_file(dataset_path, "md5"),
        sha256=_hash_file(dataset_path, "sha256"),
    )


def write_dataset_metadata(
    metadata: DatasetMetadata,
    path: Path | None = None,
) -> Path:
    output_path = path or settings.dataset_metadata_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(metadata), indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write hash metadata for a dataset file.")
    parser.add_argument("--input", type=Path, default=settings.raw_data_path)
    parser.add_argument("--output", type=Path, default=settings.dataset_metadata_path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = build_dataset_metadata(args.input)
    output_path = write_dataset_metadata(metadata, args.output)

    print(f"Wrote dataset metadata to {output_path}")
    print(f"md5:    {metadata.md5}")
    print(f"sha256: {metadata.sha256}")


if __name__ == "__main__":
    main()
