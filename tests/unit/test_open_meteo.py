import pandas as pd
import requests

from weather_mlops.data.open_meteo import (
    OpenMeteoError,
    WeatherLocation,
    _get_json,
    normalize_open_meteo_payloads,
    read_locations,
)
from weather_mlops.data.weatheraus_schema import WEATHERAUS_COLUMNS


def test_read_locations_loads_required_columns(tmp_path) -> None:
    path = tmp_path / "locations.csv"
    path.write_text(
        "location,latitude,longitude,timezone\nSydney,-33.8688,151.2093,Australia/Sydney\n",
        encoding="utf-8",
    )

    assert read_locations(path) == [
        WeatherLocation(
            location="Sydney",
            latitude=-33.8688,
            longitude=151.2093,
            timezone="Australia/Sydney",
        )
    ]


def test_normalize_open_meteo_payloads_writes_weatheraus_columns() -> None:
    payloads = [
        {
            "provider": "open-meteo",
            "location": {
                "location": "Sydney",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "timezone": "Australia/Sydney",
            },
            "date": "2026-09-01",
            "response": {
                "daily": {
                    "time": ["2026-09-01", "2026-09-02"],
                    "temperature_2m_min": [12.2, 11.8],
                    "temperature_2m_max": [23.5, 19.0],
                    "rain_sum": [0.4, 2.1],
                    "precipitation_sum": [0.4, 2.1],
                    "wind_gusts_10m_max": [43.2, 38.0],
                    "wind_direction_10m_dominant": [280, 230],
                    "sunshine_duration": [28_800, 18_000],
                    "et0_fao_evapotranspiration": [3.2, 2.4],
                },
                "hourly": {
                    "time": [
                        "2026-09-01T09:00",
                        "2026-09-01T15:00",
                        "2026-09-02T09:00",
                    ],
                    "temperature_2m": [16.2, 22.7, 15.1],
                    "relative_humidity_2m": [72, 48, 81],
                    "pressure_msl": [1014, 1010, 1009],
                    "cloud_cover": [25, 75, 90],
                    "wind_speed_10m": [10.8, 18.0, 13.0],
                    "wind_direction_10m": [10, 270, 200],
                    "wind_gusts_10m": [19.0, 30.0, 22.0],
                },
            },
        }
    ]

    result = normalize_open_meteo_payloads(payloads)

    assert result.columns.tolist() == WEATHERAUS_COLUMNS
    assert result.loc[0, "Date"] == "2026-09-01"
    assert result.loc[0, "Location"] == "Sydney"
    assert result.loc[0, "MinTemp"] == 12.2
    assert result.loc[0, "MaxTemp"] == 23.5
    assert result.loc[0, "Rainfall"] == 0.4
    assert result.loc[0, "Evaporation"] == 3.2
    assert result.loc[0, "Sunshine"] == 8.0
    assert result.loc[0, "WindGustDir"] == "W"
    assert result.loc[0, "WindGustSpeed"] == 43.2
    assert result.loc[0, "WindDir9am"] == "N"
    assert result.loc[0, "WindDir3pm"] == "W"
    assert result.loc[0, "WindSpeed9am"] == 10.8
    assert result.loc[0, "WindSpeed3pm"] == 18.0
    assert result.loc[0, "Cloud9am"] == 2
    assert result.loc[0, "Cloud3pm"] == 6
    assert result.loc[0, "RainToday"] == "No"
    assert result.loc[0, "RainTomorrow"] == "Yes"


def test_get_json_reports_open_meteo_errors(monkeypatch) -> None:
    class FakeResponse:
        ok = False
        status_code = 400
        text = '{"reason":"Invalid timezone"}'

        def json(self) -> dict[str, str]:
            return {"reason": "Invalid timezone"}

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("weather_mlops.data.open_meteo.requests.get", fake_get)

    try:
        _get_json("https://archive-api.open-meteo.com/v1/archive", {"timezone": "bad"}, 30)
    except OpenMeteoError as error:
        message = str(error)
        assert "HTTP 400" in message
        assert "Invalid timezone" in message
    else:
        raise AssertionError("Expected invalid Open-Meteo request to fail.")


def test_get_json_wraps_network_errors(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError("network blocked")

    monkeypatch.setattr("weather_mlops.data.open_meteo.requests.get", fake_get)

    try:
        _get_json("https://archive-api.open-meteo.com/v1/archive", {}, 30)
    except OpenMeteoError as error:
        message = str(error)
        assert "archive" in message
        assert "ConnectionError" in message
        assert "network blocked" not in message
    else:
        raise AssertionError("Expected Open-Meteo network request to fail.")


def test_normalize_open_meteo_payloads_leaves_missing_values_when_hours_absent() -> None:
    payloads = [
        {
            "provider": "open-meteo",
            "location": {"location": "Sydney"},
            "date": "2026-09-01",
            "response": {"daily": {"time": ["2026-09-01"]}, "hourly": {"time": []}},
        }
    ]

    result = normalize_open_meteo_payloads(payloads)

    assert pd.isna(result.loc[0, "Temp9am"])
    assert pd.isna(result.loc[0, "RainTomorrow"])
