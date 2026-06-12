"""Generate the latest station forecasts from persisted direct-horizon models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from madrid_pollution.modeling.features import (
    MODEL_FEATURES,
    build_feature_frame,
    build_hourly_panel,
    load_processed_inputs,
)


def select_latest_fresh_features(
    features: pd.DataFrame,
    *,
    max_staleness_hours: int,
) -> pd.DataFrame:
    """Select each station's latest row when it is close to global freshness."""

    latest = features.sort_values("prediction_created_at").groupby("station_id").tail(1).copy()
    freshness_cutoff = features["prediction_created_at"].max() - pd.Timedelta(
        hours=max_staleness_hours
    )
    return latest.loc[latest["prediction_created_at"].ge(freshness_cutoff)].copy()


def predict_latest(
    processed_data_dir: Path,
    artifacts_dir: Path,
    reports_dir: Path,
    *,
    horizons: tuple[int, ...] = (1, 24, 72),
    max_staleness_hours: int = 14 * 24,
) -> pd.DataFrame:
    """Predict each station from its latest complete feature row."""

    latest_file = artifacts_dir / "models" / "LATEST"
    if not latest_file.exists():
        raise FileNotFoundError("No trained model version found; run the training command first")
    model_version = latest_file.read_text(encoding="utf-8").strip()
    observations, stations = load_processed_inputs(processed_data_dir)
    panel = build_hourly_panel(observations, stations)

    forecast_frames: list[pd.DataFrame] = []
    generated_at = datetime.now(UTC)
    for horizon in horizons:
        bundle = joblib.load(artifacts_dir / "models" / model_version / f"horizon_{horizon}.joblib")
        features = build_feature_frame(panel, horizon, include_target=False)
        latest = select_latest_fresh_features(
            features,
            max_staleness_hours=max_staleness_hours,
        )
        latest["predicted_no2_ug_m3"] = bundle["model"].predict(latest[MODEL_FEATURES])
        latest["horizon_hours"] = horizon
        latest["model_version"] = model_version
        latest["generated_at"] = generated_at
        forecast_frames.append(
            latest[
                [
                    "station_id",
                    "prediction_created_at",
                    "target_at",
                    "horizon_hours",
                    "predicted_no2_ug_m3",
                    "model_version",
                    "generated_at",
                ]
            ]
        )

    forecasts = pd.concat(forecast_frames, ignore_index=True).sort_values(
        ["station_id", "horizon_hours"]
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    forecasts.to_parquet(reports_dir / "latest_predictions.parquet", index=False)
    forecasts.to_csv(reports_dir / "latest_predictions.csv", index=False)
    return forecasts.reset_index(drop=True)
