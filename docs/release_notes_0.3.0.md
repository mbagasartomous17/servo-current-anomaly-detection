# Release notes — 0.3.0

Version 0.3.0 adds a reproducible comparison harness and diagnostic plots.

## Highlights

- Six methods are compared under the same cycle-disjoint partitions and alarm rule.
- FAR and POD are summarized separately by station with exact binomial intervals.
- Benchmark output includes summary metrics, cycle decisions, sample scores, thresholds,
  configuration, FAR/POD plots, and a representative cycle diagnostic.
- Detection delay is computed only from explicit `event_onset_time_ms` ground truth.

## Compatibility

The input schema adds the optional `event_onset_time_ms` column. Existing datasets
without this column remain supported; detection latency is left empty when onset labels
are unavailable.

## Limitations

This is still Alpha research software. The included benchmark and plots use synthetic
signals only. They do not demonstrate superiority, real-world fault coverage, or safety.
