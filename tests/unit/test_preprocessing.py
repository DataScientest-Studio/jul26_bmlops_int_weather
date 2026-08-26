import pandas as pd

from weather_mlops.data.preprocessing import clean_dataframe


def test_clean_dataframe_maps_target() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": ["2020-01-01", "2020-01-02"],
            "Location": ["Sydney", "Sydney"],
            "RainTomorrow": ["Yes", "No"],
        }
    )

    result = clean_dataframe(dataframe)

    assert result["RainTomorrow"].tolist() == [1, 0]
