"""Copy for the five-minute defense deck."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slide:
    id: str
    title: str
    kicker: str
    notes: tuple[str, ...] = ()


SLIDES: tuple[Slide, ...] = (
    Slide(
        id="architecture",
        title="One loop",
        kicker="Architecture",
        notes=(
            "Open-Meteo in, FastAPI out. Nginx is the public edge.",
            "Airflow will later POST /train. It is not in Compose yet.",
            "DVC is only how a developer pulls files. Production lineage is Postgres.",
        ),
    ),
    Slide(
        id="stores",
        title="Two buckets, one catalog",
        kicker="Data",
        notes=(
            "weather-mlops-dvc holds datasets. weather-mlops-mlflow holds MLflow artifacts.",
            "dataset_versions names each snapshot by sha256.",
            "Vault holds S3 keys and API basic auth. Streamlit never sees the service-role key.",
        ),
    ),
    Slide(
        id="live",
        title="Will it rain tomorrow?",
        kicker="Demo",
        notes=(
            "This page calls Nginx, which proxies /health and /predict/live_data.",
            "It uses basic auth hydrated from Vault. It never loads SUPABASE_KEY.",
        ),
    ),
)


def slide_index(slide_id: str) -> int:
    for index, slide in enumerate(SLIDES):
        if slide.id == slide_id:
            return index
    raise KeyError(slide_id)
