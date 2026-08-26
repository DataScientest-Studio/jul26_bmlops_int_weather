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
    raw_data_path: Path = PROJECT_ROOT / "data" / "raw" / "weatherAUS.csv"
    model_path: Path = PROJECT_ROOT / "models" / "rain_classifier.joblib"

    # Supabase
    supabase_url: str | None = None
    supabase_key: str | None = None

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
