# Benchmarking and visualization

## Objective

Version 0.3.0 adds a fixed-split comparison harness. It is intended to make the
comparison between the phase-aware GPR detector and simpler or multivariate baselines
reproducible. It is not designed to identify a universally best detector.

## Methods

| Identifier | Method | Fit data | Input features |
|---|---|---|---|
| `global_robust` | Global median/MAD envelope | Training reference + scale residuals | Six current channels; no progress conditioning |
| `phase_binned_robust` | Progress-binned median/MAD envelope | Training reference + scale residuals | Six current channels conditioned on progress bins |
| `isolation_forest` | Isolation Forest | Training only | Progress + six current channels |
| `local_outlier_factor` | LOF novelty mode | Training only | Progress + six current channels |
| `one_class_svm` | RBF One-Class SVM | Training only | Progress + six current channels |
| `gpr_phase_aware` | GPR per station/channel with robust residual centering/scaling | Training + scale | Progress-conditioned current reference for each channel |

The robust baselines are intended as transparent references. Isolation Forest, LOF, and
One-Class SVM are fitted separately per station after robust feature scaling. These
models produce multivariate scores but do not claim per-joint causal attribution; their
`most_affected_joint` field is therefore left empty.

## Shared decision protocol

Every method receives the same four cycle-disjoint partitions:

- **Training:** normal-only data used to fit the method.
- **Scale:** normal-only data used by GPR and the robust-envelope baselines to estimate
  residual dispersion or local spread.
- **Calibration:** normal-only data used to calibrate each method's cycle threshold.
- **Test:** labelled normal/anomalous cycles used only for evaluation.

For each sample, each method returns an anomaly score where larger means more unusual.
For each normal calibration cycle, the cycle score is the maximum across all sliding
windows of the minimum score in that window. The finite-sample split-conformal quantile
is then calculated separately for each station. At inference, an alarm is raised at the
first sample ending a run of `consecutive` scores strictly above that station's
threshold.

The benchmark refuses cycle overlap among partitions and rejects non-normal fitting
partitions. The test partition is never used to fit models or select thresholds.

## Metrics

- **FAR / 1,000 normal cycles:** false-alarmed normal test cycles divided by normal test
  cycles, multiplied by 1,000.
- **POD:** anomalous test cycles with an alarm at or after the annotated onset divided
  by all labelled anomalous test cycles. An alarm that occurs before the onset is
  recorded separately as a pre-onset alarm and does not count as a successful detection.
- **Uncertainty:** two-sided exact Clopper–Pearson binomial intervals for FAR and POD.
- **Pre-onset alarms:** alarms on labelled anomalous cycles that occur before the
  annotated event onset. They are reported separately and excluded from POD.
- **Median detection delay:** first eligible alarm time at or after `event_onset_time_ms`
  minus that onset, calculated only when an explicit onset annotation is available. No
  onset is inferred from cycle start.

The confidence intervals quantify binomial sampling uncertainty only. They do not
account for temporal dependence, changing operating conditions, or imperfect labels.

## Reproduce the default synthetic benchmark

Install the package with visualization support:

```bash
python -m pip install -e ".[dev,viz]"
```

Generate the data and run the benchmark:

```bash
servo-current-detector make-synthetic --output examples/synthetic_data --seed 2026

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

Windows PowerShell users can execute `examples/run_synthetic_demo.ps1`.

## One deterministic synthetic run

The default generator creates two synthetic stations, with 60 normal and 60 anomalous
test cycles per station. The seed is 2026 and the exploratory calibration level is
`alpha=0.05`. A run in the development environment produced the following results:

| Method | Station | False alarms / 60 normal | Pre-onset alarms / 60 anomalies | FAR / 1,000 | Detected after onset / 60 | POD | Median delay (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| Global robust | A | 4 | 4 | 66.7 | 56 | 93.3% | 98 |
| Global robust | B | 3 | 3 | 50.0 | 57 | 95.0% | 104 |
| Progress-binned robust | A | 3 | 0 | 50.0 | 60 | 100% | 48 |
| Progress-binned robust | B | 2 | 0 | 33.3 | 60 | 100% | 40 |
| Isolation Forest | A | 2 | 0 | 33.3 | 60 | 100% | 92 |
| Isolation Forest | B | 3 | 5 | 50.0 | 53 | 88.3% | 112 |
| LOF novelty | A | 4 | 2 | 66.7 | 58 | 96.7% | 40 |
| LOF novelty | B | 0 | 1 | 0.0 | 59 | 98.3% | 44 |
| One-Class SVM | A | 2 | 1 | 33.3 | 59 | 98.3% | 52 |
| One-Class SVM | B | 1 | 2 | 16.7 | 58 | 96.7% | 58 |
| Phase-aware GPR | A | 5 | 0 | 83.3 | 60 | 100% | 40 |
| Phase-aware GPR | B | 3 | 1 | 50.0 | 59 | 98.3% | 36 |

These are illustrative software demonstration results, not a real-world benchmark. The
normal test sample per station is only 60 cycles, so FAR confidence intervals are
wide. Some models generated alerts before the labelled synthetic event onset; these are
reported separately and excluded from POD. In this run, pre-onset alerts range from zero
to five per 60 synthetic anomalies, and post-onset POD varies from 88.3% to 100%.
These results do not demonstrate detector superiority or establish that the synthetic
disturbances reproduce physical insertion failures.

## Plots

The benchmark creates FAR and POD comparison plots with exact confidence intervals,
and a representative GPR cycle diagnostic with six current traces, the normalized
anomaly score, the calibrated threshold, alarm sample, and synthetic event onset.

The checked-in figures under `docs/assets/` are snapshots from the deterministic
synthetic run above. Re-running the command regenerates outputs under the selected
results directory.

## Interpretation cautions

- Compare FAR and POD together. A high POD by itself is not sufficient.
- Do not pool station-level results unless the pooling estimand is pre-specified.
- Do not tune the methods using the labelled test partition.
- Synthetic injection only tests the specified shapes, amplitude range, and onset
  distribution. It is not evidence of coverage for all mechanical or process faults.
- At `alpha=0.001`, at least 999 independent normal calibration cycles per station are
  needed for a finite split-conformal threshold. The bundled demo uses `alpha=0.05` only
  to keep the example small and quick.
- For real industrial evaluation, obtain data-owner approval, define independent
  ground-truth events, split by time/day at cycle level, and preserve raw data securely.
