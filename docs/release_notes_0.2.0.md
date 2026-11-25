# Release notes — 0.2.0

Version 0.2.0 is a research-prototype update focused on score calibration hygiene and
reproducibility.

## Method changes

- Per-channel residuals are now centered by the median residual learned from the
  separate normal-only scale partition, within each movement-progress bin.
- Robust MAD scales remain progress-conditioned and use a positive scale floor.
- Training, scale, and calibration partitions must contain the same station set and
  disjoint `(station_id, cycle_id)` pairs.
- A cycle must have one consistent label, and supplied timestamps cannot decrease
  as progress increases. Cycles shorter than the consecutive-run length are rejected.

## Reproducibility and maintenance

- Synthetic anomalies now vary polarity as well as onset and shape.
- A Windows PowerShell script runs the complete synthetic example. Generated CSVs,
  fitted models, and metrics are ignored by Git to reduce accidental data publication.
- GitHub Actions tests Python 3.10–3.13, runs the unit tests and Ruff, and uses
  read-only repository permissions.
- Package metadata uses SPDX license expression `MIT`.

## Compatibility

The residual-scoring definition changed. Do not reuse serialized model objects created
with version 0.1.x; retrain and recalibrate them with version 0.2.0.

## Validation performed for this release

- 17 local unit tests passed.
- Python source and test files compiled successfully.
- Editable package metadata/install check passed with the local build toolchain.
- The bundled synthetic generate → fit → evaluate CLI workflow completed.
- The synthetic test produced false alarms as well as detections; see
  [`synthetic_demo.md`](synthetic_demo.md). These results are not an industrial benchmark.
