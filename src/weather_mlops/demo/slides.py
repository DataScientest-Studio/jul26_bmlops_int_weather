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
            "The two small panels below are the real Grafana request-rate and duration "
            "panels for the last 5 minutes. They show /health, /predict/live_data, and "
            "/train, not the /metrics scrape, and they refresh every 5 seconds.",
        ),
    ),
    Slide(
        id="train",
        title="Model training",
        kicker="Model training",
        notes=(
            "Click Train model now. This sends one authenticated POST /train request through "
            "the same Nginx gateway as the prediction.",
            "While it runs, the page shows a training state instead of asking us to explain "
            "background monitoring charts.",
            "The API returns the training and validation metrics directly. Point to validation "
            "Recall, ROC-AUC, and Accuracy.",
            "The result is the visible proof: a real model was fitted and evaluated during "
            "the demo.",
        ),
    ),
)


def slide_index(slide_id: str) -> int:
    for index, slide in enumerate(SLIDES):
        if slide.id == slide_id:
            return index
    raise KeyError(slide_id)
