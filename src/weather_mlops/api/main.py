from functools import lru_cache
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator, Field, field_validator
from weather_mlops.models.predict import predict, load_model
from weather_mlops.models.training import train_model
from weather_mlops.config.settings import settings
import difflib


WindDirection = Literal["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

def convert(x):
    """
    Convert a snake_case feature name to a PascalCase.
    
    The API accepts snake_case field names (Python convention), but the trained pipeline expects the original 
    PascalCase column names from the source CSV (e.g. "MinTemp"). This function translates between the two.
    """

    x = x.split('_')
    res = ''.join(word.capitalize() for word in x[0:])
    return(res)

@lru_cache(maxsize=1)
def get_locations():
    pipeline = load_model()
    preprocessor = pipeline.named_steps["preprocessor"]
    categorical_pipeline = preprocessor.named_transformers_["categorical"]
    categorical_encoder = categorical_pipeline.named_steps["encoder"]

    for name, _, columns in preprocessor.transformers_:
        if name == "categorical":
            location_index = columns.index("Location")
            return list(categorical_encoder.categories_[location_index])

    return []

class PredictionInput(BaseModel):
    location: str
    min_temp: float | None =  Field(default = None, ge = -20, le = 40)
    max_temp: float | None = Field(default = None, ge = -10, le = 60)
    rainfall: float | None = Field(default = None, ge= 0, le = 500)
    evaporation: float | None = Field(default = None, ge= 0, le = 250)
    sunshine: float | None = Field(default = None, ge= 0, le = 18)
    wind_gust_dir: WindDirection | None = None
    wind_gust_speed: float | None = Field(default=None, ge=0, le=200)
    wind_dir_9am: WindDirection | None = None
    wind_dir_3pm: WindDirection | None = None
    wind_speed_9am: float | None = Field(default=None, ge=0, le=200)
    wind_speed_3pm: float | None = Field(default=None, ge=0, le=200)
    humidity_9am: float | None = Field(default = None, ge= 0, le = 100)
    humidity_3pm: float | None = Field(default = None, ge= 0, le = 100)
    pressure_9am: float | None = Field(default=None, ge=950, le=1070)
    pressure_3pm: float | None = Field(default=None, ge=950, le=1070)
    cloud_9am: float | None = Field(default = None, ge= 0, le = 9)
    cloud_3pm: float | None = Field(default = None, ge= 0, le = 9)
    temp_9am: float | None = Field(default=None, ge=-20, le=60)
    temp_3pm: float | None = Field(default=None, ge=-20, le=60)
    rain_today: Literal["Yes", "No"] | None = None

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        try:
            for known_location in get_locations():
                if value.lower() == known_location.lower():
                    return known_location
            hint = difflib.get_close_matches(value, get_locations(), n=1, cutoff=0.6)
            suggestion = f" Did you mean '{hint[0]}'?" if hint else ""
            raise ValueError(f"Unknown location: '{value}'.{suggestion}")
        except FileNotFoundError:
            return value

    @model_validator(mode="after")
    def check_minimum_values(self):
        """
        Checks if at least the location and three additional weather values are provided

        There are 20 different features which can be provided (location + 19 weather conditions).
        Weather stations could lack some weather values due to problems. We need at least four values (location + 3 weather values)
        to predict if it's going to rain tomorrow
        
        """
        dict_values = self.model_dump()
        count_filled = sum(1 for value in dict_values.values() if value is not None)
        if count_filled < 4:
            raise ValueError("At least location and 3 weather values must be provided")
        return self


class TrainInput(BaseModel):
    n_estimators: int = Field(default = 250, gt = 0)
    max_depth: int = Field(default = 4, gt = 0, le = 15)
    learning_rate: float = Field(default = 0.05, gt = 0, le = 1)
    subsample: float = Field(default = 0.9, gt = 0, le = 1)
    colsample_bytree: float = Field(default = 0.9, gt = 0, le = 1)

class PredictionOutput(BaseModel):
    rain_tomorrow: bool
    probability: float

class TrainOutput(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float



app = FastAPI()

@app.get("/health")
def health_check():
    """
    Report whether the API is running and whether a trained model is available.

    This is used mostly by orchestration tools to verify the service is ready before routing traffic to it.
    A missing model means /predict will fail until /train has been called
    """
    if settings.model_path.exists():
        model_status = "A pretrained model is already loaded"
    else:
        model_status = "There is no pretrained model loaded"
    
    return {
        "status": "This API is running",
        "model_status": model_status
    }

@app.post("/predict", response_model = PredictionOutput)
def predict_endpoint(features: PredictionInput):
    """
    Predict whether it will rain tomorrow at the given location.

    Returns a boolean prediction and its probability, based on the location
    and whatever weather features were provided.
    """
    raw_dict = features.model_dump()
    converted_dict ={convert(key): value for key, value in raw_dict.items()}
    try:
        return predict(converted_dict)
    except FileNotFoundError as e:
        raise HTTPException(status_code = 404, detail = f"Required model not found: {e}.")



@app.post("/train", response_model = TrainOutput)
def train_endpoint(features: TrainInput):
    """
    Train a new rainfall classifier and return its evaluation metrics.

    Retrains the model on the current training data using the given
    hyperparameters, saves it to disk, and clears the prediction cache so
    /predict uses the newly trained model on the next call.
    """
    try:
        pipeline, metrics = train_model(**features.model_dump())
        load_model.cache_clear()
        get_locations.cache_clear()
        return metrics
    except FileNotFoundError as e:
        raise HTTPException(status_code = 404, detail = f"Required file not found: {e}")