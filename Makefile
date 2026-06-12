.DEFAULT_GOAL := help

UV_CACHE_DIR ?= .uv-cache
export UV_CACHE_DIR

.PHONY: help setup status lint format test quality up down ingest ingest-local dbt-parse dbt-build

help:
	@printf '%s\n' \
		'setup    Install locked project and development dependencies' \
		'status   Show resolved local project configuration' \
		'lint     Run Ruff lint and formatting checks' \
		'format   Apply Ruff lint fixes and formatting' \
		'test     Run the Python test suite with coverage' \
		'quality  Run lint and tests' \
		'up       Start local PostgreSQL' \
		'down     Stop local services' \
		'ingest   Ingest official data into Parquet and PostgreSQL' \
		'ingest-local  Ingest one demo year into Parquet without PostgreSQL' \
		'dbt-parse  Validate the dbt project without running models' \
		'dbt-build  Build and test all dbt models'

setup:
	uv sync --all-groups

status:
	uv run madrid-pollution status

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest --cov=madrid_pollution --cov-report=term-missing

quality: lint test

up:
	docker compose --env-file .env -f infra/docker-compose.yml up -d --wait

down:
	docker compose --env-file .env -f infra/docker-compose.yml down

ingest:
	uv run madrid-pollution ingest-stations
	uv run madrid-pollution ingest-air-quality
	uv run madrid-pollution ingest-weather --start-date 2018-01-01 --end-date 2025-12-31

ingest-local:
	uv run madrid-pollution ingest-stations --no-database
	uv run madrid-pollution ingest-air-quality --years 2024 --no-database
	uv run madrid-pollution ingest-weather --start-date 2024-01-01 --end-date 2024-01-07 --no-database

dbt-parse:
	uv run dbt parse --project-dir dbt --profiles-dir dbt

dbt-build:
	uv run dbt build --project-dir dbt --profiles-dir dbt
