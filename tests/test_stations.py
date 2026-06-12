from pathlib import Path

import pytest

from madrid_pollution.data.stations import parse_stations

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_stations_normalizes_metadata() -> None:
    result = parse_stations(FIXTURES / "stations_sample.csv")

    row = result.iloc[0]
    assert row["station_id"] == "28079004"
    assert row["station_code"] == 4
    assert row["measures_no2"]
    assert row["longitude"] == pytest.approx(-3.7122567)
    assert row["latitude"] == pytest.approx(40.4238823)
