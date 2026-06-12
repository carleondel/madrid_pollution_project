"""Station-level hourly feature engineering with explicit time availability."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

MADRID_TIMEZONE = "Europe/Madrid"
LAG_HOURS = (1, 2, 3, 24, 48, 72, 168)
ROLLING_WINDOWS = (3, 24, 168)

NUMERIC_FEATURES = [
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "is_weekend",
    "altitude_m",
    "station_longitude",
    "station_latitude",
    *[f"no2_lag_{lag}h" for lag in LAG_HOURS],
    *[f"no2_roll_mean_{window}h" for window in ROLLING_WINDOWS],
    *[f"no2_roll_std_{window}h" for window in ROLLING_WINDOWS],
]
CATEGORICAL_FEATURES = ["station_id", "station_type"]
MODEL_FEATURES = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]


def load_processed_inputs(processed_data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load normalized observations and stations from partitioned Parquet files."""

    observation_paths = sorted((processed_data_dir / "air_quality").glob("year=*/data.parquet"))
    if not observation_paths:
        raise FileNotFoundError(
            f"No air-quality Parquet partitions found below {processed_data_dir / 'air_quality'}"
        )
    station_path = processed_data_dir / "stations.parquet"
    if not station_path.exists():
        raise FileNotFoundError(f"Station metadata not found at {station_path}")

    observations = pd.concat(
        [pd.read_parquet(path) for path in observation_paths],
        ignore_index=True,
    )
    stations = pd.read_parquet(station_path)
    return observations, stations


def build_hourly_panel(observations: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Create a complete hourly UTC index between each station's first and last reading."""

    required_observation_columns = {"station_id", "observed_at", "no2_ug_m3"}
    missing = required_observation_columns.difference(observations.columns)
    if missing:
        raise ValueError(f"Observations are missing columns: {sorted(missing)}")

    source = observations[list(required_observation_columns)].copy()
    source["observed_at"] = pd.to_datetime(source["observed_at"], utc=True, errors="coerce")
    source["no2_ug_m3"] = pd.to_numeric(source["no2_ug_m3"], errors="coerce")
    source = source.dropna(subset=["station_id", "observed_at", "no2_ug_m3"])

    station_frames: list[pd.DataFrame] = []
    for station_id, group in source.groupby("station_id", sort=True):
        series = group.groupby("observed_at")["no2_ug_m3"].mean().sort_index()
        full_index = pd.date_range(series.index.min(), series.index.max(), freq="h", tz="UTC")
        station_frame = series.reindex(full_index).rename("no2_ug_m3").to_frame()
        station_frame.index.name = "prediction_created_at"
        station_frame["station_id"] = str(station_id)
        station_frames.append(station_frame.reset_index())

    if not station_frames:
        raise ValueError("No valid station observations were provided")

    panel = pd.concat(station_frames, ignore_index=True)
    station_columns = [
        "station_id",
        "station_type",
        "altitude_m",
        "longitude",
        "latitude",
    ]
    metadata = stations.copy()
    for column in station_columns:
        if column not in metadata:
            metadata[column] = np.nan
    metadata = metadata[station_columns].drop_duplicates("station_id", keep="last")
    metadata["station_id"] = metadata["station_id"].astype(str)
    metadata = metadata.rename(
        columns={"longitude": "station_longitude", "latitude": "station_latitude"}
    )
    panel = panel.merge(metadata, on="station_id", how="left", validate="many_to_one")
    panel["station_type"] = panel["station_type"].fillna("unknown").astype(str)
    return panel.sort_values(["station_id", "prediction_created_at"]).reset_index(drop=True)


def _seasonal_baseline_offset(horizon_hours: int, period_hours: int) -> int:
    cycles = math.ceil(horizon_hours / period_hours)
    return cycles * period_hours - horizon_hours


def build_feature_frame(
    panel: pd.DataFrame,
    horizon_hours: int,
    *,
    include_target: bool = True,
) -> pd.DataFrame:
    """Create features available at prediction time and an optional direct target."""

    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be positive")
    frame = panel.sort_values(["station_id", "prediction_created_at"]).copy()
    frame["prediction_created_at"] = pd.to_datetime(
        frame["prediction_created_at"], utc=True, errors="coerce"
    )
    grouped = frame.groupby("station_id", sort=False)["no2_ug_m3"]

    local_time = frame["prediction_created_at"].dt.tz_convert(MADRID_TIMEZONE)
    hour = local_time.dt.hour
    day_of_week = local_time.dt.dayofweek
    day_of_year = local_time.dt.dayofyear
    frame["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    frame["day_of_week_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    frame["day_of_week_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    frame["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    frame["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    frame["is_weekend"] = day_of_week.ge(5).astype(int)

    for lag in LAG_HOURS:
        frame[f"no2_lag_{lag}h"] = grouped.shift(lag)
    for window in ROLLING_WINDOWS:
        frame[f"no2_roll_mean_{window}h"] = grouped.transform(
            lambda values, size=window: values.shift(1).rolling(size, min_periods=size).mean()
        )
        frame[f"no2_roll_std_{window}h"] = grouped.transform(
            lambda values, size=window: values.shift(1).rolling(size, min_periods=size).std()
        )

    frame["target_at"] = frame["prediction_created_at"] + pd.Timedelta(hours=horizon_hours)
    if include_target:
        frame["target_no2_ug_m3"] = grouped.shift(-horizon_hours)

    for period in (24, 168):
        offset = _seasonal_baseline_offset(horizon_hours, period)
        baseline_column = f"baseline_{period}h"
        frame[baseline_column] = frame["no2_ug_m3"] if offset == 0 else grouped.shift(offset)

    required = [*MODEL_FEATURES, "baseline_24h", "baseline_168h"]
    if include_target:
        required.append("target_no2_ug_m3")
    frame = frame.dropna(subset=required)
    return frame.reset_index(drop=True)
