from __future__ import annotations
from dataclasses import dataclass
import math, time
from typing import Any
import numpy as np

from .core import SemilinearProblem, Solution
from .methods import KROGSTAD
from .adaptive import _clone_backend_with_tol, _scaled_error_norm
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
        if self.rtol <= 0 or self.atol < 0:
            raise ValueError("require rtol>0 and atol>=0")
        if self.h0 is not None and self.h0 <= 0:
            raise ValueError("h0 must be positive")
        if self.h_min < 0 or self.h_max <= 0 or self.h_min > self.h_max:
            raise ValueError("invalid h_min/h_max")
        if self.controller not in {"accuracy", "cost"}:
            raise ValueError("controller must be accuracy or cost")
        if self.cost_metric not in {"matvecs", "wall"}:
            raise ValueError("cost_metric must be matvecs or wall")
        if self.norm not in {"rms", "inf"}:
            raise ValueError("norm must be rms or inf")


def _numeric_stat_tree(stats: Any, key: str) -> float:
    if not isinstance(stats, dict):
        return 0.0
    total = 0.0
    for k, v in stats.items():
        if k == key and isinstance(v, (int, float, np.integer, np.floating)) and np.isfinite(v):
            total += float(v)
        elif isinstance(v, dict):
            total += _numeric_stat_tree(v, key)
    return total


def _backend_work(backend) -> float:
    return _numeric_stat_tree(getattr(backend, "stats", lambda: {})(), "matvecs")


def _cost_proposal(h_n, work_n, h_prev, work_prev, *, alpha, beta, lambd, delta):
    if h_prev is None or work_prev is None or min(h_n, h_prev, work_n, work_prev) <= 0:
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
    """Adaptive Krogstad fourth-order ETD with embedded third-order estimator."""
    if options is None:
        options = ETD34Options(**overrides)
    elif overrides:
        raise ValueError("pass either ETD34Options or keyword overrides, not both")

    t0, tf = map(float, problem.t_span)
    span = tf - t0
    h = options.h0 if options.h0 is not None else span / 16.0
    h = min(h, options.h_max, span)

    action_tol = min(
        options.action_tol_ceiling,
        max(options.action_tol_floor, options.action_rtol_fraction * options.rtol),
    )
    work_backend = _clone_backend_with_tol(backend, action_tol)
    if hasattr(work_backend, "reset_stats"):
        work_backend.reset_stats()

    t, y = t0, np.array(problem.y0, copy=True)
    n1 = np.asarray(problem.nonlinear(t, y))
    nonlinear_evals = 1
    ts, ys, hs, errs = [t], [y.copy()], [], []
    work_attempt, work_accept, modes = [], [], []
    rejected = attempts = backend_failures = 0
    prev_h = prev_work = None

    while t < tf:
        if attempts >= options.max_steps:
            raise RuntimeError("maximum number of ETD34 attempts exceeded")
        attempts += 1
        h = min(h, tf - t)

        mv0 = _backend_work(work_backend)
        tic = time.perf_counter()
        try:
            high, err_vec, n5 = _etd34_trial(problem, t, y, h, work_backend, n1)
        except (LejaConvergenceError, KiopsConvergenceError, KrylovConvergenceError):
            # An iterative phi-action failure is a rejected time step, not a fatal
            # integration error. This follows the adaptive strategy advocated for
            # iterative exponential integrators: reduce h and retry.
            wall = time.perf_counter() - tic
            rejected += 1
            backend_failures += 1
            h *= 0.5
            if options.h_min > 0:
                h = max(options.h_min, h)
            continue
        wall = time.perf_counter() - tic
        mv1 = _backend_work(work_backend)
        nonlinear_evals += 4

        work = (mv1 - mv0) if options.cost_metric == "matvecs" else wall
        if options.cost_metric == "matvecs" and work <= 0:
            work = wall
        work_attempt.append(float(work))

        err_norm = _scaled_error_norm(err_vec, y, high, rtol=options.rtol, atol=options.atol, norm=options.norm)
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
            h = min(options.h_max, h_next)
            if options.h_min > 0:
                h = max(options.h_min, h)
        else:
            rejected += 1
            fac = options.safety * err_norm ** (-0.25)
            h *= min(1.0, max(options.min_factor, fac))
            if options.h_min > 0:
                h = max(options.h_min, h)

    return Solution(
        t=np.asarray(ts), y=np.real_if_close(np.asarray(ys)),
        method="ETD34(Krogstad4/embedded3)", backend=f"adaptive-etd34:{backend.name}",
        step_size=float("nan"),
        stats={
            "adaptive": True, "embedded": True, "controller": options.controller,
            "cost_metric": options.cost_metric, "accepted_steps": len(hs),
            "rejected_steps": rejected, "attempted_steps": attempts,
            "step_sizes": hs, "error_norms": errs, "work_per_attempt": work_attempt,
            "work_per_accepted_step": work_accept, "controller_modes": modes,
            "cost_limited_steps": sum(m == "cost" for m in modes),
            "backend_failure_rejections": backend_failures,
            "rtol": options.rtol, "atol": options.atol, "action_tolerance": action_tol,
            "nonlinear_evals_estimate": nonlinear_evals,
            "backend_stats": getattr(work_backend, "stats", lambda: {})(),
        },
    )
