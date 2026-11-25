"""Cycle-level evaluation metrics with exact binomial confidence intervals."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import beta

from .model import PhaseAwareGPRDetector
from .schema import cycle_groups, validate_frame


def clopper_pearson(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Return a two-sided exact Clopper-Pearson binomial interval."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Require 0 <= successes <= trials")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if trials == 0:
        return math.nan, math.nan
    tail = (1.0 - confidence) / 2.0
    lower = 0.0 if successes == 0 else float(beta.ppf(tail, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1.0 - tail, successes + 1, trials - successes))
    return lower, upper


def evaluate(
    detector: PhaseAwareGPRDetector,
    test: pd.DataFrame,
    *,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Evaluate normal false alarms and labelled anomaly detection by station.

    FAR is reported per 1,000 normal cycles; POD is reported on labelled anomalous
    cycles. Both include two-sided exact Clopper-Pearson confidence intervals.
    Detection latency is only reported when `time_ms` exists.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    frame = validate_frame(test, name="test", require_label=True)
    prediction = detector.predict_samples(frame)
    rows: list[dict[str, float | int | str]] = []

    for (station, cycle_id), group in cycle_groups(prediction):
        alarm_rows = group[group["alarm"]]
        detected = not alarm_rows.empty
        label = int(group["label"].max())
        latency = math.nan
        if detected and label == 1 and "time_ms" in group.columns:
            first_time = float(group["time_ms"].min())
            latency = float(alarm_rows.iloc[0]["time_ms"]) - first_time
        rows.append({
            "station_id": str(station),
            "cycle_id": str(cycle_id),
            "label": label,
            "detected": int(detected),
            "latency_ms": latency,
        })

    cycles = pd.DataFrame(rows)
    summary: list[dict[str, float | int | str]] = []
    for station, group in cycles.groupby("station_id", sort=True):
        normal = group[group["label"] == 0]
        anomalous = group[group["label"] == 1]
        false_alarms = int(normal["detected"].sum())
        hits = int(anomalous["detected"].sum())
        far_low, far_high = clopper_pearson(false_alarms, len(normal), confidence)
        pod_low, pod_high = clopper_pearson(hits, len(anomalous), confidence)
        detected_anomalies = anomalous[anomalous["detected"] == 1]
        median_latency = (
            float(np.median(detected_anomalies["latency_ms"].dropna()))
            if "time_ms" in prediction.columns and not detected_anomalies["latency_ms"].dropna().empty
            else math.nan
        )
        summary.append({
            "station_id": str(station),
            "normal_cycles": int(len(normal)),
            "false_alarms": false_alarms,
            "far_per_1000_cycles": 1000.0 * false_alarms / len(normal) if len(normal) else math.nan,
            "far_ci_lower_per_1000": 1000.0 * far_low,
            "far_ci_upper_per_1000": 1000.0 * far_high,
            "anomaly_cycles": int(len(anomalous)),
            "detected_anomalies": hits,
            "pod": hits / len(anomalous) if len(anomalous) else math.nan,
            "pod_ci_lower": pod_low,
            "pod_ci_upper": pod_high,
            "median_detection_latency_ms": median_latency,
            "confidence_level": confidence,
        })
    return pd.DataFrame(summary)
