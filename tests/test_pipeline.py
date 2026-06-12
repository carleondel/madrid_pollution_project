from pathlib import Path

import pandas as pd

from madrid_pollution.config import Settings
from madrid_pollution.pipeline import ingest_air_quality


def test_ingest_air_quality_keeps_only_requested_year(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        raw_data_dir=tmp_path / "data" / "raw",
        processed_data_dir=tmp_path / "data" / "processed",
        artifacts_dir=tmp_path / "artifacts",
        reports_dir=tmp_path / "reports",
    )
    source = pd.DataFrame(
        {
            "station_id": ["a", "a"],
            "observed_at": pd.to_datetime(["2025-01-01", "2026-01-01"], utc=True),
            "no2_ug_m3": [10.0, 20.0],
            "validity": ["V", "V"],
            "source_file": ["current.csv", "current.csv"],
            "source_year": pd.Series([2025, 2026], dtype="Int64"),
            "ingested_at": pd.to_datetime(["2026-01-01", "2026-01-01"], utc=True),
        }
    )

    monkeypatch.setattr(
        "madrid_pollution.pipeline.download_air_quality_year",
        lambda *args, **kwargs: tmp_path / "current.csv",
    )
    monkeypatch.setattr(
        "madrid_pollution.pipeline.parse_air_quality_resource", lambda path: source.copy()
    )

    result = ingest_air_quality(settings, [2025], load_database=False)

    assert result["source_year"].tolist() == [2025]
    persisted = pd.read_parquet(
        settings.processed_data_dir / "air_quality" / "year=2025" / "data.parquet"
    )
    assert persisted["source_year"].tolist() == [2025]
