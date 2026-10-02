from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from weather_mlops.data.weatheraus_schema import WEATHERAUS_COLUMNS

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
RAIN_THRESHOLD_MM = 1.0
AUSTRALIAN_TIMEZONE_PREFIX = "Australia/"
# Norfolk Island is an Australian external territory represented by a
# `Pacific/*` IANA timezone in the WeatherAUS location catalogue.
AUSTRALIAN_EXTERNAL_TERRITORY_TIMEZONES = {"Pacific/Norfolk"}
RATE_LIMIT_RETRIES = 5
DEFAULT_RATE_LIMIT_WAIT_SECONDS = 60.0

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]
DAILY_VARIABLES = [
    "temperature_2m_min",
    "temperature_2m_max",
    "rain_sum",
    "precipitation_sum",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "sunshine_duration",
    "et0_fao_evapotranspiration",
]


class OpenMeteoError(RuntimeError):
    """Raised when Open-Meteo rejects or fails a request."""


@dataclass(frozen=True)
class WeatherLocation:
    location: str
    latitude: float
    longitude: float
    timezone: str


def read_locations(path: Path) -> list[WeatherLocation]:
    dataframe = pd.read_csv(path)
    required_columns = {"location", "latitude", "longitude", "timezone"}
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{path} is missing required columns: {missing}")

    return [
        WeatherLocation(
            location=str(row.location),
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            timezone=str(row.timezone),
        )
        for row in dataframe.itertuples(index=False)
    ]


def fetch_open_meteo_daily_payload(
    location: WeatherLocation,
    observation_date: date,
    timeout_seconds: int = 30,
    include_next_day: bool = True,
) -> dict[str, Any]:
    end_date = observation_date + timedelta(days=1) if include_next_day else observation_date

    response = _get_json(
        ARCHIVE_URL,
        {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": observation_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(HOURLY_VARIABLES),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": location.timezone,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        },
        timeout_seconds,
    )

    return {
        "provider": "open-meteo",
        "location": asdict(location),
        "date": observation_date.isoformat(),
        "response": response,
    }


def ensure_australian_locations(locations: list[WeatherLocation]) -> None:
    """Reject non-Australian fixtures from the production backfill path."""

    invalid = [
        location.location
        for location in locations
        if not location.timezone.startswith(AUSTRALIAN_TIMEZONE_PREFIX)
        and location.timezone not in AUSTRALIAN_EXTERNAL_TERRITORY_TIMEZONES
    ]
    if invalid:
        raise ValueError(
            "Historical production backfill accepts Australian timezones and "
            "approved Australian external territories; "
            f"received {', '.join(invalid)}."
        )


