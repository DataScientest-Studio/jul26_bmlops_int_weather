#!/bin/sh
set -e

# two days ago, because RainTomorrow needs the next day to be observed
OBSERVATION_DATE=$(date -u -d "2 days ago" +%Y-%m-%d)

echo "[ingestion] fetching Open-Meteo data for $OBSERVATION_DATE"
python scripts/fetch_open_meteo_daily.py --date "$OBSERVATION_DATE"

echo "[ingestion] merging the seed file with the incremental snapshots"
python -m weather_mlops.data.merge_raw
