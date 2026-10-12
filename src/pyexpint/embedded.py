from __future__ import annotations
from dataclasses import dataclass
import math, time
from typing import Any
import numpy as np

from .core import SemilinearProblem, Solution
from .methods import KROGSTAD
from .adaptive import (
    _clone_backend_with_tol, _counting_problem, _is_finite, _minimum_step,
    _scaled_error_norm, _validate_common_options,
)
from .solve import _sum_actions
from .backends import LejaConvergenceError, KiopsConvergenceError, KrylovConvergenceError


@dataclass(frozen=True)
class ETD34Options:
    rtol: float = 1e-6
    atol: float = 1e-9
    h0: float | None = None
    h_min: float = 0.0
    h_max: float = math.inf
    safety: float = 0.9
    min_factor: float = 0.2
    max_factor: float = 4.0
    max_steps: int = 100000
    norm: str = "rms"
    action_rtol_fraction: float = 0.05
    action_tol_floor: float = 1e-13
    action_tol_ceiling: float = 1e-5
    controller: str = "accuracy"
    cost_metric: str = "matvecs"
    cost_alpha: float = 0.65241444
    cost_beta: float = 0.26862269
    cost_lambda: float = 1.37412002
    cost_delta: float = 0.64446017

    def __post_init__(self):
        _validate_common_options(self)
        if self.controller not in {"accuracy", "cost"}:
            raise ValueError("controller must be accuracy or cost")
        if self.cost_metric not in {"matvecs", "wall"}:
            raise ValueError("cost_metric must be matvecs or wall")
        if not all(_is_finite(v) for v in (self.cost_alpha, self.cost_beta, self.cost_lambda, self.cost_delta)):
            raise ValueError("cost controller parameters must be finite")
        if not (self.cost_alpha > 0 and self.cost_beta > 0 and self.cost_lambda >= 1 and 0 < self.cost_delta <= 1):
            raise ValueError("require cost_alpha>0, cost_beta>0, cost_lambda>=1 and 0<cost_delta<=1")


def _backend_matvecs(backend) -> float | None:
    """Authoritative cumulative matrix-vector count reported by ``backend``.

    Only the top-level ``"matvecs"`` entry of ``backend.stats()`` is used.  Nested
    dictionaries, such as the per-engine breakdowns reported by AutoBackend, describe
    the same products and are never added to it.  ``None`` means that the backend
    does not report a matrix-vector count; it is never replaced by another unit.
    """
    getter = getattr(backend, "stats", None)
    if getter is None:
        return None
    stats = getter()
    if not isinstance(stats, dict):
        return None
    value = stats.get("matvecs")
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _cost_proposal(h_n, work_n, h_prev, work_prev, *, alpha, beta, lambd, delta):
    values = (h_n, work_n, h_prev, work_prev)
    if any(v is None for v in values):
        return None
    if not all(math.isfinite(float(v)) and float(v) > 0 for v in values):
        return None
    dlogh = math.log(h_n) - math.log(h_prev)
    if abs(dlogh) < 1e-10:
        return None
    c_n, c_prev = work_n / h_n, work_prev / h_prev
    gradient = (math.log(c_n) - math.log(c_prev)) / dlogh
    s = math.exp(-alpha * math.tanh(beta * gradient))
    if 1.0 <= s < lambd:
        s = lambd
    elif delta <= s < 1.0:
        s = delta
    return h_n * s


def _check_budget(reason, h_next, t, tf, attempts, max_steps, cause=None):
    """Stop early when a failure leaves a step size that cannot reach tf within max_steps.

    Only failures (backend errors or non-finite trials) trigger this check, so
    accuracy-driven reductions of the step size are never affected.
    """
    remaining = max_steps - attempts
    if (tf - t) > h_next * remaining:
        raise RuntimeError(
            f"ETD34: {reason}; after reducing the step to {h_next:.3e} at t={t!r}, reaching "
            f"tf={tf!r} would need more than the remaining max_steps={remaining} attempts"
        ) from cause


def _attempt_work(count_matvecs, backend, mv0, tic):
    """Work of one attempt in the declared unit; NaN when the matvec count is missing."""
    wall = time.perf_counter() - tic
    if not count_matvecs:
        return wall
    mv1 = _backend_matvecs(backend)
    if mv0 is None or mv1 is None:
        return math.nan
    if mv1 < mv0:
        raise RuntimeError("backend matrix-vector counter decreased during an ETD34 trial")
    return mv1 - mv0


