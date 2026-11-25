# Roadmap

## Completed in 0.3.0

- Fixed-split benchmark harness for robust and multivariate novelty baselines.
- Common cycle-level conformal calibration and consecutive-sample alarm rule.
- Cycle-level FAR/POD metrics with exact confidence intervals.
- Diagnostic and benchmark plots; reproducible synthetic run.
- Explicit onset annotations for detection-delay calculations.

## Candidate next steps

- Add configurable, pre-registered fault families and severity strata to the synthetic benchmark.
- Add benchmark result manifests with hashes of the four input partitions.
- Add optional time-series baselines after agreeing a common windowing and calibration protocol.
- Add a public, independently licensed real-data example only if data rights and labels are clear.
- Add performance profiling for memory and training/inference time on larger datasets.

## Research constraints

- Do not claim synthetic injection represents all physical fault mechanisms.
- Keep calibration and test partitions independent.
- Report negative results and uncertainty rather than promoting a single headline POD.
- Do not publish private telemetry, company identifiers, controller settings, or production logs.
