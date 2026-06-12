"""Historical Madrid weather ingestion from Open-Meteo."""

from datetime import UTC, date, datetime

import httpx
import pandas as pd

from madrid_pollution.data.http import get_json

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
MADRID_LATITUDE = 40.4168
MADRID_LONGITUDE = -3.7038
WEATHER_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
]
WEATHER_COLUMNS = [
    "observed_at",
    *WEATHER_VARIABLES,
    "latitude",
    "longitude",
    "source",
    "ingested_at",
]


def fetch_historical_weather(
    client: httpx.Client,
    start_date: date,
    end_date: date,
    *,
    latitude: float = MADRID_LATITUDE,
    longitude: float = MADRID_LONGITUDE,
) -> pd.DataFrame:
    """Fetch an hourly historical weather series in UTC."""

    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")
    payload = get_json(
        client,
        OPEN_METEO_ARCHIVE_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "hourly": ",".join(WEATHER_VARIABLES),
            "timezone": "UTC",
        },
    )
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or "time" not in hourly:
        raise ValueError("Open-Meteo response does not contain hourly time-series data")

    frame = pd.DataFrame(hourly)
    missing = set(WEATHER_VARIABLES).difference(frame.columns)
    if missing:
        raise ValueError(f"Open-Meteo response is missing variables: {sorted(missing)}")
    frame["observed_at"] = pd.to_datetime(frame.pop("time"), utc=True, errors="coerce")
    for column in WEATHER_VARIABLES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["latitude"] = float(payload.get("latitude", latitude))
    frame["longitude"] = float(payload.get("longitude", longitude))
    frame["source"] = "open-meteo-historical"
    frame["ingested_at"] = datetime.now(UTC)
    return frame[WEATHER_COLUMNS].dropna(subset=["observed_at"]).drop_duplicates("observed_at")
