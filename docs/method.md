# Method overview

## Intended problem

Many cyclic electromechanical movements have a repeatable current signature that
changes with movement progress. A single global current threshold can confuse normal
position-dependent variation with an abnormal event. This package demonstrates a
position-conditioned reference model using Gaussian Process Regression (GPR).

## Pipeline

1. Fit one GPR regressor per station and current channel using normal training cycles.
2. Estimate the median residual center and robust residual dispersion in progress bins
   using a separate normal-only scale partition. The scale is
   `max(1.4826 * MAD, scale_floor_pct)`. Sparse bins fall back to global robust
   residual statistics.
3. For sample progress `p` and channel `j`, calculate
   `z_j(p) = abs(r_j(p) - m_j(p)) / s_j(p)`, where `r_j` is the observed-minus-predicted
   residual, `m_j` is the median residual center, and `s_j` is the robust MAD scale
   (with a positive floor). The sample score is `max_j z_j(p)`. This avoids treating
   a stable local model bias as an anomaly.
4. Summarize each normal calibration cycle by the maximum value of the minimum score
   in each `consecutive`-sample window.
5. Calibrate a finite-sample split-conformal threshold independently per station.
   Every calibration cycle must contain at least as many samples as the configured
   consecutive-run length; shorter cycles are rejected rather than assigned an
   artificial negative-infinite score.
6. At inference, raise one cycle alarm at the first run of `consecutive` samples above
   the calibrated threshold. The highest-scoring channel is reported for triage.

## Statistical caveats

- The conformal guarantee relies on exchangeability between calibration and future
  normal cycles within each station. Distribution shift, temporal dependence, and
  nonstationary process conditions can invalidate the nominal false-alarm level.
- The scale partition is separate from both GPR training and threshold calibration.
- The implementation rejects any `(station_id, cycle_id)` appearing in more than one
  fitting partition. It also rejects inconsistent labels or decreasing timestamps
  within a cycle.
- At `alpha=0.001`, at least 999 calibration cycles per station are needed for a
  finite split-conformal order statistic. With fewer cycles, the implementation
  intentionally returns an infinite threshold rather than claiming unsupported tail
  calibration. Use a larger alpha only for exploratory demonstrations and report it.
- GPR uses an exact kernel method. The number of training points is capped and
  stratified across progress bins to limit cubic-time fitting cost.
- Synthetic fault injection is a controlled sensitivity experiment. The included
  generator varies anomaly direction and shape, but these patterns are not proof that
  the data reproduce real mechanical contact or failure physics.
- The maximum normalized channel score is a simple transparent fusion rule. Compare
  it with other baselines before making claims about superiority.
- Version 0.2.0 changes residual scoring by centering each progress-bin residual on
  the median learned from the scale partition. Refit models created with version 0.1.x.
- FAR and probability of detection (POD) are reported with exact two-sided
  Clopper-Pearson binomial confidence intervals. These intervals quantify binomial
  sampling uncertainty; they do not correct temporal dependence or distribution shift.

## What this implementation does not claim

It does not prove detection performance on a real industrial process, estimate contact
force, identify mechanical root cause, or control/stop a robot. Real-world claims
require independently authorized data, ground-truth labels, time-separated testing,
confidence intervals, and review by qualified engineers.


## Benchmark comparisons (version 0.3.0)

The benchmark module compares the GPR reference with global robust, progress-binned
robust, Isolation Forest, LOF novelty, and One-Class SVM baselines. All methods use the
same training, scale, calibration, and test partitions and the same cycle-level
consecutive-sample decision rule. Calibration thresholds are computed separately for
each method and station. See [`benchmarking.md`](benchmarking.md) for the exact
protocol, metrics, and synthetic example.
