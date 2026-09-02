from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    seed_raw_data_path: Path = PROJECT_ROOT / "data" / "raw" / "weatherAUS.csv"
    raw_incremental_dir: Path = PROJECT_ROOT / "data" / "raw" / "incremental"
    raw_data_path: Path = PROJECT_ROOT / "data" / "raw" / "weatherAUS_current.csv"
    weather_locations_path: Path = PROJECT_ROOT / "references" / "weather_locations.csv"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    x_train_path: Path = PROJECT_ROOT / "data" / "processed" / "X_train.csv"
    x_validation_path: Path = PROJECT_ROOT / "data" / "processed" / "X_validation.csv"
    x_test_path: Path = PROJECT_ROOT / "data" / "processed" / "X_test.csv"
    y_train_path: Path = PROJECT_ROOT / "data" / "processed" / "y_train.csv"
    y_validation_path: Path = PROJECT_ROOT / "data" / "processed" / "y_validation.csv"
    y_test_path: Path = PROJECT_ROOT / "data" / "processed" / "y_test.csv"
    sample_prediction_input_path: Path = PROJECT_ROOT / "sample_prediction.json"
    sample_prediction_output_path: Path = (
        PROJECT_ROOT / "data" / "predictions" / "sample_prediction.json"
    )
    model_path: Path = PROJECT_ROOT / "models" / "rain_classifier.joblib"
    dataset_metadata_path: Path = PROJECT_ROOT / "data" / "metadata" / "weatherAUS.json"
    train_metrics_path: Path = PROJECT_ROOT / "reports" / "metrics" / "train.json"
    validation_metrics_path: Path = PROJECT_ROOT / "reports" / "metrics" / "validation.json"
    evaluation_metrics_path: Path = PROJECT_ROOT / "reports" / "metrics" / "evaluation.json"

    # Supabase
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_weather_table: str = "weather_observations"
    supabase_dataset_versions_table: str = "dataset_versions"

    # DVC remote backed by Supabase Storage's S3-compatible API.
    dvc_remote_name: str = "supabase"
    dvc_remote_url: str = "s3://weather-mlops-dvc"
    supabase_s3_endpoint: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_default_region: str = "local"

    # Model
    random_state: int = 42
    train_fraction: float = 0.7
    validation_fraction: float = 0.15


settings = Settings()
