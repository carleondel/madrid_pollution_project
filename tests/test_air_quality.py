import zipfile
from pathlib import Path

import pandas as pd
import pytest

from madrid_pollution.data.air_quality import (
    air_quality_url,
    iter_csv_payloads,
    normalize_air_quality_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_air_quality_filters_pollutant_and_invalid_hours() -> None:
    payload = (FIXTURES / "air_quality_sample.csv").read_bytes()

    result = normalize_air_quality_csv(payload, source_file="sample.csv")

    assert len(result) == 23
    assert result["station_id"].unique().tolist() == ["28079004"]
    assert result["no2_ug_m3"].min() == 9
    assert result["observed_at"].dt.tz is not None
    assert result["observed_at"].is_unique


def test_iter_csv_payloads_ignores_zip_folders_and_other_formats(tmp_path: Path) -> None:
    archive_path = tmp_path / "annual.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/month.csv", b"a;b\n1;2\n")
        archive.writestr("nested/month.xml", b"<root />")

    members = list(iter_csv_payloads(archive_path))

    assert members == [("nested/month.csv", b"a;b\n1;2\n")]


def test_normalize_air_quality_rejects_missing_schema() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        normalize_air_quality_csv(b"ANO;MES\n2018;1\n", source_file="broken.csv")


def test_air_quality_url_rejects_unsupported_year() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        air_quality_url(2017)


def test_dst_nonexistent_hour_is_not_emitted() -> None:
    payload = (FIXTURES / "air_quality_sample.csv").read_text()
    payload = payload.replace(";2018;01;01;", ";2018;03;25;").replace(";29;N;", ";29;V;")

    result = normalize_air_quality_csv(payload.encode(), source_file="dst.csv")

    assert len(result) == 23
    assert result["observed_at"].is_unique
    assert result["observed_at"].min() == pd.Timestamp("2018-03-24 23:00:00+00:00")
