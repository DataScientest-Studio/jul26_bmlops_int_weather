"""Reconcile serving predictions only after their next-day weather outcome exists."""

from __future__ import annotations

import argparse
from typing import Any

import pandas as pd

from weather_mlops.config.settings import settings


def load_unlabelled_predictions(client: Any) -> pd.DataFrame:
    """Return date and station of every prediction that has no outcome yet"""

    response = (
        client.table(settings.supabase_predictions_table)
        .select("observation_date,location")
        .is_("observed_label", "null")
        .execute()
    )
    return pd.DataFrame(response.data, columns=["observation_date", "location"])


def reconcile_prediction_outcomes(rows: pd.DataFrame, client: Any) -> int:
    """Fill only empty labels for WeatherAUS-compatible rows with a known outcome."""

    required = {"Date", "Location", "RainTomorrow"}
    if not required.issubset(rows.columns):
        raise ValueError(f"Outcome rows must contain {sorted(required)}")

    known = rows.loc[rows["RainTomorrow"].isin(["Yes", "No"])].copy()
    pending = load_unlabelled_predictions(client)
    known["Date"] = known["Date"].astype(str)
    pending["observation_date"] = pending["observation_date"].astype(str)
    matches = pending.merge(
        known, left_on=["observation_date", "location"], right_on=["Date", "Location"]
    )
    matches = matches.drop_duplicates(subset=["Date", "Location"])

    updated = 0
    for row in matches.itertuples(index=False):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile mature prediction outcomes.")
    parser.add_argument("--input", type=str, default=str(settings.raw_data_path))
    args = parser.parse_args()
    from weather_mlops.data.database import get_supabase_client

    rows = pd.read_csv(args.input)
    updated = reconcile_prediction_outcomes(rows, get_supabase_client())
    print(f"Reconciled {updated} prediction outcomes.")


if __name__ == "__main__":
    main()
