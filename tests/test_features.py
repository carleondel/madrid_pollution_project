import numpy as np
import pandas as pd

from madrid_pollution.modeling.features import build_feature_frame, build_hourly_panel


def _sample_inputs(hours: int = 500) -> tuple[pd.DataFrame, pd.DataFrame]:
    timestamps = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    observations = pd.DataFrame(
        {
            "station_id": "28079004",
            "observed_at": timestamps,
            "no2_ug_m3": np.arange(hours, dtype=float),
        }
    )
    stations = pd.DataFrame(
        {
            "station_id": ["28079004"],
            "station_type": ["Urbana tráfico"],
            "altitude_m": [637.0],
            "longitude": [-3.71],
            "latitude": [40.42],
        }
    )
    return observations, stations


def test_hourly_panel_reindexes_missing_hours() -> None:
    observations, stations = _sample_inputs(10)
    observations = observations.drop(index=4)

    panel = build_hourly_panel(observations, stations)

    assert len(panel) == 10
    assert panel.loc[4, "no2_ug_m3"] != panel.loc[4, "no2_ug_m3"]


def test_feature_values_use_only_past_observations() -> None:
    observations, stations = _sample_inputs()
    panel = build_hourly_panel(observations, stations)

    features = build_feature_frame(panel, horizon_hours=24)
    row = features.iloc[0]
    source = panel.set_index("prediction_created_at")["no2_ug_m3"]
    prediction_time = row["prediction_created_at"]

    assert row["no2_lag_1h"] == source.loc[prediction_time - pd.Timedelta(hours=1)]
    assert (
        row["no2_roll_mean_3h"]
        == source.loc[
            prediction_time - pd.Timedelta(hours=3) : prediction_time - pd.Timedelta(hours=1)
        ].mean()
    )
    assert row["target_no2_ug_m3"] == source.loc[prediction_time + pd.Timedelta(hours=24)]
    assert row["baseline_24h"] == source.loc[prediction_time]
    assert row["prediction_created_at"] < row["target_at"]


def test_prediction_features_do_not_require_future_target() -> None:
    observations, stations = _sample_inputs(300)
    panel = build_hourly_panel(observations, stations)

    features = build_feature_frame(panel, horizon_hours=72, include_target=False)

    assert "target_no2_ug_m3" not in features
    assert features["prediction_created_at"].max() == panel["prediction_created_at"].max()
