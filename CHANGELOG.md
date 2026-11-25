# Changelog

## 0.3.0 — 2026-11-25

- Added a fixed-split benchmark harness for global robust, progress-binned robust,
  Isolation Forest, LOF novelty, One-Class SVM, and phase-aware GPR methods.
- Applied a common cycle-level conformal calibration and consecutive-sample alarm rule.
- Added FAR/POD station summaries with exact Clopper–Pearson intervals and per-cycle
  result exports.
- Added sample-level diagnostic plots and benchmark FAR/POD comparison plots.
- Added explicit `event_onset_time_ms` metadata so detection delay is measured from a
  ground-truth event onset rather than cycle start; pre-onset alerts are reported
  separately and excluded from POD.
- Added JSON snapshots of benchmark configuration and calibrated thresholds.
- Expanded CI and tests to cover benchmark and visualization workflows.

## 0.2.1 — 2026-11-25

- Fix six Ruff lint findings so the CI lint step can pass: remove redundant integer casts, sort Gaussian-process kernel imports, and simplify postponed self-referential type annotations.
- No detector behavior or data schema changed from version 0.2.0.

## 0.2.0 — 2026-11-25

- Center normalized residuals by the robust median within each progress bin.
- Reject cycle leakage between training, residual-scale, and calibration partitions.
- Validate cycle-level label consistency and monotonic sample timestamps.
- Expand continuous integration to Python 3.10–3.13 and add lint checks.

## 0.1.0 — 2026-11-25

- Initial research prototype.
- Added progress-conditioned GPR for six current channels.
- Added robust residual scaling and split-conformal calibration.
- Added synthetic data generation, cycle-level metrics, tests, and documentation.
