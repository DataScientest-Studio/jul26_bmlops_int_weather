import pandas as pd
import pytest

from weather_mlops.data.preprocess import clean_dataframe, temporal_train_validation_test_split


def weather_frame_for_dates(
    start: str,
    *,
    days: int,
    locations: list[str] | None = None,
) -> pd.DataFrame:
    rows = []
    for day in pd.date_range(start, periods=days):
        for location in locations or ["Sydney"]:
            rows.append(
                {
                    "Date": day,
                    "Location": location,
                    "MinTemp": 12.0,
                    "RainTomorrow": "Yes",
                }
            )
    return pd.DataFrame(rows)


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


def test_clean_dataframe_preserves_an_already_cleaned_target() -> None:
    dataframe = pd.DataFrame(
        {
            "Date": ["2020-01-01", "2020-01-02"],
            "Location": ["Sydney", "Sydney"],
            "RainTomorrow": ["Yes", "No"],
        }
    )

    cleaned = clean_dataframe(dataframe)

    assert clean_dataframe(cleaned)["RainTomorrow"].tolist() == [1, 0]


def test_temporal_train_validation_test_split_writes_feature_and_label_sets() -> None:
    dataframe = weather_frame_for_dates(
        "2020-01-01",
        days=270,
    )

    X_train, X_validation, X_test, y_train, y_validation, y_test = (
        temporal_train_validation_test_split(
            dataframe,
            training_window_days=90,
            validation_window_days=90,
            test_window_days=90,
        )
    )

    assert len(X_train) == 90
    assert len(X_validation) == 90
    assert len(X_test) == 90
    assert "Date" not in X_train.columns
    assert "RainTomorrow" not in X_train.columns
    assert y_train.name == "RainTomorrow"
    assert y_validation.name == "RainTomorrow"
    assert y_test.name == "RainTomorrow"


def test_temporal_split_keeps_whole_calendar_days_together() -> None:
    dataframe = weather_frame_for_dates(
        "2020-01-01",
        days=270,
        locations=["Sydney", "Melbourne"],
    )

    X_train, X_validation, X_test, _y_train, _y_validation, _y_test = (
        temporal_train_validation_test_split(
            dataframe,
            training_window_days=90,
            validation_window_days=90,
            test_window_days=90,
        )
    )

    assert len(X_train) == 180
    assert len(X_validation) == 180
    assert len(X_test) == 180
    assert set(X_train["Location"]) == {"Sydney", "Melbourne"}


def test_rolling_split_keeps_each_date_in_exactly_one_partition() -> None:
    frame = weather_frame_for_dates(
        "2025-01-01",
        days=400,
        locations=["Sydney", "Perth"],
    )

    X_train, X_validation, X_test, *_ = temporal_train_validation_test_split(
        frame,
        training_window_days=180,
        validation_window_days=90,
        test_window_days=90,
    )

    assert set(X_train.index).isdisjoint(X_validation.index)
    assert set(X_validation.index).isdisjoint(X_test.index)
    assert len(X_train) == 180 * 2
    assert len(X_validation) == 90 * 2
    assert len(X_test) == 90 * 2


def test_rolling_split_rejects_insufficient_unique_dates() -> None:
    with pytest.raises(ValueError, match="270 distinct dates"):
        temporal_train_validation_test_split(
            weather_frame_for_dates("2025-01-01", days=269),
            training_window_days=90,
            validation_window_days=90,
            test_window_days=90,
        )
