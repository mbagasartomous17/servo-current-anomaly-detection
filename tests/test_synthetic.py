from servo_current_detection.synthetic import make_synthetic_dataset


def test_synthetic_generator_creates_independent_partitions(tmp_path):
    paths = make_synthetic_dataset(
        tmp_path, training_cycles_per_station=3, scale_cycles_per_station=2,
        calibration_cycles_per_station=3, test_normal_cycles_per_station=2,
        test_anomaly_cycles_per_station=2,
    )
    assert set(paths) == {"training", "scale", "calibration", "test"}
    assert all(path.exists() for path in paths.values())
