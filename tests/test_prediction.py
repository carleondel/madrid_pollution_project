import pandas as pd

from madrid_pollution.modeling.prediction import select_latest_fresh_features


def test_select_latest_fresh_features_excludes_stale_stations() -> None:
    features = pd.DataFrame(
        {
            "station_id": ["active", "active", "stale"],
            "prediction_created_at": pd.to_datetime(
                ["2025-12-31T21:00Z", "2025-12-31T22:00Z", "2025-09-01T00:00Z"]
            ),
        }
    )

    result = select_latest_fresh_features(features, max_staleness_hours=48)

    assert result["station_id"].tolist() == ["active"]
    assert result["prediction_created_at"].iloc[0] == pd.Timestamp("2025-12-31T22:00Z")
