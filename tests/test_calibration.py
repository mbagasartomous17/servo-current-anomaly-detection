import numpy as np
import pytest

from servo_current_detection.calibration import conformal_quantile, cycle_run_score


def test_conformal_quantile_uses_finite_sample_rank():
    assert conformal_quantile(np.arange(9.0), alpha=0.2) == 7.0


def test_conformal_quantile_is_infinite_when_calibration_set_is_too_small():
    assert np.isinf(conformal_quantile(np.arange(100.0), alpha=0.001))


def test_conformal_quantile_rejects_invalid_alpha():
    with pytest.raises(ValueError):
        conformal_quantile(np.arange(5.0), alpha=1.0)


def test_cycle_run_score_requires_consecutive_high_samples():
    assert cycle_run_score(np.array([0.0, 4.0, 5.0, 6.0, 0.0]), consecutive=3) == 4.0
    assert cycle_run_score(np.array([4.0, 5.0]), consecutive=3) == float("-inf")
