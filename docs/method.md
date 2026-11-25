# Method overview

## Intended problem

Many cyclic electromechanical movements have a repeatable current signature that
changes with movement progress. A single global current threshold can confuse normal
position-dependent variation with an abnormal event. This package demonstrates a
position-conditioned reference model using Gaussian Process Regression (GPR).

## Pipeline

1. Fit one GPR regressor per station and current channel using normal training cycles.
2. Estimate robust residual dispersion in progress bins using a separate normal-only
   scale partition. The scale is `max(1.4826 * MAD, scale_floor_pct)`.
3. For each sample, calculate the maximum absolute residual divided by its channel's
   local robust scale.
4. Summarize each normal calibration cycle by the maximum value of the minimum score
   in each `consecutive`-sample window.
5. Calibrate a finite-sample split-conformal threshold independently per station.
6. At inference, raise one cycle alarm at the first run of `consecutive` samples above
   the calibrated threshold. The highest-scoring channel is reported for triage.

## Statistical caveats

- The conformal guarantee relies on exchangeability between calibration and future
  normal cycles within each station. Distribution shift, temporal dependence, and
  nonstationary process conditions can invalidate the nominal false-alarm level.
- The scale partition is separate from both GPR training and threshold calibration.
- At `alpha=0.001`, at least 999 calibration cycles per station are needed for a
  finite split-conformal order statistic. With fewer cycles, the implementation
  intentionally returns an infinite threshold rather than claiming unsupported tail
  calibration. Use a larger alpha only for exploratory demonstrations and report it.
- GPR uses an exact kernel method. The number of training points is capped and
  stratified across progress bins to limit cubic-time fitting cost.
- Synthetic fault injection is a controlled sensitivity experiment. It is not proof
  that injected patterns reproduce all real mechanical contact or failure physics.
- The maximum normalized channel score is a simple transparent fusion rule. Compare
  it with other baselines before making claims about superiority.
- FAR and probability of detection (POD) are reported with exact two-sided
  Clopper-Pearson binomial confidence intervals. These intervals quantify binomial
  sampling uncertainty; they do not correct temporal dependence or distribution shift.

## What this implementation does not claim

It does not prove detection performance on a real industrial process, estimate contact
force, identify mechanical root cause, or control/stop a robot. Real-world claims
require independently authorized data, ground-truth labels, time-separated testing,
confidence intervals, and review by qualified engineers.
