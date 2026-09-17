from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

from .auto import AutoBackend


@dataclass(frozen=True)
class SelectorCalibration:
    """Portable description of a measured Kiops/Leja crossover rule."""

    leja_min_size: int
    leja_width_threshold: float
    dense_cutoff: int = 96
    objective: str = "log-regret"
    training_cases: int = 0
    mean_log_regret: float = 0.0
    max_slowdown: float = 1.0
    machine_label: str = "unspecified"

    def to_dict(self):
        return asdict(self)

    def to_json(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    @classmethod
    def from_json(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def fit_threshold_selector(cases, *, dense_cutoff=96, machine_label="unspecified") -> SelectorCalibration:
    """Fit the simple sparse-Hermitian Leja-vs-KIOPS threshold rule.

    ``cases`` entries require ``n``, ``scaled_spectral_width``, ``kiops_seconds``
    and ``leja_seconds``.  The fitted rule is Leja iff

        n >= leja_min_size and width <= leja_width_threshold.

    The objective minimizes mean log runtime regret against the faster of the two.
    """
    rows = [r for r in cases if r["kiops_seconds"] > 0 and r["leja_seconds"] > 0]
    if not rows:
        raise ValueError("no valid calibration cases")
    ns = sorted({int(r["n"]) for r in rows})
    widths = sorted({float(r["scaled_spectral_width"]) for r in rows})
    n_candidates = ns + [max(ns) + 1]
    w_candidates = widths + [math.inf]

    best = None
    for n0 in n_candidates:
        for w0 in w_candidates:
            regrets = []
            slowdowns = []
            for r in rows:
                choose_leja = int(r["n"]) >= n0 and float(r["scaled_spectral_width"]) <= w0
                chosen = r["leja_seconds"] if choose_leja else r["kiops_seconds"]
                fastest = min(r["kiops_seconds"], r["leja_seconds"])
                ratio = chosen / fastest
                regrets.append(math.log(max(ratio, 1.0)))
                slowdowns.append(ratio)
            score = sum(regrets) / len(regrets)
            candidate = (score, max(slowdowns), n0, w0)
            if best is None or candidate < best:
                best = candidate
    score, worst, n0, w0 = best
    return SelectorCalibration(
        leja_min_size=int(n0), leja_width_threshold=float(w0),
        dense_cutoff=int(dense_cutoff), training_cases=len(rows),
        mean_log_regret=float(score), max_slowdown=float(worst),
        machine_label=machine_label,
    )


class CalibratedAutoBackend(AutoBackend):
    """AutoBackend configured from a measured SelectorCalibration."""

    name = "auto-calibrated"

    def __init__(self, calibration: SelectorCalibration, *, tol=1e-10, leja_target_width=12.0):
        self.calibration = calibration
        super().__init__(
            tol=tol,
            dense_cutoff=calibration.dense_cutoff,
            leja_min_size=calibration.leja_min_size,
            leja_width_threshold=calibration.leja_width_threshold,
            leja_target_width=leja_target_width,
        )

    def stats(self):
        out = super().stats()
        out["calibration"] = self.calibration.to_dict()
        return out
