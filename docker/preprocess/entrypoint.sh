#!/bin/sh
set -e

# this job only prepares the data. training is done by the api, not here.
echo "[preprocess] building the train/validation/test splits"
python -m weather_mlops.data.preprocess
