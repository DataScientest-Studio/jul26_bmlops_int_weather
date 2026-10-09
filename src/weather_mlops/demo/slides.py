"""Copy for the defense demo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slide:
    id: str
    title: str
    kicker: str
    notes: tuple[str, ...] = ()


SLIDES: tuple[Slide, ...] = (
    Slide(
        id="live",
        title="Will it rain tomorrow?",
        kicker="Live prediction",
        notes=(
            "The live outcome stays on screen: a clear Yes or No and the rain probability.",
            "This page calls Nginx, which proxies /health and /predict/live_data.",
            "It uses basic auth hydrated from Vault. It never loads SUPABASE_KEY.",
            "The three small panels below are the real Grafana request, error-rate, "
            "and latency panels.",
        ),
    ),
    Slide(
        id="health",
        title="Model health",
        kicker="Model health",
        notes=(
            "First we run weather_pipeline: it ingests and merges the prepared batch, "
            "preprocesses it, then snapshots both raw and processed data in Supabase Storage.",
            "The dataset hash is recorded before monitoring, so training uses a reproducible "
            "version rather than a mutable local file.",
            "The live Grafana trends show Evidently's drift share, delayed quality, and the "
            "retraining gate. We can point to the exact monitoring evidence before acting.",
            "For the demo we can manually start weather_retrain on the latest registered snapshot. "
            "Airflow shows train, evaluation, and compare as it runs.",
            "Train registers the candidate in MLflow. Compare only promotes it to champion if it "
            "beats the validation guards on that same dataset version.",
        ),
    ),
)


def slide_index(slide_id: str) -> int:
    for index, slide in enumerate(SLIDES):
        if slide.id == slide_id:
            return index
    raise KeyError(slide_id)
