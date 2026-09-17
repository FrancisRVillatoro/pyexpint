from __future__ import annotations

import math
import numpy as np

from .core import SemilinearProblem, Solution, ExternalState
from .methods import MethodSpec, HOCHOST4
from .startup import ExactStartup, OneStepStartup, StartupPolicy


def _sum_actions(exprs, vectors, ctx, shape):
    # Matrix-free backends may fuse a sum of phi-actions with distinct right-hand
    # sides into one augmented Krylov projection.
    fused = getattr(ctx, "sum_operator_actions", None)
    if fused is not None:
        value = fused(exprs, vectors)
        if value is not None:
            return np.real_if_close(value)

    out = np.zeros(shape, dtype=np.result_type(*[v.dtype for v in vectors], np.complex128))
    for expr, vec in zip(exprs, vectors):
        if expr is not None:
            out = out + expr.apply(ctx, vec)
    return np.real_if_close(out)


def step_external(
    problem: SemilinearProblem,
    method: MethodSpec,
    state: ExternalState,
    h: float,
    backend,
) -> ExternalState:
    """Advance one explicit exponential GLM step."""
    method.validate()
    X = np.asarray(state.values)
    r = method.outputs
    if X.shape != (r, problem.y0.size):
        raise ValueError(f"External state shape {X.shape} incompatible with method r={r}.")

    ctx = backend.bind(problem.linear_operator, h)
    s = method.stages
    G: list[np.ndarray] = []

    for i in range(s):
        Yi = _sum_actions(method.U[i], list(X), ctx, X[0].shape)
        if i:
            Yi = Yi + _sum_actions(method.A[i][:i], G, ctx, X[0].shape)
        Fi = np.asarray(problem.nonlinear(state.t + method.c[i]*h, np.asarray(np.real_if_close(Yi))))
        if Fi.shape != X[0].shape:
            raise ValueError("nonlinear(t,y) must return the same state shape.")
        G.append(h * Fi)

    Xnew = []
    for out_i in range(r):
        val = _sum_actions(method.V[out_i], list(X), ctx, X[0].shape)
        val = val + _sum_actions(method.B[out_i], G, ctx, X[0].shape)
        Xnew.append(np.asarray(np.real_if_close(val)))

    return ExternalState(state.t + h, np.stack(Xnew, axis=0))


def _step_one_step(problem, method, t, y, h, backend):
    if method.outputs != 1:
        raise ValueError("_step_one_step requires r=1.")
    state = ExternalState(float(t), np.stack([np.asarray(y)], axis=0))
    return step_external(problem, method, state, h, backend).y


def _select_startup(problem, method, startup):
    if method.outputs == 1:
        # No warm-up is actually needed; ExactStartup is convenient and exact at t0.
        if problem.exact_solution is not None:
            return ExactStartup()
        return OneStepStartup(HOCHOST4)
    if startup is not None:
        return startup
    if problem.exact_solution is not None:
        return ExactStartup()
    return OneStepStartup(HOCHOST4)


def solve_fixed(
    problem: SemilinearProblem,
    method: MethodSpec,
    h: float,
    backend,
    *,
    startup: StartupPolicy | None = None,
) -> Solution:
    """Integrate an explicit exponential GLM at constant step size.

    For r>1 methods, the default startup uses exact solution values when the
    problem supplies them and otherwise uses HochOst4.  A custom StartupPolicy
    can be injected explicitly.
    """
    if h <= 0:
        raise ValueError("h must be positive.")
    method.validate()
    reset_backend_stats = getattr(backend, "reset_stats", None)
    if reset_backend_stats is not None:
        reset_backend_stats()

    t0, tf = map(float, problem.t_span)
    span = tf - t0
    nsteps = int(round(span / h))
    if not math.isclose(nsteps*h, span, rel_tol=2e-13, abs_tol=2e-14):
        raise ValueError("solve_fixed requires h to divide the integration interval exactly.")

    required = method.history_length
    policy = _select_startup(problem, method, startup)

    # If the whole requested interval is shorter than the history warm-up, use the
    # selected one-step starter for the requested interval.  This avoids inventing
    # an incomplete external state that will never be used.
    if nsteps < required:
        starter = getattr(policy, "starter", HOCHOST4)
        if problem.exact_solution is not None and isinstance(policy, ExactStartup):
            ts = t0 + h*np.arange(nsteps+1)
            ys = np.asarray([problem.exact_solution(t) for t in ts])
            return Solution(ts, ys, method.name, backend.name, h, {
                "steps": nsteps, "main_steps": 0, "startup_steps": nsteps,
                "startup_policy": "exact-short-interval", "starter_method": None,
                "nonlinear_evals_estimate": 0,
            })
        short_problem = SemilinearProblem(problem.linear_operator, problem.nonlinear, problem.y0, problem.t_span, problem.exact_solution)
        return solve_fixed(short_problem, starter, h, backend)

    init = policy.initialize(problem, method, h, backend, _step_one_step)
    state = init.state
    ts = list(np.asarray(init.t, dtype=float))
    ys = [np.asarray(y) for y in init.y]

    main_steps = nsteps - required
    for _ in range(main_steps):
        state = step_external(problem, method, state, h, backend)
        ts.append(state.t)
        ys.append(np.asarray(state.y))

    return Solution(
        t=np.asarray(ts),
        y=np.real_if_close(np.asarray(ys)),
        method=method.name,
        backend=backend.name,
        step_size=h,
        stats={
            "steps": nsteps,
            "main_steps": main_steps,
            "startup_steps": required,
            "startup_policy": init.policy,
            "starter_method": init.starter_method,
            "nonlinear_evals_estimate": required * (0 if init.policy == "exact" else HOCHOST4.nonlinear_evals_per_step)
                + main_steps * (method.nonlinear_evals_per_step or method.stages),
            "external_outputs": method.outputs,
            "backend_stats": getattr(backend, "stats", lambda: {})(),
        },
    )