def _etd34_trial(problem, t, y, h, backend, n1):
    method = KROGSTAD
    ctx = backend.bind(problem.linear_operator, h)
    y = np.asarray(y)
    G = [h * np.asarray(n1)]
    for i in range(1, method.stages):
        Yi = method.U[i][0].apply(ctx, y)
        Yi = Yi + _sum_actions(method.A[i][:i], G, ctx, y.shape)
        Ni = np.asarray(problem.nonlinear(t + method.c[i] * h, np.real_if_close(Yi)))
        G.append(h * Ni)
    high = method.V[0][0].apply(ctx, y)
    high = high + _sum_actions(method.B[0], G, ctx, y.shape)
    high = np.asarray(np.real_if_close(high))
    n5 = np.asarray(problem.nonlinear(t + h, high))
    err = h * method.B[0][3].apply(ctx, (G[3] / h) - n5)
    return high, np.asarray(np.real_if_close(err)), n5


def solve_etd34(problem: SemilinearProblem, backend, *, options: ETD34Options | None = None, **overrides) -> Solution:
    """Adaptive Krogstad fourth-order ETD with embedded third-order estimator.

    The pair is the ETD34 method of Whalen, Brio and Moloney (J. Comput. Phys. 280,
    2015).  The local error estimate is

        e_n = h b_4(hL) (N(t_n + h, Y_4) - N(t_n + h, y_{n+1})),

    the same form used by rkstiff 1.0.2.  Both evaluations share the time t_n + h,
    so any state-independent part of N (for example a forcing g(t)) cancels and is
    invisible to the controller; for N(t, y) = g(t) the estimate vanishes
    identically.  Failed matrix-function actions and non-finite trial results are
    treated as rejected attempts with h halved.  The integration stops with
    RuntimeError when an attempt fails or is rejected at the minimum step
    max(h_min, 16*eps*T), T = max(|t0|, |tf|, tf - t0), when a step would make no
    progress in floating point, or when a failure leaves a step size too small to
    reach tf within the remaining max_steps attempts.
    """
    if options is None:
        options = ETD34Options(**overrides)
    elif overrides:
        raise ValueError("pass either ETD34Options or keyword overrides, not both")

    t0, tf = map(float, problem.t_span)
    span = tf - t0
    h_floor = _minimum_step(options.h_min, t0, tf)
    if h_floor > options.h_max:
        raise ValueError(
            f"h_max={options.h_max:.3e} is below the smallest resolvable step {h_floor:.3e} "
            f"for t_span=({t0}, {tf})"
        )
    h = options.h0 if options.h0 is not None else span / 16.0
    h = min(h, options.h_max, span)
    h = max(h, h_floor)

    action_tol = min(
        options.action_tol_ceiling,
        max(options.action_tol_floor, options.action_rtol_fraction * options.rtol),
    )
    work_backend = _clone_backend_with_tol(backend, action_tol)
    if hasattr(work_backend, "reset_stats"):
        work_backend.reset_stats()
    count_matvecs = options.cost_metric == "matvecs"
    if count_matvecs and options.controller == "cost" and _backend_matvecs(work_backend) is None:
        raise ValueError(
            "controller='cost' with cost_metric='matvecs' requires a backend whose stats() "
            "report 'matvecs'; use cost_metric='wall' for this backend"
        )

    problem, counter = _counting_problem(problem)
    t, y = t0, np.array(problem.y0, copy=True)
    n1 = np.asarray(problem.nonlinear(t, y))
    if not np.all(np.isfinite(n1)):
        raise ValueError("nonlinear(t0, y0) returned non-finite values")
    nonlinear_evals = 1
    ts, ys, hs, errs = [t], [y.copy()], [], []
    work_attempt, work_accept, work_failed, modes = [], [], [], []
    rejected = attempts = backend_failures = nonfinite = missing_work = 0
    prev_h = prev_work = None

    while t < tf:
        if attempts >= options.max_steps:
            raise RuntimeError("maximum number of ETD34 attempts exceeded")
        attempts += 1
        h = min(h, tf - t)
        if not t + h > t:
            raise RuntimeError(f"ETD34 step size {h:.3e} makes no progress at t={t!r}")
        at_floor = h <= h_floor * (1.0 + 1e-12)

        mv0 = _backend_matvecs(work_backend) if count_matvecs else None
        tic = time.perf_counter()
        try:
            high, err_vec, n5 = _etd34_trial(problem, t, y, h, work_backend, n1)
        except (LejaConvergenceError, KiopsConvergenceError, KrylovConvergenceError) as exc:
            # An iterative phi-action failure is a rejected time step, not a fatal
            # integration error. This follows the adaptive strategy advocated for
            # iterative exponential integrators: reduce h and retry.
            work = _attempt_work(count_matvecs, work_backend, mv0, tic)
            missing_work += int(math.isnan(work))
            work_failed.append(float(work))
            rejected += 1
            backend_failures += 1
            if at_floor:
                raise RuntimeError(
                    f"ETD34: matrix-function backend failed at the minimum step size {h:.3e} (t={t!r})"
                ) from exc
            h = max(h_floor, 0.5 * h)
            _check_budget("matrix-function backend failed", h, t, tf, attempts, options.max_steps, exc)
            continue
        nonlinear_evals += 4

        work = _attempt_work(count_matvecs, work_backend, mv0, tic)
        missing_work += int(math.isnan(work))

        finite = bool(np.all(np.isfinite(high)) and np.all(np.isfinite(err_vec)) and np.all(np.isfinite(n5)))
        err_norm = (
            _scaled_error_norm(err_vec, y, high, rtol=options.rtol, atol=options.atol, norm=options.norm)
            if finite else math.nan
        )
        if not math.isfinite(err_norm):
            work_failed.append(float(work))
            rejected += 1
            nonfinite += 1
            if at_floor:
                raise RuntimeError(f"ETD34: non-finite trial result at the minimum step size {h:.3e} (t={t!r})")
            h = max(h_floor, 0.5 * h)
            _check_budget("non-finite trial result", h, t, tf, attempts, options.max_steps)
            continue
        work_attempt.append(float(work))

        if err_norm == 0.0:
            h_acc = h * options.max_factor
        else:
            fac = options.safety * err_norm ** (-0.25)
            h_acc = h * min(options.max_factor, max(options.min_factor, fac))

        if err_norm <= 1.0:
            t += h
            y, n1 = high, n5
            ts.append(float(t)); ys.append(y.copy()); hs.append(float(h)); errs.append(float(err_norm))
            work_accept.append(float(work))
            h_next, mode = h_acc, "accuracy"
            if options.controller == "cost":
                hc = _cost_proposal(
                    h, work, prev_h, prev_work,
                    alpha=options.cost_alpha, beta=options.cost_beta,
                    lambd=options.cost_lambda, delta=options.cost_delta,
                )
                if hc is not None and hc < h_next:
                    h_next, mode = hc, "cost"
            modes.append(mode)
            prev_h, prev_work = float(h), float(work)
            h = max(h_floor, min(options.h_max, h_next))
        else:
            rejected += 1
            if at_floor:
                raise RuntimeError(
                    f"ETD34: error test failed at the minimum step size {h:.3e} (t={t!r}); "
                    "the requested tolerances cannot be met"
                )
            fac = options.safety * err_norm ** (-0.25)
            h = max(h_floor, h * min(1.0, max(options.min_factor, fac)))

    return Solution(
        t=np.asarray(ts), y=np.real_if_close(np.asarray(ys)),
        method="ETD34(Krogstad4/embedded3)", backend=f"adaptive-etd34:{backend.name}",
        step_size=float("nan"),
        stats={
            "adaptive": True, "embedded": True, "controller": options.controller,
            "cost_metric": options.cost_metric, "accepted_steps": len(hs),
            "rejected_steps": rejected, "attempted_steps": attempts,
            "step_sizes": hs, "error_norms": errs, "work_per_attempt": work_attempt,
            "work_per_accepted_step": work_accept, "work_per_failed_attempt": work_failed,
            "work_unit": "matvecs" if count_matvecs else "seconds",
            "work_missing_attempts": missing_work, "controller_modes": modes,
            "cost_limited_steps": sum(m == "cost" for m in modes),
            "backend_failure_rejections": backend_failures,
            "nonfinite_rejections": nonfinite,
            "minimum_step": h_floor,
            "rtol": options.rtol, "atol": options.atol, "action_tolerance": action_tol,
            "nonlinear_evals_estimate": nonlinear_evals,
            "nonlinear_evals": counter.calls,
            "backend_stats": getattr(work_backend, "stats", lambda: {})(),
        },
    )
