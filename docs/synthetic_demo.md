# Synthetic demo result (illustrative only)

This report records one run of the bundled deterministic generator using seed `2026`,
version `0.2.0`, and exploratory conformal level `alpha=0.05`. Each station had 60
normal test cycles and 60 synthetic anomaly test cycles. The synthetic generator varies
anomaly polarity, onset, and waveform shape. Each sample is 4 ms apart in this example.

| Station | Normal cycles | False alarms | FAR / 1,000 cycles | 95% FAR interval / 1,000 | Synthetic anomaly cycles | Detected | POD | 95% POD interval | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| station_a | 60 | 5 | 83.3 | 27.6–183.9 | 60 | 60 | 100% | 94.0–100% | 174 ms |
| station_b | 60 | 3 | 50.0 | 10.4–139.2 | 60 | 60 | 100% | 94.0–100% | 164 ms |

These values show why a single headline percentage is insufficient: despite detecting all
synthetic anomalies in this run, the detector also raised false alarms on normal synthetic
cycles. The confidence intervals are wide because the example contains few independent
cycles.

**Interpretation limit:** this is a software smoke demonstration on artificial signals.
It is not a benchmark against a real robot, does not validate the synthetic fault physics,
and must not be cited as evidence of field performance or safety. Real-data evaluation
requires authorization, independent time-based partitions, ground-truth labels, and
uncertainty reporting.

Reproduce it with `examples/run_synthetic_demo.ps1` on Windows PowerShell or with the
manual commands in the main README.
