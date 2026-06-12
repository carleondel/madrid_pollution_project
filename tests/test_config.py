from pathlib import Path

from madrid_pollution.config import PROJECT_ROOT, Settings


def test_project_root_contains_pyproject() -> None:
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_settings_build_expected_runtime_paths(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        raw_data_dir=tmp_path / "data" / "raw",
        processed_data_dir=tmp_path / "data" / "processed",
        artifacts_dir=tmp_path / "artifacts",
        reports_dir=tmp_path / "reports",
    )

    settings.ensure_directories()

    assert settings.raw_data_dir.is_dir()
    assert settings.processed_data_dir.is_dir()
    assert settings.artifacts_dir.is_dir()
    assert settings.reports_dir.is_dir()
