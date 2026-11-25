"""Command-line interface for synthetic generation, detection, and benchmarking."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path

import pandas as pd

from . import __version__
from .benchmark import METHODS, run_benchmark
from .metrics import evaluate
from .model import DetectorConfig, PhaseAwareGPRDetector
from .synthetic import make_synthetic_dataset
from .visualize import plot_benchmark_summary, plot_cycle_diagnostics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="servo-current-detector")
    commands = parser.add_subparsers(dest="command", required=True)

    synthetic = commands.add_parser("make-synthetic", help="generate synthetic tutorial CSV files")
    synthetic.add_argument("--output", default="examples/synthetic_data")
    synthetic.add_argument("--seed", type=int, default=2026)

    fit = commands.add_parser("fit", help="fit GPR models and calibrate thresholds")
    fit.add_argument("--training", required=True)
    fit.add_argument("--scale", required=True)
    fit.add_argument("--calibration", required=True)
    fit.add_argument("--model-out", default="artifacts/detector.joblib")
    fit.add_argument("--alpha", type=float, default=0.001)
    fit.add_argument("--consecutive", type=int, default=3)

    test = commands.add_parser("evaluate", help="evaluate a calibrated GPR detector")
    test.add_argument("--model", required=True)
    test.add_argument("--test", required=True)
    test.add_argument("--output", default="results/metrics.csv")

    benchmark = commands.add_parser(
        "benchmark", help="compare GPR and baseline methods on identical data partitions"
    )
    benchmark.add_argument("--training", required=True)
    benchmark.add_argument("--scale", required=True)
    benchmark.add_argument("--calibration", required=True)
    benchmark.add_argument("--test", required=True)
    benchmark.add_argument("--output-dir", default="results/benchmark")
    benchmark.add_argument("--alpha", type=float, default=0.05)
    benchmark.add_argument("--consecutive", type=int, default=3)
    benchmark.add_argument("--seed", type=int, default=2026)
    benchmark.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    benchmark.add_argument("--no-plots", action="store_true", help="write CSV files only")

    return parser


def _run_benchmark(args: argparse.Namespace) -> None:
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = run_benchmark(
        pd.read_csv(args.training),
        pd.read_csv(args.scale),
        pd.read_csv(args.calibration),
        pd.read_csv(args.test),
        alpha=args.alpha,
        consecutive=args.consecutive,
        random_state=args.seed,
        methods=tuple(args.methods),
    )
    summary_path = output / "benchmark_metrics_by_station.csv"
    cycles_path = output / "benchmark_cycle_results.csv"
    scores_path = output / "benchmark_sample_scores.csv"
    thresholds_path = output / "benchmark_thresholds.json"
    config_path = output / "benchmark_config.json"
    result.summary.to_csv(summary_path, index=False)
    result.cycle_metrics.to_csv(cycles_path, index=False)
    result.sample_scores.to_csv(scores_path, index=False)
    thresholds_path.write_text(json.dumps(result.thresholds, indent=2), encoding="utf-8")

    def file_sha256(path: str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def package_version(distribution: str) -> str | None:
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            return None

    method_parameters = {
        "global_robust": {
            "reference": "training median per station/channel",
            "spread": "scale-partition residual MAD",
            "bins": 1,
            "scale_floor_pct": 0.10,
        },
        "phase_binned_robust": {
            "reference": "training median per station/channel/progress bin",
            "spread": "scale-partition residual MAD",
            "bins": 20,
            "minimum_samples_per_bin": 15,
            "scale_floor_pct": 0.10,
        },
        "isolation_forest": {
            "n_estimators": 200,
            "max_samples": "auto",
            "contamination": "auto",
            "features": ["progress", *[f"current_j{i}_pct" for i in range(1, 7)]],
        },
        "local_outlier_factor": {
            "mode": "novelty",
            "n_neighbors": "min(20, training_samples_per_station - 1)",
            "contamination": "auto",
            "features": ["progress", *[f"current_j{i}_pct" for i in range(1, 7)]],
        },
        "one_class_svm": {
            "kernel": "rbf",
            "gamma": "scale",
            "nu": 0.05,
            "features": ["progress", *[f"current_j{i}_pct" for i in range(1, 7)]],
        },
        "gpr_phase_aware": {
            "gpr_bins": 40,
            "minimum_scale_samples_per_bin": 25,
            "max_training_points_per_joint": 400,
            "scale_floor_pct": 0.10,
            "optimizer_restarts": 0,
        },
    }
    config = {
        "package_version": __version__,
        "python_version": platform.python_version(),
        "dependency_versions": {
            name: package_version(name)
            for name in ("numpy", "pandas", "scikit-learn", "scipy", "matplotlib")
        },
        "alpha": args.alpha,
        "consecutive": args.consecutive,
        "seed": args.seed,
        "methods": list(args.methods),
        "method_parameters": {name: method_parameters[name] for name in args.methods},
        "input_partitions": {
            "training": {"filename": Path(args.training).name, "sha256": file_sha256(args.training)},
            "scale": {"filename": Path(args.scale).name, "sha256": file_sha256(args.scale)},
            "calibration": {"filename": Path(args.calibration).name, "sha256": file_sha256(args.calibration)},
            "test": {"filename": Path(args.test).name, "sha256": file_sha256(args.test)},
        },
        "test_partition_used_for_fitting_or_calibration": False,
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("Benchmark summary (station-specific):")
    print(result.summary.to_string(index=False))
    print(f"Saved: {summary_path}")
    print(f"Saved: {cycles_path}")
    print(f"Saved: {scores_path}")
    print(f"Saved: {thresholds_path}")
    print(f"Saved: {config_path}")

    if not args.no_plots:
        paths = plot_benchmark_summary(result.summary, output)
        print(f"Saved: {paths['far_per_1000_cycles']}")
        print(f"Saved: {paths['pod']}")
        gpr_anomalies = result.sample_scores[
            (result.sample_scores["method"] == "gpr_phase_aware")
            & (result.sample_scores["label"] == 1)
        ]
        if not gpr_anomalies.empty:
            first = gpr_anomalies.iloc[0]
            cycle_path = output / "cycle_diagnostic_gpr_phase_aware.png"
            plot_cycle_diagnostics(
                result.sample_scores,
                method="gpr_phase_aware",
                station_id=str(first["station_id"]),
                cycle_id=str(first["cycle_id"]),
                output_path=cycle_path,
            )
            print(f"Saved: {cycle_path}")

    print("\nInterpretation: this benchmark is only as representative as its input data.")
    print("Synthetic results are software demonstrations, not industrial performance evidence.")


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "make-synthetic":
        files = make_synthetic_dataset(args.output, seed=args.seed)
        for name, path in files.items():
            print(f"{name}: {path}")
        return

    if args.command == "fit":
        config = DetectorConfig(alpha=args.alpha, consecutive=args.consecutive)
        detector = PhaseAwareGPRDetector(config)
        detector.fit(
            pd.read_csv(args.training), pd.read_csv(args.scale), pd.read_csv(args.calibration)
        )
        target = Path(args.model_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        detector.save(str(target))
        print(f"Saved calibrated detector to {target}")
        print(f"Thresholds: {detector.thresholds_}")
        return

    if args.command == "evaluate":
        detector = PhaseAwareGPRDetector.load(args.model)
        result = evaluate(detector, pd.read_csv(args.test))
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(target, index=False)
        print(result.to_string(index=False))
        print(f"Saved metrics to {target}")
        return

    if args.command == "benchmark":
        _run_benchmark(args)


if __name__ == "__main__":
    main()
