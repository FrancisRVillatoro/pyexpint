from __future__ import annotations

"""Adaptive time integration for one-step exponential methods.

Adaptive integration currently restricts variable time stepping to methods whose external
state contains only the physical solution.  Variable-step multistep/EGLM methods
require ratio-dependent coefficients and a transformed external state; restarting
those methods at every accepted step would hide rather than solve that problem.

The local temporal error is estimated by step doubling.  Matrix-function actions
are evaluated at a tighter tolerance, coupled to the requested temporal rtol.
"""

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .core import ExternalState, SemilinearProblem, Solution
from .solve import step_external
from .backends import (
    AutoBackend,
    CalibratedAutoBackend,
    DenseBackend,
    DiagonalBackend,
    KiopsBackend,
    KrylovBackend,
    LejaBackend,
    ScipyKiopsBackend,
)


@dataclass(frozen=True)
class AdaptiveOptions:
    rtol: float = 1e-6
    atol: float = 1e-9
    h0: float | None = None
    h_min: float = 0.0
    h_max: float = math.inf
    safety: float = 0.9
    min_factor: float = 0.2
    max_factor: float = 5.0
    max_steps: int = 100000
    norm: str = "rms"
    action_rtol_fraction: float = 0.05
    action_tol_floor: float = 1e-13
    action_tol_ceiling: float = 1e-5
    use_richardson: bool = False
    effective_order: float | None = None

    def __post_init__(self):
        _validate_common_options(self)
        if self.effective_order is not None and not (
            _is_finite(self.effective_order) and self.effective_order > 0
        ):
            raise ValueError("effective_order must be a positive finite number")


def _is_finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _validate_common_options(o) -> None:
    """Checks shared by AdaptiveOptions and ETD34Options (all values finite unless stated)."""
    if not (_is_finite(o.rtol) and o.rtol > 0 and _is_finite(o.atol) and o.atol >= 0):
        raise ValueError("require finite rtol>0 and atol>=0")
    if o.h0 is not None and not (_is_finite(o.h0) and o.h0 > 0):
        raise ValueError("h0 must be positive and finite")
    if not (_is_finite(o.h_min) and o.h_min >= 0) or math.isnan(float(o.h_max)) or o.h_max <= 0 \
            or o.h_min > o.h_max:
        raise ValueError("invalid h_min/h_max")
    if not (_is_finite(o.safety) and 0 < o.safety < 1.5):
        raise ValueError("invalid safety factor")
    if not (_is_finite(o.min_factor) and _is_finite(o.max_factor) and 0 < o.min_factor <= 1 <= o.max_factor):
        raise ValueError("invalid controller factors")
    if int(o.max_steps) != o.max_steps or o.max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    if o.norm not in {"rms", "inf"}:
        raise ValueError("norm must be 'rms' or 'inf'")
    if not (_is_finite(o.action_rtol_fraction) and o.action_rtol_fraction > 0):
        raise ValueError("action_rtol_fraction must be positive and finite")
    if not (_is_finite(o.action_tol_floor) and _is_finite(o.action_tol_ceiling)
            and 0 < o.action_tol_floor <= o.action_tol_ceiling):
        raise ValueError("require 0 < action_tol_floor <= action_tol_ceiling")


def _minimum_step(h_min: float, t0: float, tf: float) -> float:
    """Smallest step a controller may propose: max(h_min, 16*eps*T), T the time scale.

    Steps below 16*eps*T, with T = max(|t0|, |tf|, tf - t0), cannot make
    meaningful progress in double precision.  A rejected or failed attempt at
    this size terminates the integration with an explicit error.
    """
    scale = max(abs(t0), abs(tf), tf - t0)
    return max(float(h_min), 16.0 * np.finfo(float).eps * scale)


class _CountingNonlinear:
    """Wraps problem.nonlinear and counts every evaluation."""

    __slots__ = ("f", "calls")

    def __init__(self, f):
        self.f = f
        self.calls = 0

    def __call__(self, t, y):
        self.calls += 1
        return self.f(t, y)


def _counting_problem(problem):
    counter = _CountingNonlinear(problem.nonlinear)
    return replace(problem, nonlinear=counter), counter


