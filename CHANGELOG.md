# Changelog

## 0.2.1 — 2026-11-25

- Fix six Ruff lint findings so the CI lint step can pass: remove redundant integer casts, sort Gaussian-process kernel imports, and simplify postponed self-referential type annotations.
- No detector behavior or data schema changed from version 0.2.0.

## 0.2.0 — 2026-11-25

- Center normalized residuals by their robust median within each progress bin.
- Reject cycle leakage between training, residual-scale, and calibration partitions.
- Validate cycle-level label consistency and monotonic sample timestamps.
- Expand continuous integration to Python 3.10–3.13, add linting, caching, and least-privilege permissions.
- Migrate package license metadata to the SPDX expression format.
- Add a Windows PowerShell synthetic demo and reproducible synthetic-result note.
- Exclude generated datasets, models, and metric outputs from Git by default.
- Existing 0.1.x fitted model files must be refitted; the residual-scoring definition changed.

## 0.1.0 — 2026-11-25

- Initial research prototype.
- Added progress-conditioned GPR for six current channels.
- Added robust progress-binned residual scaling and split-conformal calibration.
- Added synthetic data generation, evaluation metrics, tests, and documentation.
