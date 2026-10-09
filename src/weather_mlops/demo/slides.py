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
            "Simulate drift shifts humidity and location, then runs the real Evidently check.",
            "The live Grafana panels show report age, drifted features, and whether the "
            "quality gate asked to retrain.",
            "Only after the simulation do we show weather_retrain and its actual Airflow "
            "task states.",
            "A request does not promote a model: compare must still validate a candidate "
            "before the champion changes.",
        ),
    ),
)


def slide_index(slide_id: str) -> int:
    for index, slide in enumerate(SLIDES):
        if slide.id == slide_id:
            return index
    raise KeyError(slide_id)
