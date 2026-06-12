"""Rolling-origin split generation with a target-availability embargo."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestFold:
    """Boolean row masks and boundaries for one rolling-origin fold."""

    fold: int
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    train_mask: pd.Series
    validation_mask: pd.Series


def rolling_origin_folds(
    frame: pd.DataFrame,
    *,
    n_splits: int,
    validation_hours: int,
    min_training_hours: int,
    max_training_hours: int | None = None,
) -> list[BacktestFold]:
    """Create trailing validation windows while embargoing overlapping targets."""

    if n_splits <= 0 or validation_hours <= 0 or min_training_hours <= 0:
        raise ValueError("split counts and window sizes must be positive")
    times = pd.DatetimeIndex(frame["prediction_created_at"].drop_duplicates().sort_values())
    required = min_training_hours + n_splits * validation_hours
    if len(times) < required:
        raise ValueError(f"Need at least {required} unique hours for the requested backtest")

    folds: list[BacktestFold] = []
    first_validation_index = len(times) - n_splits * validation_hours
    for fold_number in range(n_splits):
        start_index = first_validation_index + fold_number * validation_hours
        end_index = start_index + validation_hours
        validation_start = times[start_index]
        validation_end = times[end_index - 1] + pd.Timedelta(hours=1)

        train_mask = frame["target_at"].lt(validation_start)
        if max_training_hours is not None:
            training_start = validation_start - pd.Timedelta(hours=max_training_hours)
            train_mask &= frame["prediction_created_at"].ge(training_start)
        validation_mask = frame["prediction_created_at"].ge(validation_start) & frame[
            "prediction_created_at"
        ].lt(validation_end)
        if not train_mask.any() or not validation_mask.any():
            raise ValueError(f"Fold {fold_number + 1} contains no train or validation rows")
        folds.append(
            BacktestFold(
                fold=fold_number + 1,
                validation_start=validation_start,
                validation_end=validation_end,
                train_mask=train_mask,
                validation_mask=validation_mask,
            )
        )
    return folds
