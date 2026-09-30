"""Reconcile serving predictions only after their next-day weather outcome exists."""

from __future__ import annotations

from typing import Any

import pandas as pd

from weather_mlops.config.settings import settings


def reconcile_prediction_outcomes(rows: pd.DataFrame, client: Any) -> int:
    """Fill only empty labels for WeatherAUS-compatible rows with a known outcome."""

    required = {"Date", "Location", "RainTomorrow"}
    if not required.issubset(rows.columns):
        raise ValueError(f"Outcome rows must contain {sorted(required)}")

    updated = 0
    for row in rows.loc[rows["RainTomorrow"].isin(["Yes", "No"])].itertuples(index=False):
        payload = row._asdict()
        (
            client.table(settings.supabase_predictions_table)
            .update({"observed_label": payload["RainTomorrow"]})
            .eq("observation_date", str(payload["Date"]))
            .eq("location", payload["Location"])
            .is_("observed_label", "null")
            .execute()
        )
        updated += 1
    return updated
