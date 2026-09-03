import difflib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator, Field
from weather_mlops.models.predict import predict, load_model
from weather_mlops.models.training import train_model
from weather_mlops.config.settings import settings

def convert(x):
    x = x.split('_')

    # Capitalize each word after the first and join them back together
    res = ''.join(word.capitalize() for word in x[0:])
    return(res)

def known_locations() -> list[str]:
    """Locations the trained model was actually fitted on."""
    preprocessor = load_model().named_steps["preprocessor"]
    for name, transformer, columns in preprocessor.transformers_:
        if name == "categorical":
            encoder = transformer.named_steps["encoder"]
            return list(encoder.categories_[columns.index("Location")])
    return []


class PredictionInput(BaseModel):
    location: str
    min_temp: float | None = None
    max_temp: float | None = None
    rainfall: float | None = None
    evaporation: float | None = None
    sunshine: float | None = None
    wind_gust_dir: str | None = None
    wind_gust_speed: float | None = None
    wind_dir_9am: str | None = None
    wind_dir_3pm: str | None = None
    wind_speed_9am: float | None = None
    wind_speed_3pm: float | None = None
    humidity_9am: float | None = None
    humidity_3pm: float | None = None
    pressure_9am: float | None = None
    pressure_3pm: float | None = None
    cloud_9am: float | None = None
    cloud_3pm: float | None = None
    temp_9am: float | None = None
    temp_3pm: float | None = None
    rain_today: str | None = None

    @model_validator(mode="after")
    def check_location_is_known(self):
        known = known_locations()
        if known and self.location not in known:
            hint = difflib.get_close_matches(self.location, known, n=1, cutoff=0.6)
            suggestion = f" Did you mean '{hint[0]}'?" if hint else ""
            raise ValueError(f"Unknown location '{self.location}'.{suggestion}")
        return self

    @model_validator(mode="after")
    def check_minimum_values(self):
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


app = FastAPI()

@app.get("/health")
def health_check():
    if settings.model_path.exists():
        model_status = "A pretrained model is already loaded"
    else:
        model_status = "There is no pretrained model loaded"
    
    return {
        "status": "This API is running",
        "model_status": model_status
    }

@app.post("/predict")
def predict_endpoint(features: PredictionInput):
    raw_dict = features.model_dump()
    converted_dict ={convert(key): value for key, value in raw_dict.items()}
    try:
        return predict(converted_dict)
    except FileNotFoundError as e:
        raise HTTPException(status_code = 404, detail = f"Required model not found: {e}. Please train a model before you try to predict if it is going to rain")


@app.post("/train")
def train_endpoint(features: TrainInput):
    try:
        pipeline, metrics = train_model(**features.model_dump())
        load_model.cache_clear()
        return metrics
    except FileNotFoundError as e:
        raise HTTPException(status_code = 404, detail = f"Required file not found: {e}")