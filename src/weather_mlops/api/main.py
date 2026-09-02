from fastapi import FastAPI
from pydantic import BaseModel
from weather_mlops.models.predict import predict, load_model
from weather_mlops.models.training import train_model

def convert(x):
    x = x.split('_')

    # Capitalize each word after the first and join them back together
    res = ''.join(word.capitalize() for word in x[0:])
    return(res)

class PredictionInput(BaseModel):
    location: str
    min_temp: float
    max_temp: float
    rainfall: float
    evaporation: float
    sunshine: float
    wind_gust_dir: str
    wind_gust_speed: float
    wind_dir_9am: str
    wind_dir_3pm: str
    wind_speed_9am: float
    wind_speed_3pm: float
    humidity_9am: float
    humidity_3pm: float
    pressure_9am: float
    pressure_3pm: float
    cloud_9am: float
    cloud_3pm: float
    temp_9am: float
    temp_3pm: float
    rain_today: str


api = FastAPI()

@api.post("/predict")
def predict_endpoint(features: PredictionInput):
    raw_dict = features.model_dump()
    converted_dict ={convert(key): value for key, value in raw_dict.items()}
    return predict(converted_dict)


class TrainInput(BaseModel):
    n_estimators: int
    max_depth: int
    learning_rate: float
    subsample: float
    colsample_bytree: float

@api.post("/train")
def train_endpoint(features: TrainInput):
    pipeline, metrics = train_model(**features.model_dump())
    load_model.cache_clear()
    return metrics