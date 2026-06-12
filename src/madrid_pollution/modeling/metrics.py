"""Forecast metrics with stable handling of zero-valued observations."""

from __future__ import annotations

import numpy as np


def regression_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    mase_scale: float,
) -> dict[str, float]:
    """Return MAE, RMSE, MASE, and symmetric MAPE."""

    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    if actual_values.shape != predicted_values.shape:
        raise ValueError("actual and predicted must have the same shape")
    if actual_values.size == 0:
        raise ValueError("metrics require at least one observation")

    errors = actual_values - predicted_values
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    denominator = np.abs(actual_values) + np.abs(predicted_values)
    smape_terms = np.divide(
        2 * np.abs(errors),
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )
    mase = float(mae / mase_scale) if mase_scale > 0 else float("nan")
    return {
        "mae": mae,
        "rmse": rmse,
        "mase": mase,
        "smape": float(np.mean(smape_terms) * 100),
    }
