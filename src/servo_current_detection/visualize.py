"""Matplotlib plots for benchmark summaries and cycle-level diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .schema import JOINTS


def _pyplot():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on optional installation
        raise RuntimeError(
            "Plotting requires the optional visualization dependencies. "
            'Install them with: python -m pip install -e ".[viz]"'
        ) from exc
    return plt


def plot_benchmark_summary(summary: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    """Save FAR and POD plots with confidence-interval error bars.

    Rows are kept station-specific; metrics are not pooled across stations.
    """
    required = {
        "method", "station_id", "far_per_1000_cycles", "far_ci_lower_per_1000",
        "far_ci_upper_per_1000", "pod", "pod_ci_lower", "pod_ci_upper",
    }
    missing = sorted(required - set(summary.columns))
    if missing:
        raise ValueError(f"summary is missing plot columns: {missing}")
    if summary.empty:
        raise ValueError("summary is empty")

    plt = _pyplot()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    methods = list(dict.fromkeys(summary["method"].astype(str)))
    stations = list(dict.fromkeys(summary["station_id"].astype(str)))
    x = np.arange(len(methods), dtype=float)
    width = 0.8 / max(1, len(stations))
    paths: dict[str, Path] = {}

    for metric, low_col, high_col, ylabel, filename, title in (
        (
            "far_per_1000_cycles", "far_ci_lower_per_1000", "far_ci_upper_per_1000",
            "False alarms per 1,000 normal cycles", "benchmark_far.png",
            "False-alarm rate by method and station",
        ),
        (
            "pod", "pod_ci_lower", "pod_ci_upper", "Probability of detection",
            "benchmark_pod.png", "Probability of detection by method and station",
        ),
    ):
        fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
        for station_index, station in enumerate(stations):
            rows = summary[summary["station_id"].astype(str) == station].set_index("method")
            values = np.array([rows.loc[m, metric] if m in rows.index else np.nan for m in methods], dtype=float)
            lows = np.array([rows.loc[m, low_col] if m in rows.index else np.nan for m in methods], dtype=float)
            highs = np.array([rows.loc[m, high_col] if m in rows.index else np.nan for m in methods], dtype=float)
            valid = np.isfinite(values) & np.isfinite(lows) & np.isfinite(highs)
            positions = x + (station_index - (len(stations) - 1) / 2) * width
            if valid.any():
                lower_error = np.maximum(0.0, values[valid] - lows[valid])
                upper_error = np.maximum(0.0, highs[valid] - values[valid])
                ax.errorbar(
                    positions[valid], values[valid], yerr=np.vstack([lower_error, upper_error]),
                    fmt="o", capsize=4, label=station,
                )
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x, methods, rotation=22, ha="right")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(title="Station")
        path = output / filename
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths[metric] = path
    return paths


def plot_cycle_diagnostics(
    sample_scores: pd.DataFrame,
    *,
    method: str,
    station_id: str,
    cycle_id: str,
    output_path: str | Path,
) -> Path:
    """Plot six raw current channels and the calibrated anomaly score for one cycle."""
    required = {"method", "station_id", "cycle_id", "progress", "anomaly_score", "threshold", "alarm", *JOINTS}
    missing = sorted(required - set(sample_scores.columns))
    if missing:
        raise ValueError(f"sample_scores is missing plot columns: {missing}")
    cycle = sample_scores[
        (sample_scores["method"] == method)
        & (sample_scores["station_id"].astype(str) == str(station_id))
        & (sample_scores["cycle_id"].astype(str) == str(cycle_id))
    ].sort_values("progress")
    if cycle.empty:
        raise ValueError("No rows match the selected method, station_id, and cycle_id")

    plt = _pyplot()
    fig, (signal_ax, score_ax) = plt.subplots(
        2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]},
        constrained_layout=True,
    )
    progress = cycle["progress"].to_numpy(dtype=float)
    for joint in JOINTS:
        signal_ax.plot(progress, cycle[joint].to_numpy(dtype=float), label=joint.removesuffix("_pct"))
    signal_ax.set_ylabel("Current (% rated current)")
    signal_ax.set_title(f"{method} — {station_id} — {cycle_id}")
    signal_ax.grid(alpha=0.25)
    signal_ax.legend(ncol=3, fontsize=8)

    score = cycle["anomaly_score"].to_numpy(dtype=float)
    threshold = cycle["threshold"].to_numpy(dtype=float)
    score_ax.plot(progress, score, label="Anomaly score")
    score_ax.plot(progress, threshold, linestyle="--", label="Calibrated threshold")
    alarms = cycle["alarm"].astype(bool).to_numpy()
    if alarms.any():
        score_ax.scatter(progress[alarms], score[alarms], marker="x", s=55, label="Alarm sample")
    if "event_onset_time_ms" in cycle.columns and "time_ms" in cycle.columns:
        onset = cycle["event_onset_time_ms"].dropna().unique()
        if len(onset) == 1:
            times = cycle["time_ms"].to_numpy(dtype=float)
            onset_index = int(np.argmin(np.abs(times - onset[0])))
            score_ax.axvline(progress[onset_index], linestyle=":", label="Synthetic event onset")
    score_ax.set_xlabel("Normalized movement progress")
    score_ax.set_ylabel("Normalized anomaly score")
    score_ax.grid(alpha=0.25)
    score_ax.legend(fontsize=8)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
