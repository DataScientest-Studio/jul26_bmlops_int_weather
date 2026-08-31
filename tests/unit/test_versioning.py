from weather_mlops.config.settings import PROJECT_ROOT
from weather_mlops.data.versioning import build_dataset_metadata, display_path


def test_build_dataset_metadata_hashes_file(tmp_path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("a,b\n1,2\n", encoding="utf-8")

    metadata = build_dataset_metadata(dataset)

    assert metadata.dataset_name == "weatherAUS"
    assert metadata.size_bytes == 8
    assert metadata.md5 == "e5ebd4c02cefbe7955977c67ada242b7"
    assert metadata.sha256 == "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470"


def test_display_path_uses_repo_relative_paths() -> None:
    assert display_path(PROJECT_ROOT / "data/raw/weatherAUS.csv") == "data/raw/weatherAUS.csv"
