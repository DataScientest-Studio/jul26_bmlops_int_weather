from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from weather_mlops.models.predict import predict
from weather_mlops.models.training import train_model

app = FastAPI(
    title="Australian Weather MLOps API",
    description="Predict whether it will rain tomorrow in Australia.",
    version="0.1.0",
)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    Location: str
    MinTemp: float | None = None
    MaxTemp: float | None = None
    Rainfall: float | None = None
    Evaporation: float | None = None
    Sunshine: float | None = None
    WindGustDir: str | None = None
    WindGustSpeed: float | None = None
    WindDir9am: str | None = None
    WindDir3pm: str | None = None
    WindSpeed9am: float | None = None
    WindSpeed3pm: float | None = None
    Humidity9am: float | None = None
    Humidity3pm: float | None = None
    Pressure9am: float | None = None
    Pressure3pm: float | None = None
    Cloud9am: float | None = None
    Cloud3pm: float | None = None
    Temp9am: float | None = None
    Temp3pm: float | None = None
    RainToday: str | None = None


class PredictionResponse(BaseModel):
    rain_tomorrow: bool
    probability: float


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def prediction_endpoint(
    request: PredictionRequest,
) -> dict[str, Any]:
    try:
        return predict(
            request.model_dump(
                exclude_none=False,
            )
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@app.post("/training")
def training_endpoint() -> dict[str, Any]:
    _, metrics = train_model()

    return {
        "status": "completed",
        "metrics": metrics,
    }
