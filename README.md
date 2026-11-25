# Servo Current Anomaly Detection

**Current release: 0.3.0 (Alpha).** A research-oriented Python toolkit for phase-aware
anomaly detection in multichannel servo motor current signals. It includes a GPR
reference detector, transparent robust-envelope baselines, multivariate novelty
baselines, cycle-level conformal calibration, and reproducible visual benchmarking.

> **Research prototype only.** This package is not a safety system, robot controller,
> collision detector, protective stop, or production-ready alarm. It does not send
> commands to hardware.

## Why this project exists

A servo-current waveform can vary naturally over the course of a movement. A single
global threshold may therefore confuse normal position-dependent variation with an
abnormal event. This toolkit provides a progress-conditioned reference and compares it
with simpler and multivariate alternatives under a common cycle-level evaluation rule.

The repository is process-agnostic. It contains synthetic data generation only; it does
not include industrial telemetry, company identifiers, controller addresses, robot
programs, proprietary parameters, or private production records.

## Features

- Six-channel example schema (`current_j1_pct` … `current_j6_pct`).
- Normal-only, cycle-disjoint training, residual-scale, and calibration partitions.
- Phase-aware Gaussian Process Regression (GPR) reference detector.
- Global robust and progress-binned median/MAD envelope baselines.
- Isolation Forest, Local Outlier Factor (novelty mode), and One-Class SVM baselines.
- One shared finite-sample conformal calibration procedure and consecutive-sample
  cycle alarm rule for all benchmark methods.
- Cycle-level FAR and POD with exact Clopper–Pearson confidence intervals.
- Separate reporting of alarms that occur before an annotated fault onset; these do not
  count as successful anomaly detections.
- Explicit event-onset timestamps for correctly defined synthetic detection delay.
- CSV outputs, JSON configuration/threshold snapshots, and Matplotlib plots.
- Synthetic data generation, unit tests, linting, and GitHub Actions across Python
  3.10–3.13.

## Install

Python 3.10 or newer is required. The visualization extra is needed for plots.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,viz]"
```

## Quick start: full synthetic benchmark

Generate reproducible normal-only training, scale, and calibration partitions plus a
labelled test partition:

```bash
servo-current-detector make-synthetic --output examples/synthetic_data --seed 2026
```

Run all six methods on the same partitions:

```bash
servo-current-detector benchmark \
  --training examples/synthetic_data/training.csv \
  --scale examples/synthetic_data/scale.csv \
  --calibration examples/synthetic_data/calibration.csv \
  --test examples/synthetic_data/test.csv \
  --output-dir results/benchmark \
  --alpha 0.05 \
  --consecutive 3 \
  --seed 2026
```

On Windows PowerShell, run the complete demonstration with:

```powershell
.\examples\run_synthetic_demo.ps1
```

The benchmark writes:

| Output | Description |
|---|---|
| `benchmark_metrics_by_station.csv` | FAR, POD, exact confidence intervals, and detection delay per method/station |
| `benchmark_cycle_results.csv` | One decision row per test cycle and method |
| `benchmark_sample_scores.csv` | Sample-level current values, scores, thresholds, and alarm markers |
| `benchmark_thresholds.json` | Calibrated cycle-score threshold per method/station |
| `benchmark_config.json` | Package/dependency versions, method parameters, alpha, seed, test-use declaration, and SHA-256 hashes of the four input files |
| `benchmark_far.png` | FAR comparison with confidence intervals |
| `benchmark_pod.png` | POD comparison with confidence intervals |
| `cycle_diagnostic_gpr_phase_aware.png` | Six current traces and the GPR score/threshold for one synthetic anomaly cycle |

Use `--no-plots` when only CSV and JSON outputs are needed. See
[`docs/benchmarking.md`](docs/benchmarking.md) for method details and interpretation.

## Methods compared

1. **Global robust envelope:** one median/MAD reference per station and current channel.
2. **Progress-binned robust envelope:** median/MAD references conditioned on progress bins.
3. **Isolation Forest:** multivariate novelty score using progress and six current channels.
4. **Local Outlier Factor:** novelty-mode LOF using the same seven features.
5. **One-Class SVM:** RBF novelty model using the same seven features.
6. **Phase-aware GPR:** one progress-conditioned GPR model per station/current channel,
   local residual centering/scaling, and max-channel fusion.

All methods use the same normal-only training and normal-only calibration cycles, the
same labelled test cycles, and the same consecutive-sample cycle alarm rule. Global
and progress-binned robust baselines also use the separate normal-only scale partition.
The multivariate novelty models fit on training samples only. No method is tuned using
test labels or test outcomes.

## Statistical design and data integrity

- Entire `(station_id, cycle_id)` groups must be disjoint across training, scale,
  calibration, and test partitions.
- Training, scale, and calibration partitions must be normal-only.
- Calibration thresholds are computed from one cycle score per normal calibration
  cycle: the maximum, within a cycle, of the minimum score in each consecutive-sample
  window.
- Split-conformal calibration assumes exchangeability of normal cycles. Time dependence,
  process drift, station changes, and distribution shift can invalidate the nominal
  false-alarm interpretation.
- At `alpha=0.001`, at least 999 independent calibration cycles per station are needed
  for a finite split-conformal order statistic. The bundled demo uses `alpha=0.05`
  because its calibration partition is intentionally small.
- Detection delay is measured from an explicit `event_onset_time_ms` annotation. The
  software does not label cycle-start-to-alarm time as fault-detection latency.
- Confidence intervals are exact binomial intervals; they do not correct dependence
  among cycles or distribution shift.

## Input data

See [`docs/data_format.md`](docs/data_format.md). Each row is one sample. `progress` is
normalized to `[0, 1]`; current channels are percentages of their respective rated
current. `label` is 0 for normal cycles and 1 for anomalous cycles. For meaningful
latency, provide a cycle-constant `event_onset_time_ms` for anomalous cycles and leave it
empty for normal cycles.

Before using real data:

1. Obtain written authorization for data use and publication.
2. Remove company, site, machine, process, program, controller, network, operator, and
   production identifiers unless their release is explicitly authorized.
3. Split whole days or independent time blocks into partitions before model fitting.
4. Fit preprocessing and model settings without looking at final test outcomes.
5. Report FAR, POD, confidence intervals, event definition, detection delay, and the
   number of independent cycles together.
6. Preserve negative results and clearly distinguish synthetic from measured data.

## Development

```bash
python -m pip install -e ".[dev,viz]"
pytest
ruff check src tests
```

Contributions should use synthetic or independently licensed data. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).

## License and citation

MIT. See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).

## Project status

**Alpha research software — version 0.3.0.** The benchmark and plots demonstrate
reproducible software workflows on artificial signals. They do not establish detector
superiority, real-world fault coverage, cross-machine generalization, or operational
safety. Validation on authorized, independently labelled industrial data remains open.
