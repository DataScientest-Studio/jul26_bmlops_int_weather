import pandas as pd

from weather_mlops.data.outcomes import reconcile_prediction_outcomes


class FakeQuery:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.filters: list[tuple[str, str, object]] = []

    def update(self, payload: dict):
        self.updates.append(payload)
        return self

    def eq(self, field: str, value: object):
        self.filters.append(("eq", field, value))
        return self

    def is_(self, field: str, value: object):
        self.filters.append(("is", field, value))
        return self

    def execute(self):
        return self


class FakeClient:
    def __init__(self) -> None:
        self.query = FakeQuery()

    def table(self, _name: str) -> FakeQuery:
        return self.query


def test_reconcile_updates_only_mature_unlabelled_predictions() -> None:
    client = FakeClient()
    rows = pd.DataFrame({"Date": ["2025-03-02"], "Location": ["Sydney"], "RainTomorrow": ["Yes"]})

    count = reconcile_prediction_outcomes(rows, client)

    assert count == 1
    assert client.query.updates == [{"observed_label": "Yes"}]
    assert ("is", "observed_label", "null") in client.query.filters


def test_reconcile_ignores_rows_without_a_valid_next_day_label() -> None:
    client = FakeClient()
    rows = pd.DataFrame({"Date": ["2025-03-01"], "Location": ["Sydney"], "RainTomorrow": [None]})

    assert reconcile_prediction_outcomes(rows, client) == 0
    assert client.query.updates == []
