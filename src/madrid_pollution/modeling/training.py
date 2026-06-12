"""Global direct-horizon XGBoost training and rolling-origin evaluation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from madrid_pollution.modeling.backtest import rolling_origin_folds
from madrid_pollution.modeling.features import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    build_feature_frame,
    build_hourly_panel,
    load_processed_inputs,
)
from madrid_pollution.modeling.metrics import regression_metrics


def build_model(*, n_estimators: int = 200, random_state: int = 42) -> Pipeline:
    """Build the deterministic preprocessing and XGBoost pipeline."""

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    estimator = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=n_estimators,
        learning_rate=0.05,
        max_depth=6,
        min_child_weight=3,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        random_state=random_state,
        n_jobs=4,
        tree_method="hist",
    )
    return Pipeline([("preprocessing", preprocessing), ("model", estimator)])


def _evaluate_model(
    validation: pd.DataFrame,
    predictions: np.ndarray,
    *,
    mase_scales: pd.Series,
    model_name: str,
    horizon_hours: int,
    fold: int,
) -> list[dict[str, object]]:
    evaluated = validation.assign(_prediction=predictions)
    overall_scale = float(mase_scales.mean())

    def metric_row(group: pd.DataFrame, station_id: str | None) -> dict[str, object]:
        scale = float(mase_scales.get(station_id, overall_scale)) if station_id else overall_scale
        metrics = regression_metrics(
            group["target_no2_ug_m3"].to_numpy(),
            group["_prediction"].to_numpy(),
            mase_scale=scale,
        )
        return {
            "scope": "station" if station_id else "overall",
            "station_id": station_id,
            "model": model_name,
            "horizon_hours": horizon_hours,
            "fold": fold,
            "validation_start": group["prediction_created_at"].min().isoformat(),
            "validation_end": group["prediction_created_at"].max().isoformat(),
            "rows": len(group),
            **metrics,
        }

    rows = [metric_row(evaluated, None)]
    rows.extend(
        metric_row(group, str(station_id))
        for station_id, group in evaluated.groupby("station_id", sort=True)
    )
    return rows


def train_horizon(
    feature_frame: pd.DataFrame,
    *,
    horizon_hours: int,
    n_splits: int,
    validation_hours: int,
    min_training_hours: int,
    max_training_hours: int | None,
    n_estimators: int,
) -> tuple[Pipeline, list[dict[str, object]], pd.DataFrame]:
    """Backtest and fit a final direct model for one horizon."""

    folds = rolling_origin_folds(
        feature_frame,
        n_splits=n_splits,
        validation_hours=validation_hours,
        min_training_hours=min_training_hours,
        max_training_hours=max_training_hours,
    )
    metric_rows: list[dict[str, object]] = []
    last_predictions = pd.DataFrame()

    for fold in folds:
        train = feature_frame.loc[fold.train_mask]
        validation = feature_frame.loc[fold.validation_mask].copy()
        mase_scales = (
            train.assign(_seasonal_error=np.abs(train["target_no2_ug_m3"] - train["baseline_168h"]))
            .groupby("station_id")["_seasonal_error"]
            .mean()
        )
        for period in (24, 168):
            metric_rows.extend(
                _evaluate_model(
                    validation,
                    validation[f"baseline_{period}h"].to_numpy(),
                    mase_scales=mase_scales,
                    model_name=f"seasonal_naive_{period}h",
                    horizon_hours=horizon_hours,
                    fold=fold.fold,
                )
            )

        model = build_model(n_estimators=n_estimators)
        model.fit(train[MODEL_FEATURES], train["target_no2_ug_m3"])
        predictions = model.predict(validation[MODEL_FEATURES])
        metric_rows.extend(
            _evaluate_model(
                validation,
                predictions,
                mase_scales=mase_scales,
                model_name="xgboost",
                horizon_hours=horizon_hours,
                fold=fold.fold,
            )
        )
        validation["predicted_no2_ug_m3"] = predictions
        validation["fold"] = fold.fold
        last_predictions = validation[
            [
                "station_id",
                "prediction_created_at",
                "target_at",
                "target_no2_ug_m3",
                "baseline_24h",
                "baseline_168h",
                "predicted_no2_ug_m3",
                "fold",
            ]
        ]

    final_model = build_model(n_estimators=n_estimators)
    final_model.fit(feature_frame[MODEL_FEATURES], feature_frame["target_no2_ug_m3"])
    return final_model, metric_rows, last_predictions


def train_all_horizons(
    processed_data_dir: Path,
    artifacts_dir: Path,
    reports_dir: Path,
    *,
    horizons: tuple[int, ...] = (1, 24, 72),
    n_splits: int = 3,
    validation_days: int = 14,
    min_training_days: int = 180,
    max_training_days: int | None = 730,
    n_estimators: int = 200,
) -> pd.DataFrame:
    """Train all direct horizons and persist versioned models and metrics."""

    observations, stations = load_processed_inputs(processed_data_dir)
    panel = build_hourly_panel(observations, stations)
    model_version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model_dir = artifacts_dir / "models" / model_version
    model_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_metrics: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    for horizon in horizons:
        feature_frame = build_feature_frame(panel, horizon)
        model, metrics, predictions = train_horizon(
            feature_frame,
            horizon_hours=horizon,
            n_splits=n_splits,
            validation_hours=validation_days * 24,
            min_training_hours=min_training_days * 24,
            max_training_hours=max_training_days * 24 if max_training_days else None,
            n_estimators=n_estimators,
        )
        metadata = {
            "model_version": model_version,
            "horizon_hours": horizon,
            "trained_at": datetime.now(UTC).isoformat(),
            "training_start": feature_frame["prediction_created_at"].min().isoformat(),
            "training_end": feature_frame["prediction_created_at"].max().isoformat(),
            "training_rows": len(feature_frame),
            "features": MODEL_FEATURES,
        }
        joblib.dump({"model": model, "metadata": metadata}, model_dir / f"horizon_{horizon}.joblib")
        (model_dir / f"horizon_{horizon}.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        predictions["horizon_hours"] = horizon
        predictions["model_version"] = model_version
        prediction_frames.append(predictions)
        all_metrics.extend(metrics)

    metrics_frame = pd.DataFrame(all_metrics)
    metrics_frame.to_csv(reports_dir / "backtest_metrics.csv", index=False)
    (reports_dir / "backtest_metrics.json").write_text(
        metrics_frame.to_json(orient="records", indent=2), encoding="utf-8"
    )
    pd.concat(prediction_frames, ignore_index=True).to_parquet(
        reports_dir / "backtest_predictions.parquet", index=False
    )
    (artifacts_dir / "models" / "LATEST").write_text(model_version, encoding="utf-8")
    return metrics_frame
