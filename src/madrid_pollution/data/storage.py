"""Parquet and PostgreSQL persistence for normalized raw datasets."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

metadata = MetaData(schema="raw")

air_quality_table = Table(
    "air_quality",
    metadata,
    Column("station_id", String(16), primary_key=True),
    Column("observed_at", DateTime(timezone=True), primary_key=True),
    Column("no2_ug_m3", Float, nullable=False),
    Column("validity", String(1), nullable=False),
    Column("source_file", String(255), nullable=False),
    Column("source_year", Integer, nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
)

stations_table = Table(
    "stations",
    metadata,
    Column("station_id", String(16), primary_key=True),
    Column("station_code", Integer),
    Column("station_name", String(255), nullable=False),
    Column("address", String(500)),
    Column("station_type_code", String(16)),
    Column("station_type", String(100)),
    Column("altitude_m", Float),
    Column("longitude", Float),
    Column("latitude", Float),
    Column("opened_on", Date),
    Column("measures_no2", Boolean, nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
)

weather_table = Table(
    "weather",
    metadata,
    Column("observed_at", DateTime(timezone=True), primary_key=True),
    Column("temperature_2m", Float),
    Column("relative_humidity_2m", Float),
    Column("precipitation", Float),
    Column("pressure_msl", Float),
    Column("wind_speed_10m", Float),
    Column("wind_direction_10m", Float),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    Column("source", String(100), nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
)


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine with connection health checks."""

    return create_engine(database_url, pool_pre_ping=True)


def initialize_database(engine: Engine) -> None:
    """Create raw and downstream schemas plus normalized raw tables."""

    with engine.begin() as connection:
        connection.execute(text("create schema if not exists raw"))
        connection.execute(text("create schema if not exists analytics"))
        connection.execute(text("create schema if not exists ml"))
    metadata.create_all(engine)


def write_parquet(frame: pd.DataFrame, destination: Path) -> Path:
    """Write a deterministic Parquet artifact atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    frame.to_parquet(temporary, index=False)
    temporary.replace(destination)
    return destination


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def upsert_dataframe(
    engine: Engine,
    table: Table,
    frame: pd.DataFrame,
    *,
    key_columns: Sequence[str],
    chunk_size: int = 5_000,
) -> int:
    """Upsert a DataFrame into PostgreSQL and return the submitted row count."""

    if frame.empty:
        return 0
    table_columns = {column.name for column in table.columns}
    missing = set(table_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"Frame for {table.fullname} is missing columns: {sorted(missing)}")

    update_columns = table_columns.difference(key_columns)
    records = _records(frame[list(table_columns)])
    with engine.begin() as connection:
        for offset in range(0, len(records), chunk_size):
            statement = insert(table).values(records[offset : offset + chunk_size])
            statement = statement.on_conflict_do_update(
                index_elements=list(key_columns),
                set_={column: getattr(statement.excluded, column) for column in update_columns},
            )
            connection.execute(statement)
    return len(records)
