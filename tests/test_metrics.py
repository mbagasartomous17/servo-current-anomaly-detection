import pandas as pd
import pytest

from servo_current_detection.metrics import clopper_pearson, evaluate_predictions
from servo_current_detection.schema import JOINTS


def test_clopper_pearson_bounds_zero_false_alarms():
    lower, upper = clopper_pearson(0, 100)
    assert lower == 0.0
    assert 0.0 < upper < 0.1


def test_clopper_pearson_all_successes():
    lower, upper = clopper_pearson(10, 10)
    assert 0.0 < lower < 1.0
    assert upper == 1.0


def test_clopper_pearson_rejects_invalid_counts():
    with pytest.raises(ValueError):
        clopper_pearson(11, 10)


def test_detection_delay_uses_explicit_event_onset_not_cycle_start():
    data = {joint: [1.0, 1.1, 1.2] for joint in JOINTS}
    data.update({
        "cycle_id": ["anomaly_1"] * 3,
        "station_id": ["station_a"] * 3,
        "progress": [0.0, 0.5, 1.0],
        "label": [1, 1, 1],
        "time_ms": [0.0, 4.0, 8.0],
        "event_onset_time_ms": [4.0, 4.0, 4.0],
        "anomaly_score": [0.5, 2.0, 3.0],
        "threshold": [1.0, 1.0, 1.0],
        "alarm": [False, False, True],
    })
    summary, cycles = evaluate_predictions(pd.DataFrame(data))
    assert cycles.loc[0, "latency_ms"] == 4.0
    assert summary.loc[0, "median_detection_latency_ms"] == 4.0


def test_detection_delay_is_empty_without_explicit_event_onset():
    data = {joint: [1.0, 1.1, 1.2] for joint in JOINTS}
    data.update({
        "cycle_id": ["anomaly_1"] * 3,
        "station_id": ["station_a"] * 3,
        "progress": [0.0, 0.5, 1.0],
        "label": [1, 1, 1],
        "time_ms": [0.0, 4.0, 8.0],
        "anomaly_score": [0.5, 2.0, 3.0],
        "threshold": [1.0, 1.0, 1.0],
        "alarm": [False, False, True],
    })
    summary, cycles = evaluate_predictions(pd.DataFrame(data))
    assert pd.isna(cycles.loc[0, "latency_ms"])
    assert pd.isna(summary.loc[0, "median_detection_latency_ms"])


def test_pre_onset_alarm_does_not_count_as_anomaly_detection():
    data = {joint: [1.0, 1.1, 1.2] for joint in JOINTS}
    data.update({
        "cycle_id": ["anomaly_early_alarm"] * 3,
        "station_id": ["station_a"] * 3,
        "progress": [0.0, 0.5, 1.0],
        "label": [1, 1, 1],
        "time_ms": [0.0, 4.0, 8.0],
        "event_onset_time_ms": [8.0, 8.0, 8.0],
        "anomaly_score": [2.0, 0.5, 0.5],
        "threshold": [1.0, 1.0, 1.0],
        "alarm": [True, False, False],
    })
    summary, cycles = evaluate_predictions(pd.DataFrame(data))
    assert cycles.loc[0, "detected"] == 0
    assert cycles.loc[0, "pre_onset_alarm"] is True or bool(cycles.loc[0, "pre_onset_alarm"])
    assert summary.loc[0, "detected_anomalies"] == 0
    assert summary.loc[0, "pre_onset_alarms"] == 1
