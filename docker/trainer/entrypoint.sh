#!/bin/sh
set -e

echo "[trainer] preprocessing"
python -m weather_mlops.data.preprocess

echo "[trainer] training"
python -m weather_mlops.models.training

echo "[trainer] evaluating"
python -m weather_mlops.models.evaluation
