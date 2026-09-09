#!/bin/sh
set -e

echo "[trainer] preprocessing"
python -m weather_mlops.data.preprocess

echo "[trainer] training"
python -m weather_mlops.models.training

echo "[trainer] validation"
python -m weather_mlops.models.evaluation \
    --x-data data/processed/X_validation.csv \
    --y-data data/processed/y_validation.csv \
    --model-path models/rain_classifier.joblib \
    --metrics-output reports/metrics/validation.json \
    --split-name validation

echo "[trainer] comparing models"
python -m weather_mlops.models.comparison

echo "[trainer] evaluating"
python -m weather_mlops.models.evaluation \
    --x-data data/processed/X_test.csv \
    --y-data data/processed/y_test.csv \
    --model-path models/rain_classifier.joblib \
    --metrics-output reports/metrics/evaluation.json \
    --split-name test