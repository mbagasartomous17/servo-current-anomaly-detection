"""Fair, cycle-level comparison of transparent and multivariate anomaly baselines.

All methods use the same normal-only training/scale/calibration partitions, the same
six current channels, and the same cycle-level consecutive-sample decision rule.
The final test partition is used only for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler
from sklearn.svm import OneClassSVM

from .calibration import conformal_quantile, cycle_run_score
from .metrics import evaluate_predictions
from .model import DetectorConfig, PhaseAwareGPRDetector
from .schema import JOINTS, cycle_groups, normal_only, validate_frame

METHODS = (
    "global_robust",
    "phase_binned_robust",
    "isolation_forest",
    "local_outlier_factor",
    "one_class_svm",
    "gpr_phase_aware",
)


@dataclass
class BenchmarkResult:
    """Outputs from one fixed-split benchmark run."""

    summary: pd.DataFrame
    cycle_metrics: pd.DataFrame
    sample_scores: pd.DataFrame
    thresholds: dict[str, dict[str, float]]


def _feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    return frame[["progress", *JOINTS]].to_numpy(dtype=float)


def _cycle_score_table(scores: pd.DataFrame, consecutive: int) -> pd.DataFrame:
    rows: list[dict[str, str | float]] = []
    for (station, cycle_id), group in cycle_groups(scores):
        rows.append({
            "station_id": str(station),
            "cycle_id": str(cycle_id),
            "cycle_score": cycle_run_score(
                group["anomaly_score"].to_numpy(dtype=float), consecutive
            ),
        })
    return pd.DataFrame(rows)


def _calibrate_thresholds(
    scores: pd.DataFrame, *, alpha: float, consecutive: int
) -> dict[str, float]:
    cycles = _cycle_score_table(scores, consecutive)
    thresholds: dict[str, float] = {}
    for station, group in cycles.groupby("station_id", sort=True):
        thresholds[str(station)] = conformal_quantile(
            group["cycle_score"].to_numpy(dtype=float), alpha
        )
    return thresholds


def _apply_cycle_rule(
    scores: pd.DataFrame, thresholds: dict[str, float], consecutive: int
) -> pd.DataFrame:
    """Apply the same threshold and consecutive-sample rule to every method."""
    result = scores.copy()
    result["threshold"] = result["station_id"].astype(str).map(thresholds)
    if result["threshold"].isna().any():
        raise ValueError("A score row has no calibrated threshold for its station")
    result["alarm"] = False
    if "most_affected_joint" not in result.columns:
        result["most_affected_joint"] = ""

    for (station, _cycle_id), group in cycle_groups(result):
        values = group["anomaly_score"].to_numpy(dtype=float)
        threshold = thresholds[str(station)]
        indices = group.index.to_numpy()
        for end in range(consecutive - 1, len(values)):
            start = end - consecutive + 1
            if np.all(values[start : end + 1] > threshold):
                result.loc[indices[end], "alarm"] = True
                score_columns = [f"score_{joint.removesuffix('_pct')}" for joint in JOINTS]
                available = [col for col in score_columns if col in result.columns]
                if available:
                    channel_scores = result.loc[indices[end], available].to_numpy(dtype=float)
                    joint_index = int(np.argmax(channel_scores))
                    result.loc[indices[end], "most_affected_joint"] = (
                        f"J{int(available[joint_index].split('_j')[1].split('_')[0])}"
                    )
                break
    return result


class _RobustEnvelope:
    """Global or progress-binned median/MAD reference envelope."""

    def __init__(self, *, n_bins: int, min_bin_samples: int) -> None:
        self.n_bins = n_bins
        self.min_bin_samples = min_bin_samples
        self.centers_: dict[str, np.ndarray] = {}
        self.scales_: dict[str, np.ndarray] = {}

    @staticmethod
    def _robust_location_scale(
        reference: np.ndarray, scale_values: np.ndarray, floor: float = 0.10
    ) -> tuple[float, float]:
        base = float(np.median(reference))
        residual = np.asarray(scale_values, dtype=float) - base
        bias = float(np.median(residual))
        mad = float(np.median(np.abs(residual - bias)))
        return base + bias, max(1.4826 * mad, floor)

    def fit(self, training: pd.DataFrame, scale: pd.DataFrame) -> None:
        stations = sorted(training["station_id"].astype(str).unique())
        edges = np.linspace(0.0, 1.0, self.n_bins + 1)
        for station in stations:
            train_station = training[training["station_id"].astype(str) == station]
            scale_station = scale[scale["station_id"].astype(str) == station]
            centers = np.zeros((self.n_bins, len(JOINTS)), dtype=float)
            scales = np.zeros_like(centers)

            global_stats = [
                self._robust_location_scale(
                    train_station[joint].to_numpy(dtype=float),
                    scale_station[joint].to_numpy(dtype=float),
                )
                for joint in JOINTS
            ]
            if self.n_bins == 1:
                centers[0, :] = [item[0] for item in global_stats]
                scales[0, :] = [item[1] for item in global_stats]
            else:
                train_bin = np.clip(
                    np.digitize(train_station["progress"].to_numpy(dtype=float), edges) - 1,
                    0,
                    self.n_bins - 1,
                )
                scale_bin = np.clip(
                    np.digitize(scale_station["progress"].to_numpy(dtype=float), edges) - 1,
                    0,
                    self.n_bins - 1,
                )
                for bin_id in range(self.n_bins):
                    train_mask = train_bin == bin_id
                    scale_mask = scale_bin == bin_id
                    for joint_index, joint in enumerate(JOINTS):
                        if (
                            int(train_mask.sum()) >= self.min_bin_samples
                            and int(scale_mask.sum()) >= self.min_bin_samples
                        ):
                            center, spread = self._robust_location_scale(
                                train_station.loc[train_mask, joint].to_numpy(dtype=float),
                                scale_station.loc[scale_mask, joint].to_numpy(dtype=float),
                            )
                        else:
                            center, spread = global_stats[joint_index]
                        centers[bin_id, joint_index] = center
                        scales[bin_id, joint_index] = spread
            self.centers_[station] = centers
            self.scales_[station] = scales

    def score_samples(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        for station in sorted(result["station_id"].astype(str).unique()):
            mask = result["station_id"].astype(str) == station
            station_data = result.loc[mask]
            if station not in self.centers_:
                raise ValueError(f"No robust-envelope model for station {station!r}")
            progress = station_data["progress"].to_numpy(dtype=float)
            if self.n_bins == 1:
                bin_index = np.zeros(len(progress), dtype=int)
            else:
                edges = np.linspace(0.0, 1.0, self.n_bins + 1)
                bin_index = np.clip(np.digitize(progress, edges) - 1, 0, self.n_bins - 1)
            observed = station_data[list(JOINTS)].to_numpy(dtype=float)
            center = self.centers_[station][bin_index]
            spread = self.scales_[station][bin_index]
            channel_scores = np.abs(observed - center) / spread
            for joint_index, joint in enumerate(JOINTS):
                column = f"score_{joint.removesuffix('_pct')}"
                result.loc[mask, column] = channel_scores[:, joint_index]
            result.loc[mask, "anomaly_score"] = np.max(channel_scores, axis=1)
            result.loc[mask, "most_affected_joint"] = [
                f"J{index + 1}" for index in np.argmax(channel_scores, axis=1)
            ]
        return result


class _MultivariateNovelty:
    """Isolation Forest, novelty LOF, or One-Class SVM per station."""

    def __init__(self, method: str, random_state: int) -> None:
        self.method = method
        self.random_state = random_state
        self.scalers_: dict[str, RobustScaler] = {}
        self.models_: dict[str, Any] = {}

    def fit(self, training: pd.DataFrame) -> None:
        for station in sorted(training["station_id"].astype(str).unique()):
            station_data = training[training["station_id"].astype(str) == station]
            features = _feature_matrix(station_data)
            scaler = RobustScaler(quantile_range=(10.0, 90.0))
            transformed = scaler.fit_transform(features)
            if len(transformed) < 3:
                raise ValueError(
                    f"{self.method} requires at least three training samples per station"
                )
            if self.method == "isolation_forest":
                model = IsolationForest(
                    n_estimators=200,
                    max_samples="auto",
                    contamination="auto",
                    random_state=self.random_state,
                    n_jobs=-1,
                )
            elif self.method == "local_outlier_factor":
                model = LocalOutlierFactor(
                    n_neighbors=min(20, len(transformed) - 1),
                    novelty=True,
                    contamination="auto",
                    n_jobs=-1,
                )
            elif self.method == "one_class_svm":
                model = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05)
            else:
                raise ValueError(f"Unsupported multivariate method: {self.method}")
            model.fit(transformed)
            self.scalers_[station] = scaler
            self.models_[station] = model

    def score_samples(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        score = np.full(len(result), np.nan, dtype=float)
        for station in sorted(result["station_id"].astype(str).unique()):
            if station not in self.models_:
                raise ValueError(f"No {self.method} model for station {station!r}")
            mask = result["station_id"].astype(str) == station
            transformed = self.scalers_[station].transform(_feature_matrix(result.loc[mask]))
            model = self.models_[station]
            if self.method == "one_class_svm":
                station_score = -model.decision_function(transformed)
            else:
                station_score = -model.score_samples(transformed)
            score[np.flatnonzero(mask.to_numpy())] = np.asarray(station_score, dtype=float)
        result["anomaly_score"] = score
        # These multivariate models do not provide a defensible per-joint attribution.
        result["most_affected_joint"] = ""
        return result


def _validate_partitions(
    training: pd.DataFrame,
    scale: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = normal_only(validate_frame(training, name="training"), name="training")
    scale_df = normal_only(validate_frame(scale, name="scale"), name="scale")
    calibration_df = normal_only(
        validate_frame(calibration, name="calibration"), name="calibration"
    )
    test_df = validate_frame(test, name="test", require_label=True)
    expected = set(train["station_id"].astype(str))
    if not expected:
        raise ValueError("training must contain at least one station")
    for name, frame in (("scale", scale_df), ("calibration", calibration_df), ("test", test_df)):
        found = set(frame["station_id"].astype(str))
        if found != expected:
            raise ValueError(
                f"{name} station mismatch; missing={sorted(expected-found)}, "
                f"unexpected={sorted(found-expected)}"
            )

    partitions = {"training": train, "scale": scale_df, "calibration": calibration_df, "test": test_df}
    keys = {
        name: set(zip(frame["station_id"].astype(str), frame["cycle_id"].astype(str)))
        for name, frame in partitions.items()
    }
    names = list(keys)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            overlap = keys[left] & keys[right]
            if overlap:
                raise ValueError(
                    f"Cycle leakage between {left} and {right}: {sorted(overlap)[:3]}"
                )
    return train, scale_df, calibration_df, test_df


def run_benchmark(
    training: pd.DataFrame,
    scale: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    *,
    alpha: float = 0.05,
    consecutive: int = 3,
    random_state: int = 2026,
    n_bins: int = 20,
    min_bin_samples: int = 15,
    methods: tuple[str, ...] = METHODS,
) -> BenchmarkResult:
    """Run all selected methods with identical partitions and cycle decisions.

    The four data partitions must be disjoint at the whole-cycle level. Thresholds
    are calibrated only on normal calibration cycles; labelled test cycles are never
    used for fitting or calibration.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    if consecutive < 1:
        raise ValueError("consecutive must be >= 1")
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"Unknown benchmark method(s): {sorted(unknown)}")
    if not methods:
        raise ValueError("At least one method must be selected")

    train, scale_df, calibration_df, test_df = _validate_partitions(
        training, scale, calibration, test
    )
    for name, frame in (("calibration", calibration_df), ("test", test_df)):
        short_cycles = [
            (str(station), str(cycle_id), len(group))
            for (station, cycle_id), group in cycle_groups(frame)
            if len(group) < consecutive
        ]
        if short_cycles:
            raise ValueError(
                f"{name} contains cycles shorter than consecutive={consecutive}: "
                f"{short_cycles[:3]}"
            )
    all_summary: list[pd.DataFrame] = []
    all_cycles: list[pd.DataFrame] = []
    all_samples: list[pd.DataFrame] = []
    all_thresholds: dict[str, dict[str, float]] = {}

    for method in methods:
        if method == "gpr_phase_aware":
            detector = PhaseAwareGPRDetector(DetectorConfig(
                alpha=alpha,
                consecutive=consecutive,
                random_state=random_state,
            ))
            detector.fit(train, scale_df, calibration_df)
            calibration_scores = detector.score_samples(calibration_df)
            thresholds = dict(detector.thresholds_)
            test_scores = detector.score_samples(test_df)
        elif method in {"global_robust", "phase_binned_robust"}:
            bins = 1 if method == "global_robust" else n_bins
            envelope = _RobustEnvelope(n_bins=bins, min_bin_samples=min_bin_samples)
            envelope.fit(train, scale_df)
            calibration_scores = envelope.score_samples(calibration_df)
            thresholds = _calibrate_thresholds(
                calibration_scores, alpha=alpha, consecutive=consecutive
            )
            test_scores = envelope.score_samples(test_df)
        else:
            novelty = _MultivariateNovelty(method, random_state)
            novelty.fit(train)
            calibration_scores = novelty.score_samples(calibration_df)
            thresholds = _calibrate_thresholds(
                calibration_scores, alpha=alpha, consecutive=consecutive
            )
            test_scores = novelty.score_samples(test_df)

        prediction = _apply_cycle_rule(test_scores, thresholds, consecutive)
        summary, cycles = evaluate_predictions(prediction)
        summary.insert(0, "method", method)
        cycles.insert(0, "method", method)
        prediction.insert(0, "method", method)
        all_summary.append(summary)
        all_cycles.append(cycles)
        all_samples.append(prediction)
        all_thresholds[method] = thresholds

    return BenchmarkResult(
        summary=pd.concat(all_summary, ignore_index=True),
        cycle_metrics=pd.concat(all_cycles, ignore_index=True),
        sample_scores=pd.concat(all_samples, ignore_index=True),
        thresholds=all_thresholds,
    )
