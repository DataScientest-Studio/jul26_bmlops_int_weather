import pandas as pd

from weather_mlops.data.database import dataframe_to_records


def test_dataframe_to_records_normalizes_weather_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": ["2020-01-01"],
            "Location": ["Sydney"],
            "MinTemp": [12.0],
            "MaxTemp": [23.0],
            "Rainfall": [0.0],
            "Evaporation": [None],
            "Sunshine": [8.0],
            "WindGustDir": ["W"],
            "WindGustSpeed": [31.0],
            "WindDir9am": ["N"],
            "WindDir3pm": ["W"],
            "WindSpeed9am": [10.0],
            "WindSpeed3pm": [13.0],
            "Humidity9am": [71.0],
            "Humidity3pm": [42.0],
            "Pressure9am": [1012.0],
            "Pressure3pm": [1009.0],
            "Cloud9am": [2.0],
            "Cloud3pm": [3.0],
            "Temp9am": [17.0],
            "Temp3pm": [21.0],
            "RainToday": ["No"],
            "RainTomorrow": ["Yes"],
        }
    )

    records = dataframe_to_records(dataframe)

    assert records[0]["source_row_number"] == 1
    assert records[0]["date"] == "2020-01-01"
    assert records[0]["min_temp"] == 12.0
    assert records[0]["evaporation"] is None
    assert records[0]["rain_tomorrow"] == "Yes"