def _clone_backend_with_tol(backend, tol: float):
    """Return a copy of ``backend`` whose matrix-function tolerance is ``tol``.

    Any backend, built-in or external, can define ``with_tolerance(tol)`` returning
    a backend of the same kind with action tolerance ``tol``; a backend without a
    tolerance (for example an exact diagonalization) may return itself.  That hook
    takes precedence.  Built-in backends are otherwise cloned with all
    non-tolerance tuning parameters, and CalibratedAutoBackend keeps its type,
    calibration record and current thresholds.
    """
    hook = getattr(backend, "with_tolerance", None)
    if callable(hook):
        return hook(tol)
    if isinstance(backend, DiagonalBackend):
        return DiagonalBackend()
    if isinstance(backend, DenseBackend):
        return DenseBackend()
    if isinstance(backend, KiopsBackend):
        o = backend.options
        return KiopsBackend(
            tol=tol, m_init=o.m_init, m_min=o.m_min, m_max=o.m_max,
            orth_len=o.orth_len, delta=o.delta,
        )
    if isinstance(backend, ScipyKiopsBackend):
        o = backend.kiops.options
        return ScipyKiopsBackend(
            tol=tol, m_init=o.m_init, m_min=o.m_min, m_max=o.m_max,
            orth_len=o.orth_len, delta=o.delta,
        )
    if isinstance(backend, KrylovBackend):
        o = backend.options
        return KrylovBackend(
            tol=tol, min_dim=o.min_dim, max_dim=o.max_dim,
            check_every=o.check_every,
            breakdown_tol=o.breakdown_tol,
            reorthogonalize=o.reorthogonalize,
            fail_on_nonconvergence=backend.fail_on_nonconvergence,
            fuse_sums=backend.fuse_sums,
        )
    if isinstance(backend, LejaBackend):
        o = backend.options
        return LejaBackend(
            tol=tol, spectral_bounds=backend.spectral_bounds,
            min_degree=o.min_degree, max_degree=o.max_degree,
            target_width=o.target_width, candidate_count=o.candidate_count,
        )
    if isinstance(backend, CalibratedAutoBackend):
        clone = CalibratedAutoBackend(
            backend.calibration, tol=tol, leja_target_width=backend.leja.options.target_width,
        )
        clone.dense_cutoff = backend.dense_cutoff
        clone.leja_min_size = backend.leja_min_size
        clone.leja_width_threshold = backend.leja_width_threshold
        return clone
    if isinstance(backend, AutoBackend):
        return AutoBackend(
            tol=tol,
            dense_cutoff=backend.dense_cutoff,
            leja_min_size=backend.leja_min_size,
            leja_width_threshold=backend.leja_width_threshold,
            leja_target_width=backend.leja.options.target_width,
        )
    raise TypeError(
        f"Adaptive tolerance coupling is not implemented for backend {type(backend).__name__}; "
        "define with_tolerance(tol) returning a backend with action tolerance tol."
    )


def _merge_numeric_stats(total: dict[str, float], stats: dict[str, Any]) -> None:
    for key, value in stats.items():
        if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
            if value is not None and np.isfinite(value):
                total[key] = total.get(key, 0.0) + float(value)


def _scaled_error_norm(err, y0, y1, *, rtol, atol, norm):
    scale = atol + rtol * np.maximum(np.abs(y0), np.abs(y1))
    scale = np.maximum(scale, np.finfo(float).tiny)
    q = np.abs(err) / scale
    if norm == "inf":
        return float(np.max(q))
    return float(np.sqrt(np.mean(q * q)))


def _trial_step(problem, method, t, y, h, backend):
    state = ExternalState(float(t), np.stack([np.asarray(y)], axis=0))
    full = step_external(problem, method, state, h, backend).y
    half1 = step_external(problem, method, state, 0.5*h, backend)
    half2 = step_external(problem, method, half1, 0.5*h, backend).y
    return np.asarray(full), np.asarray(half2)


