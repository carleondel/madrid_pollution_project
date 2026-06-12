from datetime import date

import httpx
import pytest
import respx

from madrid_pollution.data.weather import OPEN_METEO_ARCHIVE_URL, fetch_historical_weather


@respx.mock
def test_fetch_historical_weather_normalizes_hourly_response() -> None:
    respx.get(OPEN_METEO_ARCHIVE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "latitude": 40.4,
                "longitude": -3.7,
                "hourly": {
                    "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                    "temperature_2m": [8.0, 7.5],
                    "relative_humidity_2m": [80, 82],
                    "precipitation": [0.0, 0.0],
                    "pressure_msl": [1020.0, 1020.5],
                    "wind_speed_10m": [4.0, 3.5],
                    "wind_direction_10m": [270, 265],
                },
            },
        )
    )

    with httpx.Client() as client:
        result = fetch_historical_weather(client, date(2024, 1, 1), date(2024, 1, 1))

    assert len(result) == 2
    assert str(result["observed_at"].dt.tz) == "UTC"
    assert result["source"].unique().tolist() == ["open-meteo-historical"]


def test_fetch_historical_weather_rejects_reversed_dates() -> None:
    with httpx.Client() as client, pytest.raises(ValueError, match="end_date"):
        fetch_historical_weather(client, date(2024, 1, 2), date(2024, 1, 1))
