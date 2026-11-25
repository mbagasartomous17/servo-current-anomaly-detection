"""Finite-sample conformal threshold calibration."""

from __future__ import annotations

import math

import numpy as np


def conformal_quantile(scores: np.ndarray, alpha: float = 0.001) -> float:
    """Return a split-conformal upper quantile.

    If the calibration set is too small for the requested alpha, return +inf.
    This is intentionally conservative: it avoids pretending that a tail
    probability can be calibrated with insufficient normal calibration cycles.
    """
    values = np.asarray(scores, dtype=float).reshape(-1)
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1")
    if values.size == 0:
        raise ValueError("scores must not be empty")
    if not np.isfinite(values).all():
        raise ValueError("scores must be finite")

    rank_1based = math.ceil((values.size + 1) * (1.0 - alpha))
    if rank_1based > values.size:
        return float("inf")
    return float(np.partition(values, rank_1based - 1)[rank_1based - 1])


def cycle_run_score(sample_scores: np.ndarray, consecutive: int = 3) -> float:
    """Summarize a cycle by its strongest run of `consecutive` high scores."""
    values = np.asarray(sample_scores, dtype=float).reshape(-1)
    if consecutive < 1:
        raise ValueError("consecutive must be >= 1")
    if values.size < consecutive:
        return float("-inf")
    windows = np.lib.stride_tricks.sliding_window_view(values, consecutive)
    return float(np.max(np.min(windows, axis=1)))