def solve_adaptive(
    problem: SemilinearProblem,
    method,
    backend,
    *,
    options: AdaptiveOptions | None = None,
    **option_overrides,
) -> Solution:
    """Adaptive one-step integration using step doubling.

    The accepted solution is the two-half-step result.  Optional Richardson
    extrapolation is available, but disabled by default because stiff order
    reduction can invalidate use of the classical order in the correction.
    """
    if method.outputs != 1 or method.history_length != 0:
        raise NotImplementedError(
            "Adaptive stepping currently supports one-step methods only. "
            "Variable-step multistep/EGLM methods require ratio-dependent coefficients."
        )
    if method.historical_comparator:
        # The algorithm still works, but this keeps the intended API explicit.
        pass

    if options is None:
        options = AdaptiveOptions(**option_overrides)
    elif option_overrides:
        raise ValueError("pass either AdaptiveOptions or keyword overrides, not both")

    t0, tf = map(float, problem.t_span)
    span = tf - t0
    order = float(options.effective_order or method.classical_order)
    if order <= 0:
        raise ValueError("effective method order must be positive")
    denom = max(1.0, 2.0**order - 1.0)
    h_floor = _minimum_step(options.h_min, t0, tf)
    if h_floor > options.h_max:
        raise ValueError(
            f"h_max={options.h_max:.3e} is below the smallest resolvable step {h_floor:.3e} "
            f"for t_span=({t0}, {tf})"
        )
    problem, counter = _counting_problem(problem)

    if options.h0 is None:
        h = min(options.h_max, span / 16.0)
    else:
        h = min(options.h_max, options.h0)
    h = min(h, span)
    h = max(h, h_floor)

    action_tol = options.action_rtol_fraction * options.rtol
    action_tol = min(options.action_tol_ceiling, max(options.action_tol_floor, action_tol))
    work_backend = _clone_backend_with_tol(backend, action_tol)
    reset = getattr(work_backend, "reset_stats", None)
    if reset is not None:
        reset()

    t = t0
    y = np.array(problem.y0, copy=True)
    ts = [t]
    ys = [y.copy()]
    hs = []
    errs = []
    rejected = 0
    nonfinite = 0
    attempts = 0
    nonlinear_evals = 0

    while t < tf:
        if attempts >= options.max_steps:
            raise RuntimeError("maximum number of adaptive step attempts exceeded")
        attempts += 1

        h = min(h, tf - t)
        if not t + h > t:
            raise RuntimeError(f"step size {h:.3e} makes no progress at t={t!r}")
        at_floor = h <= h_floor * (1.0 + 1e-12)

        full, half = _trial_step(problem, method, t, y, h, work_backend)
        nonlinear_evals += 3 * (method.nonlinear_evals_per_step or method.stages)

        err_vec = (half - full) / denom
        if np.all(np.isfinite(full)) and np.all(np.isfinite(half)):
            err_norm = _scaled_error_norm(
                err_vec, y, half,
                rtol=options.rtol, atol=options.atol, norm=options.norm,
            )
        else:
            err_norm = math.nan

        if not math.isfinite(err_norm):
            rejected += 1
            nonfinite += 1
            if at_floor:
                raise RuntimeError(f"non-finite trial result at the minimum step size {h:.3e} (t={t!r})")
            h = max(h_floor, 0.5 * h)
            if (tf - t) > h * (options.max_steps - attempts):
                raise RuntimeError(
                    f"non-finite trial result; after reducing the step to {h:.3e} at t={t!r}, reaching "
                    f"tf={tf!r} would need more than the remaining max_steps attempts"
                )
            continue

        if err_norm <= 1.0:
            if options.use_richardson:
                ynew = half + err_vec
            else:
                ynew = half
            tnew = t + h
            t = float(tnew)
            y = np.asarray(np.real_if_close(ynew))
            ts.append(t)
            ys.append(y.copy())
            hs.append(float(h))
            errs.append(float(err_norm))

            if err_norm == 0.0:
                factor = options.max_factor
            else:
                factor = options.safety * err_norm ** (-1.0 / (order + 1.0))
                factor = min(options.max_factor, max(options.min_factor, factor))
            h = max(h_floor, min(options.h_max, h * factor))
        else:
            rejected += 1
            if at_floor:
                raise RuntimeError(
                    f"error test failed at the minimum step size {h:.3e} (t={t!r}); "
                    "the requested tolerances cannot be met"
                )
            factor = options.safety * err_norm ** (-1.0 / (order + 1.0))
            factor = min(1.0, max(options.min_factor, factor))
            h = max(h_floor, h * factor)

    backend_stats = getattr(work_backend, "stats", lambda: {})()
    return Solution(
        t=np.asarray(ts),
        y=np.real_if_close(np.asarray(ys)),
        method=method.name,
        backend=f"adaptive:{backend.name}",
        step_size=float("nan"),
        stats={
            "adaptive": True,
            "accepted_steps": len(hs),
            "rejected_steps": rejected,
            "attempted_steps": attempts,
            "step_sizes": hs,
            "error_norms": errs,
            "rtol": options.rtol,
            "atol": options.atol,
            "effective_order": order,
            "action_tolerance": action_tol,
            "action_rtol_fraction": options.action_rtol_fraction,
            "nonlinear_evals_estimate": nonlinear_evals,
            "nonlinear_evals": counter.calls,
            "nonfinite_rejections": nonfinite,
            "minimum_step": h_floor,
            "backend_stats": backend_stats,
        },
    )