def chunk_date_range(
    start_date: date, end_date: date, *, chunk_days: int
) -> list[tuple[date, date]]:
    """Partition an inclusive date interval into contiguous non-overlapping chunks."""

    if chunk_days < 1:
        raise ValueError("chunk_days must be positive.")
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date.")
    chunks: list[tuple[date, date]] = []
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def fetch_open_meteo_range_payload(
    location: WeatherLocation,
    start_date: date,
    end_date: date,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Fetch an inclusive historical range plus its next day for final labels."""

    return fetch_open_meteo_range_payloads(
        [location], start_date, end_date, timeout_seconds=timeout_seconds
    )[0]


def fetch_open_meteo_range_payloads(
    locations: list[WeatherLocation],
    start_date: date,
    end_date: date,
    timeout_seconds: int = 60,
) -> list[dict[str, Any]]:
    """Fetch a historical range for multiple locations in one archive request."""

    if end_date < start_date:
        raise ValueError("end_date must not precede start_date.")
    if not locations:
        raise ValueError("At least one location is required.")
    response = _get_json(
        ARCHIVE_URL,
        {
            "latitude": ",".join(str(location.latitude) for location in locations),
            "longitude": ",".join(str(location.longitude) for location in locations),
            "start_date": start_date.isoformat(),
            "end_date": (end_date + timedelta(days=1)).isoformat(),
            "hourly": ",".join(HOURLY_VARIABLES),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": ",".join(location.timezone for location in locations),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        },
        timeout_seconds,
    )
    responses = response if isinstance(response, list) else [response]
    if len(responses) != len(locations) or not all(isinstance(item, dict) for item in responses):
        raise OpenMeteoError(
            "Open-Meteo returned an unexpected number or shape of location responses."
        )
    return [
        {
            "provider": "open-meteo",
            "location": asdict(location),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "response": location_response,
        }
        for location, location_response in zip(locations, responses, strict=True)
    ]


def _get_json(
    url: str,
    params: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any] | list[dict[str, Any]]:
    endpoint = url.rsplit("/", maxsplit=1)[-1]
    for retry in range(RATE_LIMIT_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout_seconds)
        except requests.RequestException as error:
            raise OpenMeteoError(
                f"Open-Meteo request failed for endpoint '{endpoint}'. "
                f"Check network access and retry. Details: {error.__class__.__name__}"
            ) from error

        if response.ok:
            payload = response.json()
            if isinstance(payload, dict) or (
                isinstance(payload, list) and all(isinstance(item, dict) for item in payload)
            ):
                return payload
            raise OpenMeteoError("Open-Meteo returned an unexpected JSON response shape.")

        if response.status_code == 429 and retry < RATE_LIMIT_RETRIES:
            wait_seconds = _rate_limit_wait_seconds(response)
            print(
                "Open-Meteo rate limit reached; retrying "
                f"endpoint '{endpoint}' in {wait_seconds:g}s "
                f"({retry + 1}/{RATE_LIMIT_RETRIES})."
            )
            time.sleep(wait_seconds)
            continue

        detail = _response_detail(response)
        raise OpenMeteoError(
            f"Open-Meteo request failed for endpoint '{endpoint}' "
            f"(HTTP {response.status_code}). Response: {detail}"
        )

    raise AssertionError("Rate-limit retry loop exited unexpectedly.")


def _rate_limit_wait_seconds(response: requests.Response) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return DEFAULT_RATE_LIMIT_WAIT_SECONDS
    try:
        return max(float(retry_after), 1.0)
    except ValueError:
        return DEFAULT_RATE_LIMIT_WAIT_SECONDS


def _response_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]

    if isinstance(payload, dict):
        for key in ("reason", "message", "error"):
            if key in payload:
                return str(payload[key])
    return str(payload)[:300]


def normalize_open_meteo_payloads(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [_normalize_payload(payload) for payload in payloads]
    return pd.DataFrame(rows, columns=WEATHERAUS_COLUMNS)


def normalize_open_meteo_range_payloads(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    """Expand historical range responses into one labeled row per observation day."""

    rows: list[dict[str, Any]] = []
    for payload in payloads:
        start_date = date.fromisoformat(payload["start_date"])
        end_date = date.fromisoformat(payload["end_date"])
        for observation_date, _chunk_end in chunk_date_range(
            start_date,
            end_date,
            chunk_days=1,
        ):
            daily_payload = {**payload, "date": observation_date.isoformat()}
            rows.append(_normalize_payload(daily_payload))
    return pd.DataFrame(rows, columns=WEATHERAUS_COLUMNS)


def write_open_meteo_snapshot(
    payloads: list[dict[str, Any]],
    normalized: pd.DataFrame,
    output_dir: Path,
    observation_date: date,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"open_meteo_{observation_date:%Y%m%d}.json"
    csv_path = output_dir / f"open_meteo_{observation_date:%Y%m%d}.csv"

    json_path.write_text(json.dumps(payloads, indent=2) + "\n", encoding="utf-8")
    normalized.to_csv(csv_path, index=False)
    return json_path, csv_path


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    location = payload["location"]
    observation_date = payload["date"]
    response = payload.get("response", {})
    daily = response.get("daily", {})
    hourly = response.get("hourly", {})

    today = _daily_record(daily, observation_date)
    tomorrow = _daily_record(daily, _next_date(observation_date))
    morning = _hourly_record(hourly, observation_date, 9)
    afternoon = _hourly_record(hourly, observation_date, 15)

    rainfall = _daily_rainfall_mm(today)
    next_day_rainfall = _daily_rainfall_mm(tomorrow)

    return {
        "Date": observation_date,
        "Location": location["location"],
        "MinTemp": today.get("temperature_2m_min"),
        "MaxTemp": today.get("temperature_2m_max"),
        "Rainfall": rainfall,
        "Evaporation": today.get("et0_fao_evapotranspiration"),
        "Sunshine": _seconds_to_hours(today.get("sunshine_duration")),
        "WindGustDir": _wind_direction(today.get("wind_direction_10m_dominant")),
        "WindGustSpeed": today.get("wind_gusts_10m_max"),
        "WindDir9am": _wind_direction(morning.get("wind_direction_10m")),
        "WindDir3pm": _wind_direction(afternoon.get("wind_direction_10m")),
        "WindSpeed9am": morning.get("wind_speed_10m"),
        "WindSpeed3pm": afternoon.get("wind_speed_10m"),
        "Humidity9am": morning.get("relative_humidity_2m"),
        "Humidity3pm": afternoon.get("relative_humidity_2m"),
        "Pressure9am": morning.get("pressure_msl"),
        "Pressure3pm": afternoon.get("pressure_msl"),
        "Cloud9am": _cloud_percent_to_oktas(morning.get("cloud_cover")),
        "Cloud3pm": _cloud_percent_to_oktas(afternoon.get("cloud_cover")),
        "Temp9am": morning.get("temperature_2m"),
        "Temp3pm": afternoon.get("temperature_2m"),
        "RainToday": _rain_label(rainfall),
        "RainTomorrow": _rain_label(next_day_rainfall),
    }


def _next_date(value: str) -> str:
    return (date.fromisoformat(value) + timedelta(days=1)).isoformat()


def _daily_record(daily: dict[str, Any], target_date: str) -> dict[str, Any]:
    times = daily.get("time", [])
    if target_date not in times:
        return {}

    index = times.index(target_date)
    return {
        variable: values[index]
        for variable, values in daily.items()
        if variable != "time" and isinstance(values, list) and index < len(values)
    }


def _hourly_record(hourly: dict[str, Any], target_date: str, hour: int) -> dict[str, Any]:
    target_time = f"{target_date}T{hour:02d}:00"
    times = hourly.get("time", [])
    if target_time not in times:
        return {}

    index = times.index(target_time)
    return {
        variable: values[index]
        for variable, values in hourly.items()
        if variable != "time" and isinstance(values, list) and index < len(values)
    }


def _daily_rainfall_mm(payload: dict[str, Any]) -> float | None:
    value = payload.get("rain_sum")
    if value is None or pd.isna(value):
        value = payload.get("precipitation_sum")
    if value is None or pd.isna(value):
        return None
    return float(value)


def _seconds_to_hours(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value) / 3600, 2)


def _cloud_percent_to_oktas(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value) / 12.5)


def _rain_label(rainfall_mm: float | None) -> str | None:
    if rainfall_mm is None or pd.isna(rainfall_mm):
        return None
    return "Yes" if rainfall_mm >= RAIN_THRESHOLD_MM else "No"


def _wind_direction(degrees: Any) -> str | None:
    if degrees is None or pd.isna(degrees):
        return None

    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    index = int((float(degrees) + 11.25) / 22.5) % 16
    return directions[index]
