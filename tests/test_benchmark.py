import pandas as pd

from servo_current_detection.benchmark import METHODS, run_benchmark
from servo_current_detection.synthetic import make_synthetic_dataset


def test_benchmark_uses_same_partitions_and_returns_all_method_outputs(tmp_path):
    paths = make_synthetic_dataset(
        tmp_path,
        training_cycles_per_station=8,
        scale_cycles_per_station=8,
        calibration_cycles_per_station=20,
        test_normal_cycles_per_station=4,
        test_anomaly_cycles_per_station=4,
    )
    result = run_benchmark(
        pd.read_csv(paths["training"]),
        pd.read_csv(paths["scale"]),
        pd.read_csv(paths["calibration"]),
        pd.read_csv(paths["test"]),
        alpha=0.05,
        consecutive=3,
    )
    assert set(result.summary["method"]) == set(METHODS)
    assert set(result.summary["station_id"]) == {"station_a", "station_b"}
    assert {"far_per_1000_cycles", "pod", "pod_ci_lower", "pod_ci_upper"}.issubset(
        result.summary.columns
    )
    assert {"alarm", "threshold", "anomaly_score", "method"}.issubset(
        result.sample_scores.columns
    )
    assert result.cycle_metrics["cycle_id"].nunique() == 16
    assert set(result.thresholds) == set(METHODS)


def test_benchmark_rejects_cycle_leakage(tmp_path):
    paths = make_synthetic_dataset(
        tmp_path,
        training_cycles_per_station=4,
        scale_cycles_per_station=4,
        calibration_cycles_per_station=20,
        test_normal_cycles_per_station=2,
        test_anomaly_cycles_per_station=2,
    )
    training = pd.read_csv(paths["training"])
    scale = pd.read_csv(paths["scale"])
    training.loc[0:79, "cycle_id"] = scale.loc[0:79, "cycle_id"].to_numpy()
    try:
        run_benchmark(
            training,
            scale,
            pd.read_csv(paths["calibration"]),
            pd.read_csv(paths["test"]),
            alpha=0.05,
            methods=("global_robust",),
        )
    except ValueError as exc:
        assert "Cycle leakage" in str(exc)
    else:
        raise AssertionError("Expected benchmark to reject cycle leakage")
