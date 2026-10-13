import importlib.util
from datetime import date
from pathlib import Path

import pandas as pd

from weather_mlops.data.open_meteo import OpenMeteoRateLimitError, WeatherLocation

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

    def fetch(locations, start_date, end_date):
        calls.append(([location.location for location in locations], start_date, end_date))
        return [
            {
                "location": {"location": location.location},
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
            for location in locations
        ]

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
        fetch_payloads=fetch,
        normalize_payloads=normalize,
    )

    assert [entry["status"] for entry in result["results"]] == ["written", "written"]
    assert result["stopped_reason"] is None
    assert result["chunks_complete"] == 2
    assert len(calls) == 2
    assert (tmp_path / "open_meteo_backfill_20170627_20170628.json").exists()
    assert (tmp_path / "open_meteo_backfill_20170629_20170630.csv").exists()
    assert (tmp_path / "open_meteo_backfill_20170627_20170628.done").exists()

    resumed = module.backfill_range(
        locations=[WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney")],
        start_date=date(2017, 6, 27),
        end_date=date(2017, 6, 30),
        chunk_days=2,
        output_dir=tmp_path,
        fetch_payloads=fetch,
        normalize_payloads=normalize,
    )

    assert [entry["status"] for entry in resumed["results"]] == ["skipped", "skipped"]
    assert len(calls) == 2
    assert module.exit_code_for_stop(None) == 0
    assert module.exit_code_for_stop("rate_limit") == 75


def _payloads(locations, start_date, end_date):
    return [
        {
            "location": {"location": location.location},
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        for location in locations
    ]


def _normalize(payloads):
    return pd.DataFrame(
        [
            {"Date": payload["start_date"], "Location": payload["location"]["location"]}
            for payload in payloads
        ]
    )


def test_backfill_stops_on_rate_limit_and_resumes_later_chunks(tmp_path) -> None:
    module = _load_backfill_module()
    calls = []

    def fetch(locations, start_date, end_date):
        calls.append(start_date)
        if len(calls) == 2:
            raise OpenMeteoRateLimitError("hourly limit", scope="hour")
        return _payloads(locations, start_date, end_date)

    kwargs = {
        "locations": [WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney")],
        "start_date": date(2017, 6, 27),
        "end_date": date(2017, 7, 2),
        "chunk_days": 2,
        "output_dir": tmp_path,
        "fetch_payloads": fetch,
        "normalize_payloads": _normalize,
    }
    stopped = module.backfill_range(**kwargs)

    assert stopped["stopped_reason"] == "rate_limit"
    assert stopped["chunks_complete"] == 1
    assert calls == [date(2017, 6, 27), date(2017, 6, 29)]
    assert (tmp_path / "open_meteo_backfill_20170627_20170628.csv").exists()
    assert (tmp_path / "open_meteo_backfill_20170629_20170630.csv").exists() is False

    resumed = module.backfill_range(**kwargs)

    assert resumed["stopped_reason"] is None
    assert resumed["chunks_complete"] == 3
    assert calls == [
        date(2017, 6, 27),
        date(2017, 6, 29),
        date(2017, 6, 29),
        date(2017, 7, 1),
    ]


def test_backfill_resumes_a_location_shard_after_a_rate_limit(tmp_path) -> None:
    module = _load_backfill_module()
    calls = []

    def fetch(locations, start_date, end_date):
        names = [location.location for location in locations]
        calls.append(names)
        if len(calls) == 2:
            raise OpenMeteoRateLimitError("daily limit", scope="day")
        return _payloads(locations, start_date, end_date)

    locations = [
        WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney"),
        WeatherLocation("Perth", -31.9, 115.9, "Australia/Perth"),
    ]
    kwargs = {
        "locations": locations,
        "start_date": date(2017, 6, 27),
        "end_date": date(2017, 6, 28),
        "chunk_days": 10,
        "output_dir": tmp_path,
        "location_batch_size": 1,
        "fetch_payloads": fetch,
        "normalize_payloads": _normalize,
    }
    stopped = module.backfill_range(**kwargs)
    assert stopped["chunks_complete"] == 0
    assert calls == [["Sydney"], ["Perth"]]
    assert (tmp_path / "open_meteo_backfill_20170627_20170628_loc000.csv").exists()
    assert (tmp_path / "open_meteo_backfill_20170627_20170628_loc001.csv").exists() is False

    resumed = module.backfill_range(**kwargs)
    assert resumed["stopped_reason"] is None
    assert resumed["chunks_complete"] == 1
    assert calls == [["Sydney"], ["Perth"], ["Perth"]]
    done = json_done(tmp_path / "open_meteo_backfill_20170627_20170628.done")
    assert done["csv_files"] == [
        "open_meteo_backfill_20170627_20170628_loc000.csv",
        "open_meteo_backfill_20170627_20170628_loc001.csv",
    ]


def json_done(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def test_backfill_request_budget_resumes_without_refetching(tmp_path) -> None:
    module = _load_backfill_module()
    calls = []

    def fetch(locations, start_date, end_date):
        calls.append((start_date, end_date))
        return _payloads(locations, start_date, end_date)

    kwargs = {
        "locations": [WeatherLocation("Sydney", -33.8, 151.2, "Australia/Sydney")],
        "start_date": date(2017, 6, 27),
        "end_date": date(2017, 6, 30),
        "chunk_days": 2,
        "output_dir": tmp_path,
        "max_requests": 1,
        "fetch_payloads": fetch,
        "normalize_payloads": _normalize,
    }
    first = module.backfill_range(**kwargs)
    second = module.backfill_range(**kwargs)

    assert first["stopped_reason"] == "request_budget"
    assert first["chunks_complete"] == 1
    assert second["stopped_reason"] is None
    assert second["chunks_complete"] == 2
    assert calls == [
        (date(2017, 6, 27), date(2017, 6, 28)),
        (date(2017, 6, 29), date(2017, 6, 30)),
    ]
