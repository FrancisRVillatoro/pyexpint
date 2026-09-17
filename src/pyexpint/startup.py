from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import numpy as np

from .core import ExternalState, SemilinearProblem


@dataclass(frozen=True)
class StartupResult:
    state: ExternalState
    t: np.ndarray
    y: np.ndarray
    policy: str
    starter_method: str | None


class StartupPolicy(Protocol):
    name: str
    def initialize(self, problem, method, h, backend, step_one_step) -> StartupResult: ...


def _history_state(problem: SemilinearProblem, h: float, ts: list[float], ys: list[np.ndarray], r: int):
    m = len(ys) - 1
    vals = [np.asarray(ys[m])]
    for lag in range(1, r):
        idx = m - lag
        vals.append(h * np.asarray(problem.nonlinear(ts[idx], ys[idx])))
    return np.stack(vals, axis=0)


@dataclass(frozen=True)
class ExactStartup:
    """Initialize history from problem.exact_solution."""
    name: str = "exact"

    def initialize(self, problem, method, h, backend, step_one_step):
        if problem.exact_solution is None:
            raise ValueError("ExactStartup requires problem.exact_solution.")
        r = method.outputs
        nstart = max(0, r - 1)
        t0 = float(problem.t_span[0])
        ts = [t0 + j*h for j in range(nstart + 1)]
        ys = [np.asarray(problem.exact_solution(t)) for t in ts]
        vals = _history_state(problem, h, ts, ys, r) if r > 1 else np.stack([ys[0]])
        return StartupResult(
            state=ExternalState(ts[-1], vals),
            t=np.asarray(ts), y=np.asarray(ys),
            policy=self.name, starter_method=None,
        )


@dataclass(frozen=True)
class OneStepStartup:
    """Build nonlinear history with an arbitrary one-step MethodSpec."""
    starter: object
    name: str = "one_step"

    def initialize(self, problem, method, h, backend, step_one_step):
        if getattr(self.starter, "outputs", None) != 1:
            raise ValueError("Startup starter must be a one-step (r=1) method.")
        r = method.outputs
        nstart = max(0, r - 1)
        t0 = float(problem.t_span[0])
        ts = [t0]
        ys = [np.array(problem.y0, copy=True)]
        y = ys[0]
        t = t0
        for _ in range(nstart):
            y = step_one_step(problem, self.starter, t, y, h, backend)
            t += h
            ts.append(t)
            ys.append(np.asarray(y))
        vals = _history_state(problem, h, ts, ys, r) if r > 1 else np.stack([ys[0]])
        return StartupResult(
            state=ExternalState(ts[-1], vals),
            t=np.asarray(ts), y=np.asarray(ys),
            policy=self.name, starter_method=self.starter.name,
        )
