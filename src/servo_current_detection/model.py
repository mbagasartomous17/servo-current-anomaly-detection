"""Position-conditioned Gaussian-process detector for six current channels."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel

from .calibration import conformal_quantile, cycle_run_score
from .schema import JOINTS, cycle_groups, normal_only, validate_frame


@dataclass(frozen=True)
class DetectorConfig:
    """Hyperparameters for the baseline phase-aware GPR detector."""

    alpha: float = 0.001
    consecutive: int = 3
    n_bins: int = 40
    min_bin_samples: int = 25
    scale_floor_pct: float = 0.10
    max_training_points_per_joint: int = 400
    random_state: int = 2026
    optimizer_restarts: int = 0

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1")
        if self.consecutive < 1 or self.n_bins < 1 or self.min_bin_samples < 1:
            raise ValueError("consecutive, n_bins, and min_bin_samples must be positive")
        if self.scale_floor_pct <= 0:
            raise ValueError("scale_floor_pct must be positive")
        if self.max_training_points_per_joint < 10:
            raise ValueError("max_training_points_per_joint must be at least 10")


class PhaseAwareGPRDetector:
    """GPR normal-current model, robust position scaling, and conformal alarm.

    Separate normal-only partitions are required for:
      * `training`: fit the six GPR regressors per station;
      * `scale`: estimate robust residual dispersion per progress bin;
      * `calibration`: calibrate the cycle-level threshold.

    This separation is deliberate to reduce optimistic residual estimates and
    to keep the calibration set independent of model fitting and scale fitting.
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self.models_: dict[tuple[str, str], GaussianProcessRegressor] = {}
        self.scales_: dict[tuple[str, str], np.ndarray] = {}
        self.thresholds_: dict[str, float] = {}
        self.stations_: tuple[str, ...] = ()
        self.is_fitted_ = False
        self.is_calibrated_ = False

    @staticmethod
    def _kernel() -> Any:
        return (
            ConstantKernel(1.0, constant_value_bounds=(1e-2, 1e2))
            * RBF(length_scale=0.25, length_scale_bounds=(0.02, 2.0))
            + WhiteKernel(noise_level=0.05, noise_level_bounds=(1e-4, 5.0))
        )

    def _select_training_rows(self, frame: pd.DataFrame, joint: str, seed_offset: int) -> pd.DataFrame:
        max_points = self.config.max_training_points_per_joint
        if len(frame) <= max_points:
            return frame
        rng = np.random.default_rng(self.config.random_state + seed_offset)
        # Stratify over progress so that downsampling does not erase a short
        # region of the movement trajectory.
        bins = np.linspace(0.0, 1.0, 21)
        progress_bin = np.clip(np.digitize(frame["progress"], bins) - 1, 0, 19)
        selected: list[int] = []
        per_bin = max(1, max_points // 20)
        for bin_id in range(20):
            indices = np.flatnonzero(progress_bin == bin_id)
            if indices.size:
                take = min(per_bin, indices.size)
                selected.extend(rng.choice(indices, size=take, replace=False).tolist())
        if len(selected) < max_points:
            remaining = np.setdiff1d(np.arange(len(frame)), np.asarray(selected, dtype=int))
            extra = min(max_points - len(selected), remaining.size)
            if extra:
                selected.extend(rng.choice(remaining, size=extra, replace=False).tolist())
        selected = sorted(selected[:max_points])
        return frame.iloc[selected]

    def fit(
        self,
        training: pd.DataFrame,
        scale: pd.DataFrame,
        calibration: pd.DataFrame,
    ) -> "PhaseAwareGPRDetector":
        """Fit the model, residual scales, and normal-cycle thresholds."""
        train = normal_only(validate_frame(training, name="training"), name="training")
        scale_df = normal_only(validate_frame(scale, name="scale"), name="scale")
        calibration_df = normal_only(
            validate_frame(calibration, name="calibration"), name="calibration"
        )
        stations = sorted(set(train["station_id"].astype(str)))
        if not stations:
            raise ValueError("training must contain at least one station")
        for dataset_name, dataset in (("scale", scale_df), ("calibration", calibration_df)):
            missing = set(stations) - set(dataset["station_id"].astype(str))
            if missing:
                raise ValueError(f"{dataset_name} is missing stations present in training: {sorted(missing)}")

        self.models_.clear()
        self.scales_.clear()
        self.thresholds_.clear()
        self.stations_ = tuple(stations)

        for station_index, station in enumerate(stations):
            train_station = train[train["station_id"].astype(str) == station]
            scale_station = scale_df[scale_df["station_id"].astype(str) == station]
            for joint_index, joint in enumerate(JOINTS):
                subset = self._select_training_rows(
                    train_station, joint, station_index * len(JOINTS) + joint_index
                )
                x = subset["progress"].to_numpy(dtype=float).reshape(-1, 1)
                y = subset[joint].to_numpy(dtype=float)
                regressor = GaussianProcessRegressor(
                    kernel=self._kernel(),
                    alpha=1e-6,
                    normalize_y=True,
                    n_restarts_optimizer=self.config.optimizer_restarts,
                    random_state=self.config.random_state + joint_index,
                )
                regressor.fit(x, y)
                self.models_[(station, joint)] = regressor

                residual_frame = scale_station[["progress", joint]]
                residual = residual_frame[joint].to_numpy(dtype=float) - regressor.predict(
                    residual_frame["progress"].to_numpy(dtype=float).reshape(-1, 1)
                )
                self.scales_[(station, joint)] = self._fit_robust_scale(
                    residual_frame["progress"].to_numpy(dtype=float), residual
                )

        self.is_fitted_ = True
        self.is_calibrated_ = False
        calibration_scores = self.score_cycles(calibration_df)
        for station in stations:
            values = calibration_scores.loc[
                calibration_scores["station_id"].astype(str) == station, "cycle_score"
            ].to_numpy(dtype=float)
            self.thresholds_[station] = conformal_quantile(values, self.config.alpha)
        self.is_calibrated_ = True
        return self

    def _fit_robust_scale(self, progress: np.ndarray, residual: np.ndarray) -> np.ndarray:
        edges = np.linspace(0.0, 1.0, self.config.n_bins + 1)
        indices = np.clip(np.digitize(progress, edges) - 1, 0, self.config.n_bins - 1)
        global_mad = np.median(np.abs(residual - np.median(residual)))
        global_scale = max(1.4826 * float(global_mad), self.config.scale_floor_pct)
        output = np.full(self.config.n_bins, global_scale, dtype=float)
        for bin_id in range(self.config.n_bins):
            values = residual[indices == bin_id]
            if values.size >= self.config.min_bin_samples:
                mad = np.median(np.abs(values - np.median(values)))
                output[bin_id] = max(1.4826 * float(mad), self.config.scale_floor_pct)
        return output

    def _scale_for(self, station: str, joint: str, progress: np.ndarray) -> np.ndarray:
        edges = np.linspace(0.0, 1.0, self.config.n_bins + 1)
        indices = np.clip(np.digitize(progress, edges) - 1, 0, self.config.n_bins - 1)
        return self.scales_[(station, joint)][indices]

    def score_samples(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return per-sample normalized residuals and a six-joint max score."""
        if not self.is_fitted_:
            raise RuntimeError("Call fit() before score_samples()")
        frame = validate_frame(data, name="data")
        unknown = set(frame["station_id"].astype(str)) - set(self.stations_)
        if unknown:
            raise ValueError(f"No fitted model for station(s): {sorted(unknown)}")
        result = frame.copy()
        joint_score_columns: list[str] = []
        for station in self.stations_:
            mask = result["station_id"].astype(str) == station
            station_data = result.loc[mask]
            progress = station_data["progress"].to_numpy(dtype=float)
            for joint in JOINTS:
                prediction = self.models_[(station, joint)].predict(progress.reshape(-1, 1))
                scale = self._scale_for(station, joint, progress)
                score_col = f"score_{joint.removesuffix('_pct')}"
                values = np.abs(station_data[joint].to_numpy(dtype=float) - prediction) / scale
                result.loc[mask, score_col] = values
                if score_col not in joint_score_columns:
                    joint_score_columns.append(score_col)
        result["anomaly_score"] = result[joint_score_columns].max(axis=1)
        return result

    def score_cycles(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute one maximum run score for each cycle and station."""
        scored = self.score_samples(data)
        records: list[dict[str, Any]] = []
        for (station, cycle_id), group in cycle_groups(scored):
            records.append({
                "station_id": str(station),
                "cycle_id": str(cycle_id),
                "cycle_score": cycle_run_score(
                    group["anomaly_score"].to_numpy(dtype=float), self.config.consecutive
                ),
                "label": int(group["label"].max()) if "label" in group.columns else 0,
            })
        return pd.DataFrame.from_records(records)

    def predict_samples(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply calibrated thresholds and mark the first alarm sample per cycle."""
        if not self.is_calibrated_:
            raise RuntimeError("Call fit() before predict_samples()")
        result = self.score_samples(data)
        result["threshold"] = result["station_id"].astype(str).map(self.thresholds_)
        result["alarm"] = False
        result["most_affected_joint"] = ""
        for (station, cycle_id), group in cycle_groups(result):
            indices = group.index.to_numpy()
            values = group["anomaly_score"].to_numpy(dtype=float)
            threshold = self.thresholds_[str(station)]
            for end in range(self.config.consecutive - 1, len(values)):
                start = end - self.config.consecutive + 1
                if np.all(values[start : end + 1] > threshold):
                    result.loc[indices[end], "alarm"] = True
                    score_columns = [f"score_{joint.removesuffix('_pct')}" for joint in JOINTS]
                    joint_scores = result.loc[indices[end], score_columns].to_numpy(dtype=float)[0]
                    joint_index = int(np.argmax(joint_scores))
                    result.loc[indices[end], "most_affected_joint"] = f"J{joint_index + 1}"
                    break
        return result

    def save(self, path: str) -> None:
        """Persist the fitted detector with joblib."""
        if not self.is_calibrated_:
            raise RuntimeError("Cannot save an uncalibrated detector")
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "PhaseAwareGPRDetector":
        """Load a detector previously saved with save()."""
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError("The file does not contain a PhaseAwareGPRDetector")
        return loaded

    def get_config(self) -> dict[str, Any]:
        """Return a JSON-friendly configuration summary."""
        return asdict(self.config)
