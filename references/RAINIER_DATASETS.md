# Rainier-region datasets for drift simulation

Assigned in the Sep 25, 2026 meeting to Gabriel Marchesan Almeida ("Find Rainy
Data"). Goal — a second dataset with the same schema as WeatherAUS but a much
higher rainy-day ratio than the Australian ~24%, so the production XGBoost
model degrades measurably when run on it (the drift-simulation demo).

WeatherAUS schema we need to match (20 features + target):

| WeatherAUS column | Notes |
| --- | --- |
| Date, Location | identifier |
| MinTemp, MaxTemp | °C |
| Rainfall | mm that day |
| Evaporation, Sunshine | mm / hours |
| WindGustDir, WindGustSpeed | categorical / km h⁻¹ |
| WindDir9am, WindDir3pm, WindSpeed9am, WindSpeed3pm | categorical / km h⁻¹ |
| Humidity9am, Humidity3pm | % |
| Pressure9am, Pressure3pm | hPa |
| Cloud9am, Cloud3pm | oktas |
| Temp9am, Temp3pm | °C |
| RainToday | Yes/No (1 if precipitation ≥ 1 mm) |
| RainTomorrow | target — Yes/No |

## Candidate paths

We need a region where it rains far more often than Australia. Rainy-day
fractions of ≥ 1 mm/d, 2014–2024 (Open-Meteo ERA5 Historical, verified
2026-09-28 against `archive-api.open-meteo.com/v1/archive`):

| Location | Lat / Lon | % rainy days (2014–24) |
| --- | --- | --- |
| **Singapore** | 1.35 / 103.82 | **82.0%** |
| Kuala Lumpur | 3.14 / 101.69 | 79.9% |
| Hilo, Hawaii | 19.73 / -155.09 | 73.7% |
| Jakarta | -6.21 / 106.85 | 72.0% |
| Kochi, India | 9.93 / 76.27 | 68.4% |
| Darwin, AU | -12.46 / 130.85 | 40.6% |
| Mumbai | 19.08 / 72.88 | 35.4% |
| Hobart, AU | -42.88 / 147.33 | 31.2% |
| Brisbane, AU | -27.47 / 153.03 | 31.0% |
| Honolulu, Hawaii | 21.31 / -157.86 | 27.9% |
| Australia (WeatherAUS) | mixed | **24.0%** |

For comparison: published studies report Singapore ≈ 51% rain days from
station networks (Mandapaka & Qin 2013, doi:10.1175/JHM-D-15-0100.1). Our
82% number uses the ERA5 ≥ 1 mm threshold over 10 years — same column as
WeatherAUS `RainToday`.

## Recommended approach: Open-Meteo Historical Weather API

Open-Meteo `/v1/archive` (ERA5 reanalysis, 0.25°, 1940-present, no key,
CC-BY 4.0) returns every WeatherAUS column as a derived daily aggregate:

| WeatherAUS column | Open-Meteo daily variable |
| --- | --- |
| MinTemp / MaxTemp | `temperature_2m_min` / `temperature_2m_max` |
| Rainfall | `precipitation_sum` |
| Sunshine | `sunshine_duration` (seconds → h) |
| WindGustSpeed | `wind_gusts_10m_max` |
| WindDir9am / WindDir3pm | not available in daily aggregate — derive from hourly `wind_direction_10m` at 09:00/15:00 local, or drop and rely on `wind_direction_10m_dominant` |
| WindSpeed9am / WindSpeed3pm | same — derive from hourly, or substitute `wind_speed_10m_max` |
| Humidity9am / Humidity3pm | derive from hourly `relative_humidity_2m`, or substitute `relative_humidity_2m_max` / `..._min` |
| Pressure9am / Pressure3pm | `pressure_msl_max` / `pressure_msl_min` (no 9am/3pm split in daily aggregate) |
| Cloud9am / Cloud3pm | not available in daily aggregate — derive from hourly `cloud_cover`, or substitute `cloud_cover_max` / `..._min` if we add it |
| Temp9am / Temp3pm | derive from hourly `temperature_2m`, or use min/max already covered |
| RainToday | derived from `precipitation_sum >= 1.0` |
| RainTomorrow | derived from `precipitation_sum.shift(-1) >= 1.0` |

**Two viable routes:**

1. **Pure daily aggregate, ERA5** — 10 daily variables. Feeds ~16 of the 20
   features; the model retrained on it has fewer signals but a clean,
   reproducible pipeline (one HTTP request per city per year). Fast to ship.

2. **ERA5 hourly, aggregated locally** — fetches `temperature_2m`,
   `relative_humidity_2m`, `pressure_msl`, `wind_speed_10m`,
   `wind_direction_10m`, `cloud_cover`, `precipitation` for each hour, then
   picks 09:00 / 15:00 local values. Recreates the WeatherAUS schema exactly
   but at the cost of a 360-row / 1-block HTTP request per city per year.

Both routes keep `make data-open-meteo-sg` (or similar) as a sibling of the
existing `make data-open-meteo` job and write the result into the same
`data/raw/open_meteo_<location>_<year>.csv` shape that the existing
`merge_raw.py` already understands.

## Other datasets we did NOT pick

- **Meteostat bulk CSV** (meteostat.net) — global daily station data since
  1973, includes `temp_min/max`, `precipitation`, `wind`, `pressure`,
  `sunshine`, `humidity`, `cloud_cover`, but only the daily aggregates (no
  9am/3pm split). Viable fallback if Open-Meteo is unavailable. License:
  CC-BY 4.0.
- **NOAA GHCN-Daily** — 100k+ stations, free, but US-centric and the same
  daily-only limitation. Adds bureaucratic CSV header work. Not needed.
- **Kaggle "Rainfall in India" / "Indian Rainfall and Weather Prediction
  Dataset"** — clean but very feature-thin (only temperature + precipitation
  + pressure + wind speed). Doesn't match WeatherAUS schema well; would
  require a much heavier normalisation layer. Skip.
- **Kaggle "Simple Rainfall Classification Dataset" / Kaggle Playground S5E3
  Rainfall** — small, generic, no location/date dimension. Wrong shape for
  our drift-by-region demo.
- **UK Met Office MIDAS Open** — daily-only, plus login-walled.
  Reproducible but UK rain-day ratios are similar to Australia (~25%), so
  doesn't help the "rainier region" demo. Skip.

## What to commit next

1. `references/rainier_locations.csv` — coordinates + city names for the 5
   rainier candidates (already a copy of the table above as CSV-ready rows).
2. `scripts/fetch_open_meteo_rainier.py` — daily-aggregate fetcher, writes
   `data/raw/open_meteo_<city>_<year>.csv` in WeatherAUS schema.
3. A small `scripts/drift_demo.py` — loads the production model, scores the
   rainier region CSV, prints ROC-AUC + recall vs the Australian test set so
   the Evidently drift report has a concrete number to anchor on.

Reviewed 2026-09-28 against Open-Meteo docs (`open-meteo.com/en/docs/historical-weather-api`)
and ERA5 reanalysis coverage.
