"""Generate reproducible portfolio charts and summary artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pandas as pd

from madrid_pollution.modeling.features import load_processed_inputs

matplotlib.use("Agg")
from matplotlib import pyplot as plt

MODEL_LABELS = {
    "seasonal_naive_24h": "Seasonal naive 24h",
    "seasonal_naive_168h": "Seasonal naive 168h",
    "xgboost": "XGBoost",
}
MODEL_COLORS = {
    "seasonal_naive_24h": "#94a3b8",
    "seasonal_naive_168h": "#cbd5e1",
    "xgboost": "#2563eb",
}


def _save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def generate_report_assets(
    processed_data_dir: Path,
    reports_dir: Path,
    docs_assets_dir: Path,
) -> dict[str, object]:
    """Generate data summaries and charts from pipeline outputs."""

    metrics = pd.read_csv(
        reports_dir / "backtest_metrics.csv",
        dtype={"station_id": "string"},
    )
    predictions = pd.read_parquet(reports_dir / "backtest_predictions.parquet")
    observations, stations = load_processed_inputs(processed_data_dir)

    overall = metrics.loc[metrics["scope"].eq("overall")].copy()
    summary = (
        overall.groupby(["horizon_hours", "model"], as_index=False)[
            ["mae", "rmse", "mase", "smape"]
        ]
        .mean()
        .sort_values(["horizon_hours", "model"])
    )
    summary.to_csv(reports_dir / "model_summary.csv", index=False)

    _figure, axis = plt.subplots(figsize=(9, 5))
    pivot = summary.pivot(index="horizon_hours", columns="model", values="mae")
    ordered_models = ["seasonal_naive_168h", "seasonal_naive_24h", "xgboost"]
    pivot = pivot[ordered_models]
    pivot.rename(columns=MODEL_LABELS).plot(
        kind="bar",
        ax=axis,
        color=[MODEL_COLORS[model] for model in ordered_models],
        width=0.78,
    )
    axis.set_title("Mean absolute error by forecast horizon")
    axis.set_xlabel("Forecast horizon (hours)")
    axis.set_ylabel("MAE (µg/m³, lower is better)")
    axis.tick_params(axis="x", rotation=0)
    axis.legend(title="Model", frameon=False)
    axis.grid(axis="y", alpha=0.25)
    _save_figure(docs_assets_dir / "mae_by_horizon.png")

    station_metrics = metrics.loc[
        metrics["scope"].eq("station")
        & metrics["model"].eq("xgboost")
        & metrics["horizon_hours"].eq(24)
    ]
    station_summary = station_metrics.groupby("station_id")["mae"].mean().sort_values()
    median_mae = station_summary.median()
    station_id = str((station_summary - median_mae).abs().idxmin())
    example = predictions.loc[predictions["horizon_hours"].eq(24)].copy()
    example = example.loc[example["station_id"].astype(str).eq(station_id)].sort_values("target_at")
    _figure, axis = plt.subplots(figsize=(11, 5))
    axis.plot(
        example["target_at"],
        example["target_no2_ug_m3"],
        label="Observed",
        color="#0f172a",
        linewidth=1.8,
    )
    axis.plot(
        example["target_at"],
        example["predicted_no2_ug_m3"],
        label="XGBoost",
        color=MODEL_COLORS["xgboost"],
        linewidth=1.5,
    )
    axis.plot(
        example["target_at"],
        example["baseline_24h"],
        label="Seasonal naive 24h",
        color=MODEL_COLORS["seasonal_naive_24h"],
        linewidth=1.2,
        alpha=0.8,
    )
    axis.set_title(f"24-hour forecast example - median-error station {station_id}")
    axis.set_xlabel("Target timestamp (UTC)")
    axis.set_ylabel("NO₂ (µg/m³)")
    axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    _save_figure(docs_assets_dir / "forecast_example_24h.png")

    _figure, axis = plt.subplots(figsize=(9, 7))
    station_summary.plot(kind="barh", ax=axis, color="#2563eb")
    axis.set_title("XGBoost 24-hour MAE by station")
    axis.set_xlabel("MAE (µg/m³, lower is better)")
    axis.set_ylabel("Station ID")
    axis.grid(axis="x", alpha=0.25)
    _save_figure(docs_assets_dir / "station_mae_24h.png")

    data_summary: dict[str, object] = {
        "observation_rows": len(observations),
        "station_catalogue_rows": len(stations),
        "observation_stations": int(observations["station_id"].nunique()),
        "observation_start": pd.to_datetime(observations["observed_at"], utc=True)
        .min()
        .isoformat(),
        "observation_end": pd.to_datetime(observations["observed_at"], utc=True).max().isoformat(),
        "backtest_station_count": int(
            metrics.loc[metrics["scope"].eq("station"), "station_id"].nunique()
        ),
        "example_station_id": station_id,
    }
    (reports_dir / "data_summary.json").write_text(
        json.dumps(data_summary, indent=2), encoding="utf-8"
    )
    return data_summary
