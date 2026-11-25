"""Deterministic synthetic signal generator; no industrial data is included."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .schema import JOINTS


def _make_cycle(
    cycle_id: str,
    station_id: str,
    rng: np.random.Generator,
    *,
    anomalous: bool = False,
    amplitude_pct: float = 0.0,
    shape: str = "ramp",
) -> pd.DataFrame:
    n = 80
    progress = np.linspace(0.0, 1.0, n)
    station_offset = 0.35 if station_id == "station_b" else 0.0
    currents = []
    for j in range(6):
        base = (
            8.0 + j * 1.4 + station_offset
            + (1.5 + 0.15 * j) * progress
            + (1.1 + 0.08 * j) * np.sin((1.0 + 0.08 * j) * np.pi * progress)
            + 0.35 * np.cos((2.0 + 0.05 * j) * np.pi * progress)
        )
        cycle_drift = rng.normal(0.0, 0.10)
        noise = rng.normal(0.0, 0.12 + j * 0.005, size=n)
        currents.append(base + cycle_drift + noise)

    signal = np.column_stack(currents)
    if anomalous:
        onset = int(rng.integers(18, 45))
        ramp = np.clip((np.arange(n) - onset) / max(1, n - onset - 1), 0.0, 1.0)
        if shape == "ramp":
            profile = ramp
        elif shape == "quadratic":
            profile = ramp**2
        elif shape == "step":
            profile = (np.arange(n) >= onset).astype(float)
        else:
            raise ValueError("shape must be 'ramp', 'quadratic', or 'step'")
        joint_pattern = np.array([0.20, 0.45, 1.00, 0.25, 0.55, 0.35])
        direction = float(rng.choice([-1.0, 1.0]))
        signal += direction * profile[:, None] * amplitude_pct * joint_pattern[None, :]

    table = pd.DataFrame(signal, columns=JOINTS)
    table.insert(0, "progress", progress)
    table.insert(0, "station_id", station_id)
    table.insert(0, "cycle_id", cycle_id)
    table["label"] = int(anomalous)
    table["time_ms"] = np.arange(n, dtype=float) * 4.0  # synthetic 250 Hz example
    return table


def make_synthetic_dataset(
    output_dir: str | Path,
    *,
    seed: int = 2026,
    training_cycles_per_station: int = 45,
    scale_cycles_per_station: int = 20,
    calibration_cycles_per_station: int = 40,
    test_normal_cycles_per_station: int = 60,
    test_anomaly_cycles_per_station: int = 60,
) -> dict[str, Path]:
    """Create four independent CSV partitions for a reproducible tutorial."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    partitions: dict[str, list[pd.DataFrame]] = {
        "training": [], "scale": [], "calibration": [], "test": []
    }
    counters = {key: 0 for key in partitions}

    for station in ("station_a", "station_b"):
        for partition, count in (
            ("training", training_cycles_per_station),
            ("scale", scale_cycles_per_station),
            ("calibration", calibration_cycles_per_station),
        ):
            for _ in range(count):
                counters[partition] += 1
                cycle_id = f"{partition}_{station}_{counters[partition]:05d}"
                partitions[partition].append(_make_cycle(cycle_id, station, rng))

        for _ in range(test_normal_cycles_per_station):
            counters["test"] += 1
            cycle_id = f"test_normal_{station}_{counters['test']:05d}"
            partitions["test"].append(_make_cycle(cycle_id, station, rng))
        for _ in range(test_anomaly_cycles_per_station):
            counters["test"] += 1
            cycle_id = f"test_anomaly_{station}_{counters['test']:05d}"
            amplitude = float(rng.choice([2.0, 3.0, 4.0, 5.0, 6.0]))
            shape = str(rng.choice(["ramp", "quadratic", "step"]))
            partitions["test"].append(_make_cycle(
                cycle_id, station, rng, anomalous=True, amplitude_pct=amplitude, shape=shape
            ))

    paths: dict[str, Path] = {}
    for name, frames in partitions.items():
        path = output / f"{name}.csv"
        pd.concat(frames, ignore_index=True).to_csv(path, index=False)
        paths[name] = path
    return paths
