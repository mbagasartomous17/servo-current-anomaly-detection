"""Command-line interface for synthetic examples and model evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .metrics import evaluate
from .model import DetectorConfig, PhaseAwareGPRDetector
from .synthetic import make_synthetic_dataset


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

    test = commands.add_parser("evaluate", help="evaluate a calibrated detector")
    test.add_argument("--model", required=True)
    test.add_argument("--test", required=True)
    test.add_argument("--output", default="results/metrics.csv")
    return parser


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


if __name__ == "__main__":
    main()
