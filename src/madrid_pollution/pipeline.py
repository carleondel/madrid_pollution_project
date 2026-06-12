"""End-to-end ingestion orchestration used by the CLI and future schedulers."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from madrid_pollution.config import Settings
from madrid_pollution.data.air_quality import (
    download_air_quality_year,
    parse_air_quality_resource,
)
from madrid_pollution.data.http import managed_client
from madrid_pollution.data.stations import download_stations, parse_stations
from madrid_pollution.data.storage import (
    air_quality_table,
    create_database_engine,
    initialize_database,
    stations_table,
    upsert_dataframe,
    weather_table,
    write_parquet,
)
from madrid_pollution.data.weather import fetch_historical_weather

LOGGER = logging.getLogger(__name__)


def ingest_air_quality(
    settings: Settings,
    years: list[int],
    *,
    load_database: bool,
    force: bool = False,
) -> pd.DataFrame:
    """Download, normalize, cache, and optionally load annual NO2 observations."""

    frames: list[pd.DataFrame] = []
    with managed_client() as client:
        for year in years:
            LOGGER.info("Ingesting official Madrid NO2 observations for %s", year)
            resource = download_air_quality_year(client, year, settings.raw_data_dir, force=force)
            frame = parse_air_quality_resource(resource)
            write_parquet(
                frame,
                settings.processed_data_dir / "air_quality" / f"year={year}" / "data.parquet",
            )
            frames.append(frame)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if load_database:
        engine = create_database_engine(settings.database_url)
        initialize_database(engine)
        upsert_dataframe(
            engine,
            air_quality_table,
            combined,
            key_columns=["station_id", "observed_at"],
        )
    return combined


def ingest_stations(
    settings: Settings,
    *,
    load_database: bool,
    force: bool = False,
) -> pd.DataFrame:
    """Download, normalize, cache, and optionally load station metadata."""

    with managed_client() as client:
        resource = download_stations(client, settings.raw_data_dir, force=force)
    frame = parse_stations(resource)
    write_parquet(frame, settings.processed_data_dir / "stations.parquet")
    if load_database:
        engine = create_database_engine(settings.database_url)
        initialize_database(engine)
        upsert_dataframe(engine, stations_table, frame, key_columns=["station_id"])
    return frame


def ingest_weather(
    settings: Settings,
    start_date: date,
    end_date: date,
    *,
    load_database: bool,
) -> pd.DataFrame:
    """Fetch, cache, and optionally load central Madrid historical weather."""

    with managed_client() as client:
        frame = fetch_historical_weather(client, start_date, end_date)
    destination = (
        settings.processed_data_dir
        / "weather"
        / (f"weather_{start_date.isoformat()}_{end_date.isoformat()}.parquet")
    )
    write_parquet(frame, destination)
    if load_database:
        engine = create_database_engine(settings.database_url)
        initialize_database(engine)
        upsert_dataframe(engine, weather_table, frame, key_columns=["observed_at"])
    return frame


def processed_path(settings: Settings, *parts: str) -> Path:
    """Return a path below the processed data directory."""

    return settings.processed_data_dir.joinpath(*parts)
