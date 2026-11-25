import numpy as np
import pandas as pd
import pytest

from servo_current_detection.metrics import evaluate
from servo_current_detection.model import DetectorConfig, PhaseAwareGPRDetector
from servo_current_detection.synthetic import make_synthetic_dataset


def test_detector_fit_predict_and_evaluate_synthetic_data(tmp_path):
    paths = make_synthetic_dataset(
        tmp_path,
        training_cycles_per_station=8,
        scale_cycles_per_station=8,
        calibration_cycles_per_station=20,
        test_normal_cycles_per_station=4,
        test_anomaly_cycles_per_station=4,
    )
    detector = PhaseAwareGPRDetector(DetectorConfig(
        alpha=0.05,
        n_bins=10,
        min_bin_samples=8,
        max_training_points_per_joint=60,
    ))
    detector.fit(
        pd.read_csv(paths["training"]),
        pd.read_csv(paths["scale"]),
        pd.read_csv(paths["calibration"]),
    )
    test_data = pd.read_csv(paths["test"])
    prediction = detector.predict_samples(test_data)
    assert "anomaly_score" in prediction.columns
    assert "alarm" in prediction.columns
    report = evaluate(detector, test_data)
    expected_columns = {
        "far_ci_lower_per_1000",
        "far_ci_upper_per_1000",
        "pod_ci_lower",
        "pod_ci_upper",
    }
    assert expected_columns.issubset(report.columns)

    short_cycle = test_data.groupby("cycle_id", sort=False).head(2)
    with pytest.raises(ValueError, match="at least 3 are required"):
        detector.score_cycles(short_cycle)


def test_fit_rejects_cycle_leakage_between_partitions(tmp_path):
    paths = make_synthetic_dataset(
        tmp_path,
        training_cycles_per_station=3,
        scale_cycles_per_station=3,
        calibration_cycles_per_station=3,
        test_normal_cycles_per_station=2,
        test_anomaly_cycles_per_station=2,
    )
    training = pd.read_csv(paths["training"])
    scale = pd.read_csv(paths["scale"])
    calibration = pd.read_csv(paths["calibration"])
    leaked_cycle_id = training.loc[0, "cycle_id"]
    leaked_cycle = training[training["cycle_id"] == leaked_cycle_id]
    scale = pd.concat([scale, leaked_cycle], ignore_index=True)

    detector = PhaseAwareGPRDetector(DetectorConfig(
        alpha=0.05,
        n_bins=5,
        min_bin_samples=5,
        max_training_points_per_joint=60,
    ))
    with pytest.raises(ValueError, match="Cycle leakage"):
        detector.fit(training, scale, calibration)


def test_residual_statistics_center_systematic_bias():
    detector = PhaseAwareGPRDetector(DetectorConfig(
        n_bins=4,
        min_bin_samples=2,
        scale_floor_pct=0.1,
    ))
    progress = np.linspace(0.0, 1.0, 40)
    residual = np.full(40, 2.5) + np.linspace(-0.03, 0.03, 40)
    centers, scales = detector._fit_robust_statistics(progress, residual)

    assert np.allclose(centers, 2.5, atol=0.03)
    assert np.all(scales >= 0.1)
