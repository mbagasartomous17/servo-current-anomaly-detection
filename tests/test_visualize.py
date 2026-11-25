import pandas as pd
import pytest

from servo_current_detection.benchmark import run_benchmark
from servo_current_detection.synthetic import make_synthetic_dataset
from servo_current_detection.visualize import plot_benchmark_summary, plot_cycle_diagnostics


def test_benchmark_visualizations_are_written(tmp_path):
    pytest.importorskip("matplotlib")
    paths = make_synthetic_dataset(
        tmp_path / "data",
        training_cycles_per_station=6,
        scale_cycles_per_station=6,
        calibration_cycles_per_station=20,
        test_normal_cycles_per_station=3,
        test_anomaly_cycles_per_station=3,
    )
    result = run_benchmark(
        pd.read_csv(paths["training"]),
        pd.read_csv(paths["scale"]),
        pd.read_csv(paths["calibration"]),
        pd.read_csv(paths["test"]),
        alpha=0.05,
        methods=("global_robust", "gpr_phase_aware"),
    )
    paths_out = plot_benchmark_summary(result.summary, tmp_path / "plots")
    assert paths_out["far_per_1000_cycles"].is_file()
    assert paths_out["pod"].is_file()

    anomaly = result.sample_scores[
        (result.sample_scores["method"] == "gpr_phase_aware")
        & (result.sample_scores["label"] == 1)
    ].iloc[0]
    cycle_plot = plot_cycle_diagnostics(
        result.sample_scores,
        method="gpr_phase_aware",
        station_id=anomaly["station_id"],
        cycle_id=anomaly["cycle_id"],
        output_path=tmp_path / "plots" / "cycle.png",
    )
    assert cycle_plot.is_file()
    assert cycle_plot.stat().st_size > 0
