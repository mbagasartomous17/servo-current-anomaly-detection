import pandas as pd

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
    prediction = detector.predict_samples(pd.read_csv(paths["test"]))
    assert "anomaly_score" in prediction.columns
    assert "alarm" in prediction.columns
    report = evaluate(detector, pd.read_csv(paths["test"]))
    assert set(["far_ci_lower_per_1000", "far_ci_upper_per_1000", "pod_ci_lower", "pod_ci_upper"]).issubset(report.columns)
