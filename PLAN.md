# Madrid NO2 Forecasting - Execution Plan

## Objective

Build a reproducible end-to-end pipeline that ingests official Madrid air-quality
observations, models station-level hourly data, and produces leakage-safe NO2
forecasts for 1, 24, and 72 hour horizons.

The MVP ends when the complete local workflow can be executed from a clean clone
through documented `make` commands. FastAPI, Airflow, dashboards, and advanced
MLOps are explicitly outside the MVP.

## Product Contract

The MVP uses one global model per forecast horizon, trained with observations from
all eligible stations and producing a forecast for each station.

Observation grain:

```text
station_id + observed_at
```

Prediction grain:

```text
station_id + prediction_created_at + target_at + horizon_hours + model_version
```

Core rules:

- Store canonical timestamps in UTC and retain source timezone metadata.
- Use Madrid Open Data measurements as the source of truth for NO2.
- Ingest historical Open-Meteo weather, but do not use future observed weather as
  a model feature.
- Build analytical tables with dbt and forecasting features in Python.
- Compare XGBoost against seasonal-naive 24-hour and 168-hour baselines.
- Report results honestly, including cases where a baseline wins.
- Do not advance to the next phase while the current phase gate is failing.
- Preserve legacy notebooks until their responsibilities have verified replacements.

## Phase 1 - Reproducible Foundations

Deliverables:

- Python package under `src/madrid_pollution/`.
- `pyproject.toml`, `uv.lock`, and pinned Python version.
- Typed settings, project paths, and logging configuration.
- Ruff, pre-commit, pytest, and GitHub Actions.
- Make targets for setup, linting, formatting, and tests.
- Honest first-pass README with component status and architecture.

Gate:

```bash
make setup
make lint
make test
```

All commands must pass without relying on untracked datasets or external services.

## Phase 2 - Official Data Pipeline

Deliverables:

- Historical and incremental Madrid Open Data downloader.
- Parser for annual/monthly hourly files and official validity flags.
- Station catalogue ingestion and normalized station metadata.
- Historical Open-Meteo weather ingestion.
- Raw Parquet cache with source metadata and deterministic paths.
- Idempotent PostgreSQL loading and schema initialization.
- HTTP retries, validation, structured errors, and mocked unit tests.
- Explicit handling of timezone and daylight-saving transitions.

Gate:

- The dataset can be rebuilt without notebooks or manual file edits.
- Repeated ingestion does not duplicate database rows.
- Unit tests cover representative source formats and invalid records.

## Phase 3 - Analytical Modeling With dbt

Deliverables:

```text
staging/
  stg_air_quality
  stg_stations
  stg_weather
intermediate/
  int_station_hourly
marts/
  fct_no2_observations
  mart_station_daily
```

- Source declarations, descriptions, contracts, and lineage.
- Tests for grain uniqueness, required values, relationships, ranges, and freshness.
- SQLFluff configuration compatible with dbt-postgres.

Gate:

```bash
make dbt-build
```

The command must build and test the project against the local PostgreSQL service.

## Phase 4 - Leakage-Safe Forecasting

Deliverables:

- Calendar and cyclical features.
- Shifted lag and rolling-window features using only information available at the
  prediction timestamp.
- Direct targets for 1, 24, and 72 hour horizons.
- Seasonal-naive 24-hour and 168-hour baselines.
- One global XGBoost model per horizon, with station and station metadata features.
- Rolling-origin backtesting with documented folds.
- MAE, RMSE, MASE, and sMAPE overall and by horizon/station.
- Tests that fail when future data leaks into features.
- Versioned artifacts and metrics with training cutoff and data metadata.

Gate:

- Backtests are deterministic and leakage tests pass.
- Every model is compared with both baselines.
- Metrics and artifacts can be regenerated through project commands.

## Phase 5 - Reproducible MVP Demo

Required workflow:

```bash
make setup
make up
make ingest
make dbt-build
make train
make predict
make test
make demo
```

Deliverables:

- A small, deterministic demo profile suitable for local execution and CI smoke
  tests.
- End-to-end predictions persisted at the declared grain.
- Final README with real metrics, architecture, data model, leakage controls,
  limitations, and reproducible examples.
- Generated charts comparing observations, predictions, models, and horizons.

Gate:

- A clean clone can reproduce the documented demo.
- README claims match generated outputs.

## Post-MVP Extensions

### Phase 6 - FastAPI

- `/health`, `/stations`, and `/forecasts`.
- Read precomputed predictions from PostgreSQL.
- Pydantic schemas, controlled errors, and API tests.

### Phase 7 - Optional Operations

- Thin Airflow DAGs that call the verified CLI.
- Scheduled ingestion, training, prediction, and matured-forecast evaluation.
- Simple dashboard and operational health views.

## Explicitly Out Of Scope Before MVP

- LSTM or other deep-learning models.
- MLflow, Evidently, Grafana, Kubernetes, or MinIO/S3.
- Complex multi-environment infrastructure.
- Real-time online inference.
- Claims of causal impact from Madrid Central.

## Progress

| Phase | Status | Gate |
|---|---|---|
| 1. Foundations | Complete | `make setup && make lint && make test` passing |
| 2. Data pipeline | Integration pending | Parquet rebuild passes; PostgreSQL gate pending |
| 3. dbt | Integration pending | Parse/lint pass; `make dbt-build` pending PostgreSQL |
| 4. Forecasting | Complete | Deterministic leakage-safe backtest passes |
| 5. MVP demo | In progress | Parquet demo passes; clean-clone database path pending |
| 6. FastAPI | Post-MVP | API contract tests |
| 7. Operations | Optional | Scheduled workflow and health checks |
