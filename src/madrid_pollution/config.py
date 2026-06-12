"""Application settings and project paths."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local `.env`."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = (
        "postgresql+psycopg://madrid_user:madrid_pass@localhost:5432/madrid_pollution"
    )
    log_level: str = Field(default="INFO", alias="MADRID_POLLUTION_LOG_LEVEL")
    data_start_year: int = Field(default=2018, alias="MADRID_POLLUTION_DATA_START_YEAR")
    data_end_year: int = Field(default=2025, alias="MADRID_POLLUTION_DATA_END_YEAR")

    data_dir: Path = PROJECT_ROOT / "data"
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    reports_dir: Path = PROJECT_ROOT / "reports"

    def ensure_directories(self) -> None:
        """Create local runtime directories that are intentionally not tracked."""

        for directory in (
            self.data_dir,
            self.raw_data_dir,
            self.processed_data_dir,
            self.artifacts_dir,
            self.reports_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
