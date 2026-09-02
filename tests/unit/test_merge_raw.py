import pandas as pd

from weather_mlops.data.merge_raw import merge_raw_datasets
from weather_mlops.data.weatheraus_schema import WEATHERAUS_COLUMNS


def _weatheraus_row(**overrides) -> dict[str, object]:
    row = dict.fromkeys(WEATHERAUS_COLUMNS, pd.NA)
    row.update(
        {
            "Date": "2020-01-01",
            "Location": "Newcastle",
            "MinTemp": 10.0,
            "MaxTemp": 20.0,
            "Rainfall": 0.0,
            "RainToday": "No",
            "RainTomorrow": "No",
        }
    )
    row.update(overrides)
    return row


def test_merge_raw_datasets_appends_incremental_rows(tmp_path) -> None:
    seed_path = tmp_path / "weatherAUS.csv"
    incremental_dir = tmp_path / "incremental"
    output_path = tmp_path / "weatherAUS_current.csv"
    incremental_dir.mkdir()

    pd.DataFrame([_weatheraus_row()]).to_csv(seed_path, index=False)

    pd.DataFrame(
        [
            _weatheraus_row(
                Date="2020-01-02",
                MinTemp=11.0,
                MaxTemp=21.0,
                Rainfall=3.0,
                RainToday="Yes",
            )
        ]
    ).to_csv(incremental_dir / "open_meteo_20200102.csv", index=False)

    result = merge_raw_datasets(seed_path, incremental_dir, output_path)

    assert output_path.exists()
    assert result["Date"].tolist() == ["2020-01-01", "2020-01-02"]
    assert result["Location"].tolist() == ["Newcastle", "Newcastle"]
    assert result["Rainfall"].tolist() == [0.0, 3.0]


def test_merge_raw_datasets_replaces_duplicate_date_location_with_incremental(tmp_path) -> None:
    seed_path = tmp_path / "weatherAUS.csv"
    incremental_dir = tmp_path / "incremental"
    output_path = tmp_path / "weatherAUS_current.csv"
    incremental_dir.mkdir()

    pd.DataFrame([_weatheraus_row()]).to_csv(seed_path, index=False)

    pd.DataFrame(
        [
            _weatheraus_row(
                MinTemp=12.0,
                MaxTemp=22.0,
                Rainfall=5.0,
                RainToday="Yes",
            )
        ]
    ).to_csv(incremental_dir / "open_meteo_20200101.csv", index=False)

    result = merge_raw_datasets(seed_path, incremental_dir, output_path)

    assert len(result) == 1
    assert result.loc[0, "MinTemp"] == 12.0
    assert result.loc[0, "Rainfall"] == 5.0
