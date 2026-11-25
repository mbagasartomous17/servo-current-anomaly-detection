import pytest

from servo_current_detection.metrics import clopper_pearson


def test_clopper_pearson_bounds_zero_false_alarms():
    lower, upper = clopper_pearson(0, 100)
    assert lower == 0.0
    assert 0.0 < upper < 0.1


def test_clopper_pearson_all_successes():
    lower, upper = clopper_pearson(10, 10)
    assert 0.0 < lower < 1.0
    assert upper == 1.0


def test_clopper_pearson_rejects_invalid_counts():
    with pytest.raises(ValueError):
        clopper_pearson(11, 10)
