# Singapore data vs WeatherAUS

We need a rainy place to test drift. We took Singapore from Open-Meteo,
2014-01-01 to 2024-12-30, 4,007 days.

## Can we use it with our model?

Yes. The file has the same 23 columns as `data/raw/weatherAUS.csv`, in the
same order. `scripts/score_drift.py` scores it with our model without errors.

## What is different

| | Australia | Singapore |
| --- | --- | --- |
| Rain tomorrow | 21.9% of days | 82.6% of days |
| MinTemp (mean) | 12.2 | 24.6 |
| Humidity3pm (mean) | 51.5 | 75.5 |
| Pressure3pm (mean) | 1015.3 | 1008.5 |
| Missing values | many | none |
| Locations | 49 | 1 (Singapore) |

So the data drifts a lot, this is what we want to show.

## How to get it

```
uv run dvc pull data/raw/open_meteo_Singapore.dvc
uv run dvc repro merge_singapore
```

The merged file is `data/raw/weatherSingapore_current.csv`.
