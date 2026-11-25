"""Input schema and validation helpers."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

JOINTS = tuple(f"current_j{i}_pct" for i in range(1, 7))
REQUIRED_COLUMNS = ("cycle_id", "station_id", "progress", *JOINTS)
OPTIONAL_COLUMNS = ("label", "time_ms", "event_onset_time_ms")


class DataValidationError(ValueError):
    """Raised when an input table does not satisfy the documented schema."""


def validate_frame(
    frame: pd.DataFrame,
    *,
    name: str = "data",
    require_label: bool = False,
) -> pd.DataFrame:
    """Validate a signal table and return a defensive copy.

    `progress` must be a normalized movement-progress coordinate in [0, 1].
    Current channels are numeric percentages of their respective rated current.
    """
    if not isinstance(frame, pd.DataFrame):
        raise DataValidationError(f"{name} must be a pandas DataFrame")
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if require_label and "label" not in frame.columns:
        missing.append("label")
    if missing:
        raise DataValidationError(f"{name} is missing required columns: {missing}")
    if frame.empty:
        raise DataValidationError(f"{name} is empty")

    result = frame.copy()
    if result[["cycle_id", "station_id"]].isna().any().any():
        raise DataValidationError(f"{name} contains missing cycle_id or station_id values")

    numeric = ["progress", *JOINTS]
    if "time_ms" in result.columns:
        numeric.append("time_ms")
    for col in numeric:
        result[col] = pd.to_numeric(result[col], errors="coerce")
        if not np.isfinite(result[col].to_numpy(dtype=float)).all():
            raise DataValidationError(f"{name}.{col} contains non-numeric or non-finite values")
    if "event_onset_time_ms" in result.columns:
        result["event_onset_time_ms"] = pd.to_numeric(
            result["event_onset_time_ms"], errors="coerce"
        )
        onset = result["event_onset_time_ms"].to_numpy(dtype=float)
        if np.isinf(onset).any():
            raise DataValidationError(f"{name}.event_onset_time_ms contains infinite values")
        if "time_ms" not in result.columns or "label" not in result.columns:
            raise DataValidationError(
                f"{name}.event_onset_time_ms requires both time_ms and label columns"
            )

    progress = result["progress"].to_numpy(dtype=float)
    if np.any((progress < 0.0) | (progress > 1.0)):
        raise DataValidationError(f"{name}.progress must be within [0, 1]")

    if "label" in result.columns:
        result["label"] = pd.to_numeric(result["label"], errors="coerce")
        if result["label"].isna().any() or not set(result["label"].unique()).issubset({0, 1}):
            raise DataValidationError(f"{name}.label must contain only 0 (normal) or 1 (anomaly)")
        result["label"] = result["label"].astype(int)

    duplicated = result.duplicated(["cycle_id", "station_id", "progress"])
    if duplicated.any():
        raise DataValidationError(
            f"{name} contains duplicate cycle_id/station_id/progress rows"
        )

    result = result.sort_values(
        ["station_id", "cycle_id", "progress"], kind="stable"
    ).reset_index(drop=True)

    grouped = result.groupby(["station_id", "cycle_id"], sort=False, dropna=False)
    if "label" in result.columns and (grouped["label"].nunique(dropna=False) > 1).any():
        raise DataValidationError(
            f"{name}.label must be constant within each station_id/cycle_id"
        )
    if "time_ms" in result.columns:
        non_monotonic = grouped["time_ms"].apply(
            lambda values: bool((values.diff().dropna() < 0).any())
        )
        if non_monotonic.any():
            raise DataValidationError(
                f"{name}.time_ms must be non-decreasing with progress within each cycle"
            )
    if "event_onset_time_ms" in result.columns:
        for (station, cycle_id), cycle in grouped:
            onset = cycle["event_onset_time_ms"].dropna().unique()
            label = int(cycle["label"].iloc[0])
            if label == 1 and (
                len(onset) != 1 or cycle["event_onset_time_ms"].isna().any()
            ):
                raise DataValidationError(
                    f"{name}.event_onset_time_ms must contain one consistent onset "
                    f"on every row of anomalous cycle {(station, cycle_id)}"
                )
            if label == 0 and len(onset) != 0:
                raise DataValidationError(
                    f"{name}.event_onset_time_ms must be empty for normal cycle "
                    f"{(station, cycle_id)}"
                )
            # Do not require onset to fall inside the supplied time window: callers
            # may validate a deliberately cropped cycle window, where the annotated
            # event onset can be outside the retained samples.
    return result


def normal_only(frame: pd.DataFrame, *, name: str) -> pd.DataFrame:
    """Return normal rows; reject anomalous rows in model-fitting partitions."""
    if "label" not in frame.columns:
        return frame
    if (frame["label"] != 0).any():
        raise DataValidationError(f"{name} must contain normal-only cycles (label == 0)")
    return frame


def cycle_groups(frame: pd.DataFrame) -> Iterable[tuple[tuple[str, str], pd.DataFrame]]:
    """Yield cycles grouped by station and cycle identifier."""
    return frame.groupby(["station_id", "cycle_id"], sort=False, dropna=False)
