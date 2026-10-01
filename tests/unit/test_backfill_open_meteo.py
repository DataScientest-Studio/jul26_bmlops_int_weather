import importlib.util
from datetime import date
from pathlib import Path

import pandas as pd

from weather_mlops.data.open_meteo import WeatherLocation

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_backfill_module():
    spec = importlib.util.spec_from_file_location(
        "backfill_open_meteo",
        PROJECT_ROOT / "scripts" / "backfill_open_meteo.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_range_writes_resumable_australian_chunks(tmp_path) -> None:
    module = _load_backfill_module()
    calls = []

    def fetch(location, start_date, end_date):
        calls.append((location.location, start_date, end_date))
        return {
            "location": {"location": location.location},
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    def normalize(payloads):
        return pd.DataFrame(
            [
                {"Date": payload["start_date"], "Location": payload["location"]["location"]}
                for payload in payloads
            ]
        )

    result = module.backfill_range(
        locations=[WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney")],
        start_date=date(2017, 6, 27),
        end_date=date(2017, 6, 30),
        chunk_days=2,
        output_dir=tmp_path,
        fetch_payload=fetch,
        normalize_payloads=normalize,
    )

    assert [entry["status"] for entry in result] == ["written", "written"]
    assert len(calls) == 2
    assert (tmp_path / "open_meteo_backfill_20170627_20170628.json").exists()
    assert (tmp_path / "open_meteo_backfill_20170629_20170630.csv").exists()

    resumed = module.backfill_range(
        locations=[WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney")],
        start_date=date(2017, 6, 27),
        end_date=date(2017, 6, 30),
        chunk_days=2,
        output_dir=tmp_path,
        fetch_payload=fetch,
        normalize_payloads=normalize,
    )

    assert [entry["status"] for entry in resumed] == ["skipped", "skipped"]
    assert len(calls) == 2
