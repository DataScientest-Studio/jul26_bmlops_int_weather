import pandas as pd

from weather_mlops.data.preprocess import clean_dataframe, temporal_train_validation_test_split


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


def test_temporal_train_validation_test_split_writes_feature_and_label_sets() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": pd.date_range("2020-01-01", periods=10),
            "Location": ["Sydney"] * 10,
            "MinTemp": range(10),
            "RainTomorrow": ["Yes", "No"] * 5,
        }
    )

    X_train, X_validation, X_test, y_train, y_validation, y_test = (
        temporal_train_validation_test_split(
            dataframe,
            train_fraction=0.6,
            validation_fraction=0.2,
        )
    )

    assert len(X_train) == 6
    assert len(X_validation) == 2
    assert len(X_test) == 2
    assert "Date" not in X_train.columns
    assert "RainTomorrow" not in X_train.columns
    assert y_train.name == "RainTomorrow"
    assert y_validation.name == "RainTomorrow"
    assert y_test.name == "RainTomorrow"
