import pandas as pd
import pytest

from servo_current_detection.schema import DataValidationError, JOINTS, validate_frame


def sample_frame():
    values = {joint: [1.0, 2.0] for joint in JOINTS}
    values.update({"cycle_id": ["c1", "c1"], "station_id": ["station_a"] * 2,
                   "progress": [0.0, 1.0], "label": [0, 0]})
    return pd.DataFrame(values)


def test_validate_frame_sorts_and_accepts_documented_schema():
    result = validate_frame(sample_frame())
    assert list(result.columns).count("progress") == 1
    assert len(result) == 2


def test_validate_frame_rejects_progress_outside_unit_interval():
    frame = sample_frame()
    frame.loc[0, "progress"] = 1.1
    with pytest.raises(DataValidationError):
        validate_frame(frame)


def test_validate_frame_rejects_invalid_labels():
    frame = sample_frame()
    frame.loc[0, "label"] = 3
    with pytest.raises(DataValidationError):
        validate_frame(frame)


def test_validate_frame_rejects_inconsistent_cycle_labels():
    frame = sample_frame()
    frame.loc[1, "label"] = 1
    with pytest.raises(DataValidationError, match="constant within"):
        validate_frame(frame)


def test_validate_frame_rejects_decreasing_time_with_progress():
    frame = sample_frame()
    frame["time_ms"] = [10.0, 5.0]
    with pytest.raises(DataValidationError, match="non-decreasing"):
        validate_frame(frame)
