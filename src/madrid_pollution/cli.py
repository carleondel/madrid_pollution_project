"""Command-line entry point for the pipeline."""

import argparse
import json
from collections.abc import Sequence
from datetime import date

from madrid_pollution import __version__
from madrid_pollution.config import get_settings
from madrid_pollution.logging import configure_logging
from madrid_pollution.modeling.prediction import predict_latest
from madrid_pollution.modeling.training import train_all_horizons
from madrid_pollution.pipeline import ingest_air_quality, ingest_stations, ingest_weather
from madrid_pollution.reporting import generate_report_assets


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(prog="madrid-pollution")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show resolved local project configuration")

    air_parser = subparsers.add_parser("ingest-air-quality", help="Ingest official Madrid NO2")
    air_parser.add_argument("--years", nargs="+", type=int)
    air_parser.add_argument("--no-database", action="store_true")
    air_parser.add_argument("--force", action="store_true")

    stations_parser = subparsers.add_parser("ingest-stations", help="Ingest station metadata")
    stations_parser.add_argument("--no-database", action="store_true")
    stations_parser.add_argument("--force", action="store_true")

    weather_parser = subparsers.add_parser("ingest-weather", help="Ingest historical weather")
    weather_parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    weather_parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    weather_parser.add_argument("--no-database", action="store_true")

    train_parser = subparsers.add_parser("train", help="Backtest and train direct models")
    train_parser.add_argument("--quick", action="store_true")

    subparsers.add_parser("predict", help="Generate latest station forecasts")
    subparsers.add_parser("report", help="Generate README metrics and charts")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested command."""

    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    if args.command == "status":
        settings.ensure_directories()
        print(
            json.dumps(
                {
                    "version": __version__,
                    "data_dir": str(settings.data_dir),
                    "artifacts_dir": str(settings.artifacts_dir),
                    "reports_dir": str(settings.reports_dir),
                    "data_years": [settings.data_start_year, settings.data_end_year],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "ingest-air-quality":
        years = args.years or list(range(settings.data_start_year, settings.data_end_year + 1))
        frame = ingest_air_quality(
            settings,
            years,
            load_database=not args.no_database,
            force=args.force,
        )
        print(json.dumps({"dataset": "air_quality", "rows": len(frame), "years": years}))
        return 0

    if args.command == "ingest-stations":
        frame = ingest_stations(
            settings,
            load_database=not args.no_database,
            force=args.force,
        )
        print(json.dumps({"dataset": "stations", "rows": len(frame)}))
        return 0

    if args.command == "ingest-weather":
        frame = ingest_weather(
            settings,
            args.start_date,
            args.end_date,
            load_database=not args.no_database,
        )
        print(json.dumps({"dataset": "weather", "rows": len(frame)}))
        return 0

    if args.command == "train":
        metrics = train_all_horizons(
            settings.processed_data_dir,
            settings.artifacts_dir,
            settings.reports_dir,
            n_splits=2 if args.quick else 3,
            validation_days=7 if args.quick else 14,
            min_training_days=90 if args.quick else 180,
            max_training_days=365 if args.quick else 730,
            n_estimators=50 if args.quick else 200,
        )
        print(json.dumps({"metric_rows": len(metrics), "quick": args.quick}))
        return 0

    if args.command == "predict":
        forecasts = predict_latest(
            settings.processed_data_dir,
            settings.artifacts_dir,
            settings.reports_dir,
        )
        print(json.dumps({"forecast_rows": len(forecasts)}))
        return 0

    if args.command == "report":
        summary = generate_report_assets(
            settings.processed_data_dir,
            settings.reports_dir,
            settings.project_root / "docs" / "assets",
        )
        print(json.dumps(summary))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
