# Contributing

Contributions are welcome. Please open an issue before substantial changes so the
scientific scope, data assumptions, and evaluation protocol can be discussed first.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev,viz]"
pytest
ruff check src tests
```

## Reproduce the synthetic benchmark

```bash
servo-current-detector make-synthetic --output examples/synthetic_data --seed 2026
servo-current-detector benchmark \
  --training examples/synthetic_data/training.csv \
  --scale examples/synthetic_data/scale.csv \
  --calibration examples/synthetic_data/calibration.csv \
  --test examples/synthetic_data/test.csv \
  --output-dir results/benchmark --alpha 0.05 --consecutive 3 --seed 2026
```

## Contribution principles

- Do not submit proprietary telemetry, robot programs, controller exports, IP
  addresses, credentials, operator identifiers, CCTV, or other restricted data.
- Use synthetic or independently licensed datasets in examples and tests.
- Keep training, scale, calibration, and test partitions separate at the whole-cycle
  level. Never tune thresholds or model choices on test outcomes.
- Benchmark competing methods with the same input partitions and cycle decision rule.
- Document method-specific fit data and assumptions. A method that does not use the
  scale partition should say so explicitly.
- Report negative results, confidence intervals, sample counts, and limitations; do not
  make unsupported performance claims.
- Add tests for new algorithms, input fields, metrics, and plots.
