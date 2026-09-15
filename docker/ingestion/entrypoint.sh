#!/bin/sh
set -e

if [ -n "$OPEN_METEO_DATE" ]; then
  OBSERVATION_DATE="$OPEN_METEO_DATE"
else
  # two days ago, because RainTomorrow needs the next day to be observed
  OBSERVATION_DATE=$(date -u -d "2 days ago" +%Y-%m-%d)
fi

echo "[ingestion] fetching Open-Meteo data for $OBSERVATION_DATE"
python scripts/fetch_open_meteo_daily.py --date "$OBSERVATION_DATE"

echo "[ingestion] merging the seed file with the incremental snapshots"
python -m weather_mlops.data.merge_raw
