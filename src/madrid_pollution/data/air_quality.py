"""Madrid Open Data NO2 extraction and normalization."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from madrid_pollution.data.http import get_bytes

NO2_MAGNITUDE_CODE = 8
MADRID_TIMEZONE = "Europe/Madrid"
AIR_QUALITY_URLS = {
    year: f"https://datos.madrid.es/egob/catalogo/201200-{catalog_id}-calidad-aire-horario.zip"
    for year, catalog_id in {
        2018: 10306314,
        2019: 10306315,
        2020: 10306316,
        2021: 10306317,
        2022: 10306318,
        2023: 10306319,
        2024: 10306320,
    }.items()
}
AIR_QUALITY_URLS[2025] = (
    "https://datos.madrid.es/egob/catalogo/201200-10306322-calidad-aire-horario.csv"
)

BASE_COLUMNS = [
    "PROVINCIA",
    "MUNICIPIO",
    "ESTACION",
    "MAGNITUD",
    "PUNTO_MUESTREO",
    "ANO",
    "MES",
    "DIA",
]
OUTPUT_COLUMNS = [
    "station_id",
    "observed_at",
    "no2_ug_m3",
    "validity",
    "source_file",
    "source_year",
    "ingested_at",
]


def air_quality_url(year: int) -> str:
    """Return the official download URL for a supported year."""

    try:
        return AIR_QUALITY_URLS[year]
    except KeyError as exc:
        supported = f"{min(AIR_QUALITY_URLS)}-{max(AIR_QUALITY_URLS)}"
        message = f"Unsupported air-quality year {year}; supported range: {supported}"
        raise ValueError(message) from exc


def download_air_quality_year(
    client: httpx.Client,
    year: int,
    cache_dir: Path,
    *,
    force: bool = False,
) -> Path:
    """Download one official annual resource into the raw cache."""

    url = air_quality_url(year)
    suffix = ".zip" if url.endswith(".zip") else ".csv"
    destination = cache_dir / "madrid_open_data" / f"air_quality_{year}{suffix}"
    if destination.exists() and not force:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = get_bytes(client, url)
    if not payload:
        raise ValueError(f"Empty response for Madrid air-quality year {year}")
    destination.write_bytes(payload)
    return destination


def iter_csv_payloads(path: Path) -> Iterator[tuple[str, bytes]]:
    """Yield CSV members from either an annual CSV or an arbitrarily nested ZIP."""

    if path.suffix.lower() == ".csv":
        yield path.name, path.read_bytes()
        return

    if path.suffix.lower() != ".zip":
        raise ValueError(f"Unsupported Madrid air-quality resource: {path}")

    with zipfile.ZipFile(path) as archive:
        members = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
        if not members:
            raise ValueError(f"No CSV files found in {path}")
        for member in members:
            yield member, archive.read(member)


def _read_source_csv(payload: bytes) -> pd.DataFrame:
    frame = pd.read_csv(
        io.BytesIO(payload),
        sep=";",
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    )
    frame.columns = frame.columns.str.strip().str.upper()
    missing = set(BASE_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Madrid air-quality CSV is missing columns: {sorted(missing)}")
    return frame


def normalize_air_quality_csv(
    payload: bytes,
    *,
    source_file: str,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    """Convert the official wide hourly format into valid station-hour NO2 rows."""

    source = _read_source_csv(payload)
    source["MAGNITUD"] = pd.to_numeric(source["MAGNITUD"], errors="coerce")
    source = source.loc[source["MAGNITUD"].eq(NO2_MAGNITUDE_CODE)].copy()
    if source.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    hourly_frames: list[pd.DataFrame] = []
    for hour_number in range(1, 25):
        value_column = f"H{hour_number:02d}"
        validity_column = f"V{hour_number:02d}"
        if value_column not in source or validity_column not in source:
            raise ValueError(f"Missing hourly columns {value_column}/{validity_column}")
        hourly = source[BASE_COLUMNS].copy()
        hourly["hour"] = hour_number - 1
        hourly["no2_ug_m3"] = pd.to_numeric(source[value_column], errors="coerce")
        hourly["validity"] = source[validity_column].str.strip().str.upper()
        hourly_frames.append(hourly)

    normalized = pd.concat(hourly_frames, ignore_index=True)
    normalized = normalized.loc[
        normalized["validity"].eq("V") & normalized["no2_ug_m3"].notna()
    ].copy()

    local_naive = pd.to_datetime(
        {
            "year": pd.to_numeric(normalized["ANO"], errors="coerce"),
            "month": pd.to_numeric(normalized["MES"], errors="coerce"),
            "day": pd.to_numeric(normalized["DIA"], errors="coerce"),
            "hour": normalized["hour"],
        },
        errors="coerce",
    )
    local_time = local_naive.dt.tz_localize(
        MADRID_TIMEZONE,
        ambiguous=False,
        nonexistent="NaT",
    )
    normalized["observed_at"] = local_time.dt.tz_convert("UTC")
    normalized["station_id"] = normalized["PUNTO_MUESTREO"].str.split("_").str[0]
    normalized["source_file"] = source_file
    normalized["source_year"] = pd.to_numeric(normalized["ANO"], errors="coerce").astype("Int64")
    normalized["ingested_at"] = ingested_at or datetime.now(UTC)

    normalized = normalized.dropna(subset=["station_id", "observed_at", "source_year"])
    normalized = normalized.loc[normalized["no2_ug_m3"].ge(0)]
    normalized = normalized[OUTPUT_COLUMNS]
    return normalized.drop_duplicates(["station_id", "observed_at"], keep="last").reset_index(
        drop=True
    )


def parse_air_quality_resource(path: Path) -> pd.DataFrame:
    """Parse and combine all CSV files in one cached annual resource."""

    ingested_at = datetime.now(UTC)
    frames = [
        normalize_air_quality_csv(payload, source_file=name, ingested_at=ingested_at)
        for name, payload in iter_csv_payloads(path)
    ]
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    combined = pd.concat(non_empty, ignore_index=True)
    return combined.drop_duplicates(["station_id", "observed_at"], keep="last").sort_values(
        ["observed_at", "station_id"]
    )
