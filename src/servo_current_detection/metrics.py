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


def evaluate_predictions(
    prediction: pd.DataFrame,
    *,
    confidence: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize an already-scored, already-thresholded prediction table.

    Returns ``(station_summary, cycle_details)``. Detection latency is computed only
    when the input has an explicit ``event_onset_time_ms`` ground-truth column. It is
    never inferred from cycle start, because cycle-start-to-alarm is not fault latency.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    frame = validate_frame(prediction, name="prediction", require_label=True)
    missing = [name for name in ("alarm", "anomaly_score") if name not in frame.columns]
    if missing:
        raise ValueError(f"prediction is missing required columns: {missing}")

    rows: list[dict[str, float | int | str | bool]] = []
    for (station, cycle_id), group in cycle_groups(frame):
        alarm_rows = group[group["alarm"].astype(bool)]
        label = int(group["label"].iloc[0])
        detected = not alarm_rows.empty
        pre_onset_alarm = False
        latency = math.nan
        if (
            label == 1
            and "event_onset_time_ms" in group.columns
            and "time_ms" in group.columns
        ):
            onset_values = group["event_onset_time_ms"].dropna().unique()
            if len(onset_values) == 1:
                onset = float(onset_values[0])
                before = alarm_rows[alarm_rows["time_ms"] < onset]
                after = alarm_rows[alarm_rows["time_ms"] >= onset]
                pre_onset_alarm = not before.empty
                detected = not after.empty
                if detected:
                    latency = float(after.iloc[0]["time_ms"]) - onset
        rows.append({
            "station_id": str(station),
            "cycle_id": str(cycle_id),
            "label": label,
            "detected": int(detected),
            "pre_onset_alarm": bool(pre_onset_alarm),
            "latency_ms": latency,
        })

    cycles = pd.DataFrame(rows)
    summary: list[dict[str, float | int | str]] = []
    for station, group in cycles.groupby("station_id", sort=True):
        normal = group[group["label"] == 0]
        anomalous = group[group["label"] == 1]
        false_alarms = int(normal["detected"].sum())
        pre_onset_alarms = int(anomalous["pre_onset_alarm"].sum())
        hits = int(anomalous["detected"].sum())
        far_low, far_high = clopper_pearson(false_alarms, len(normal), confidence)
        pod_low, pod_high = clopper_pearson(hits, len(anomalous), confidence)
        detected_anomalies = anomalous[anomalous["detected"] == 1]
        available_latency = detected_anomalies["latency_ms"].dropna()
        median_latency = float(np.median(available_latency)) if not available_latency.empty else math.nan
        summary.append({
            "station_id": str(station),
            "normal_cycles": len(normal),
            "false_alarms": false_alarms,
            "pre_onset_alarms": pre_onset_alarms,
            "far_per_1000_cycles": (
                1000.0 * false_alarms / len(normal) if len(normal) else math.nan
            ),
            "far_ci_lower_per_1000": 1000.0 * far_low,
            "far_ci_upper_per_1000": 1000.0 * far_high,
            "anomaly_cycles": len(anomalous),
            "detected_anomalies": hits,
            "pod": hits / len(anomalous) if len(anomalous) else math.nan,
            "pod_ci_lower": pod_low,
            "pod_ci_upper": pod_high,
            "median_detection_latency_ms": median_latency,
            "confidence_level": confidence,
        })
    return pd.DataFrame(summary), cycles


def evaluate(
    detector: PhaseAwareGPRDetector,
    test: pd.DataFrame,
    *,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Evaluate normal false alarms and labelled anomaly detection by station.

    FAR is reported per 1,000 normal cycles; POD is reported on labelled anomalous
    cycles. Both include two-sided exact Clopper-Pearson confidence intervals.
    Latency is reported only when ground-truth event onset is explicitly supplied.
    """
    frame = validate_frame(test, name="test", require_label=True)
    prediction = detector.predict_samples(frame)
    summary, _cycles = evaluate_predictions(prediction, confidence=confidence)
    return summary
