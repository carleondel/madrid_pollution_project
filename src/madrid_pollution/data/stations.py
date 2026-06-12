"""Madrid air-quality station catalogue ingestion."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from madrid_pollution.data.http import get_bytes

STATIONS_URL = "https://datos.madrid.es/egob/catalogo/212629-1-estaciones-control-aire.csv"

STATION_COLUMNS = [
    "station_id",
    "station_code",
    "station_name",
    "address",
    "station_type_code",
    "station_type",
    "altitude_m",
    "longitude",
    "latitude",
    "opened_on",
    "measures_no2",
    "ingested_at",
]


def download_stations(
    client: httpx.Client,
    cache_dir: Path,
    *,
    force: bool = False,
) -> Path:
    """Download the official station catalogue."""

    destination = cache_dir / "madrid_open_data" / "stations.csv"
    if destination.exists() and not force:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(get_bytes(client, STATIONS_URL))
    return destination


def parse_stations(path: Path, *, ingested_at: datetime | None = None) -> pd.DataFrame:
    """Normalize the official station catalogue."""

    source = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    source.columns = source.columns.str.strip().str.upper()
    required = {
        "CODIGO",
        "CODIGO_CORTO",
        "ESTACION",
        "DIRECCION",
        "COD_TIPO",
        "NOM_TIPO",
        "ALTITUD",
        "LONGITUD",
        "LATITUD",
        "FECHA ALTA",
        "NO2",
    }
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"Madrid stations CSV is missing columns: {sorted(missing)}")

    normalized = pd.DataFrame(
        {
            "station_id": source["CODIGO"].str.strip(),
            "station_code": pd.to_numeric(source["CODIGO_CORTO"], errors="coerce").astype("Int64"),
            "station_name": source["ESTACION"].str.strip(),
            "address": source["DIRECCION"].str.strip(),
            "station_type_code": source["COD_TIPO"].str.strip(),
            "station_type": source["NOM_TIPO"].str.strip(),
            "altitude_m": pd.to_numeric(source["ALTITUD"], errors="coerce"),
            "longitude": pd.to_numeric(
                source["LONGITUD"].str.replace(",", ".", regex=False), errors="coerce"
            ),
            "latitude": pd.to_numeric(
                source["LATITUD"].str.replace(",", ".", regex=False), errors="coerce"
            ),
            "opened_on": pd.to_datetime(source["FECHA ALTA"], dayfirst=True, errors="coerce"),
            "measures_no2": source["NO2"].fillna("").str.strip().str.upper().eq("X"),
            "ingested_at": ingested_at or datetime.now(UTC),
        }
    )
    normalized = normalized.dropna(subset=["station_id", "station_name"])
    return (
        normalized[STATION_COLUMNS]
        .drop_duplicates("station_id", keep="last")
        .reset_index(drop=True)
    )
