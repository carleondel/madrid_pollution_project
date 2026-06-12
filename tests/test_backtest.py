import pandas as pd

from madrid_pollution.modeling.backtest import rolling_origin_folds


def test_rolling_origin_embargoes_training_targets() -> None:
    prediction_times = pd.date_range("2024-01-01", periods=1_000, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "prediction_created_at": prediction_times,
            "target_at": prediction_times + pd.Timedelta(hours=72),
        }
    )

    folds = rolling_origin_folds(
        frame,
        n_splits=2,
        validation_hours=100,
        min_training_hours=500,
    )

    assert len(folds) == 2
    for fold in folds:
        assert frame.loc[fold.train_mask, "target_at"].max() < fold.validation_start
        validation_start = frame.loc[fold.validation_mask, "prediction_created_at"].min()
        assert validation_start == fold.validation_start
