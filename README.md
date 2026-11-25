# Servo Current Anomaly Detection

A small, research-oriented Python toolkit (current release: **0.2.0**) for **phase-aware anomaly detection in
multichannel servo motor current signals**. It demonstrates a transparent baseline:
one Gaussian Process Regression (GPR) model per current channel, robust residual
scaling by movement progress, and a split-conformal cycle threshold.

> **Research prototype only.** This package is not a safety system, robot controller,
> collision detector, or production-ready alarm. It does not send commands to hardware.

## Why this project exists

A servo-current waveform can vary naturally over the course of a movement. A single
global threshold may therefore be too crude: the same current value can be normal at
one point in a trajectory and unusual at another. This toolkit models the expected
current as a function of normalized movement progress and scores deviations from that
reference.

The code is intentionally process-agnostic. It contains no industrial telemetry,
company identifiers, controller addresses, robot programs, proprietary parameters,
or private production records.

## Features

- Six-channel example schema (`current_j1_pct` … `current_j6_pct`).
- Separate normal-only partitions for GPR fitting, residual-scale estimation, and
  conformal threshold calibration.
- Position/progress-binned robust residual scale based on median absolute deviation.
- Per-station finite-sample conformal thresholds.
- Consecutive-sample alarm rule and highest-scoring channel localization.
- Synthetic signal generator and cycle-level FAR/POD/detection-latency evaluation.
- Unit tests and GitHub Actions workflow.

## Install

Python 3.10 or newer is required.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Quick start: synthetic data only

Generate four independent partitions:

```bash
servo-current-detector make-synthetic --output examples/synthetic_data
```

On Windows PowerShell, the complete synthetic walkthrough can also be run with:

```powershell
.\examples\run_synthetic_demo.ps1
```

Fit and calibrate an exploratory model:

```bash
servo-current-detector fit \
  --training examples/synthetic_data/training.csv \
  --scale examples/synthetic_data/scale.csv \
  --calibration examples/synthetic_data/calibration.csv \
  --model-out artifacts/demo_detector.joblib \
  --alpha 0.05
```

Evaluate the labelled synthetic test partition:

```bash
servo-current-detector evaluate \
  --model artifacts/demo_detector.joblib \
  --test examples/synthetic_data/test.csv \
  --output results/synthetic_metrics.csv
```

The synthetic tutorial uses `alpha=0.05` because its calibration sample is small.
This is **not** the recommended setting for a high-reliability industrial study. The
project's stringent research configuration may use `alpha=0.001`, which requires at
least 999 independent normal calibration cycles per station to obtain a finite
split-conformal threshold. The code returns an infinite threshold when the calibration
partition is too small; it does not silently lower the statistical requirement.

## Input data

See [`docs/data_format.md`](docs/data_format.md) for the complete schema. Each row is
one sample; `progress` is normalized to `[0, 1]`; six current columns are expressed
as percentages of their respective rated current. `label` is optional for fitting
partitions and required for evaluation.

Before using real data:

1. Obtain written authorization for data use and publication.
2. Remove company, machine, program, controller, network, operator, and production
   identifiers unless explicitly authorized.
3. Split whole days or time blocks into training, scale, calibration, and test sets.
   Keep every sample from a cycle in exactly one partition.
4. Fit all preprocessing and model settings without looking at test outcomes.
5. Report false alarms per cycle, POD by injected/separately labelled fault level,
   detection latency, uncertainty intervals, and the number of independent cycles.
6. Preserve negative results and clearly label synthetic experiments.

## Method and limitations

Read [`docs/method.md`](docs/method.md) before interpreting results. One reproducible
synthetic run is documented in [`docs/synthetic_demo.md`](docs/synthetic_demo.md); it
includes false alarms as well as detections and is explicitly not an industrial benchmark. In particular,
conformal calibration assumes exchangeability of normal cycles; changes in tooling,
loads, speed, trajectory, temperature, or maintenance state may invalidate the
nominal false-alarm level. Synthetic fault injection measures sensitivity to the
specified synthetic patterns only.

## Development

```bash
pytest
```

Contributions should use synthetic or independently licensed data. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).

## Project status

**Alpha research software — version 0.2.0.** This release centers residuals by the
local median learned from the scale partition. Refit any detector serialized with
version 0.1.x before using it with this release.

The package is a reproducible starting point, not a completed validated detector.
Real-world performance, generalization across machines, and operational safety have
not been established by this repository.
