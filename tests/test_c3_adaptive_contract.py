"""C3: contract of the adaptive solvers (ETD34 and step doubling).

Covers option validation, termination at the minimum step after persistent
backend failures, error-test failures or non-finite trials, unresolvable step
sizes, rejection followed by acceptance, exact counts of nonlinear evaluations,
and the documented blindness of the ETD34 estimator to state-independent forcing.
"""

import math

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator

from pyexpint import (
    KROGSTAD, AdaptiveOptions, DiagonalBackend, ETD34Options, LejaBackend,
    SemilinearProblem, solve_adaptive, solve_etd34,
)


def logistic(T=1.0):
    exact = lambda t: np.array([1.0 / (1.0 + 1.5 * np.exp(t))])
    return SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, exact(0.0), (0.0, T),
                             exact_solution=exact), exact


def run_etd34(problem, backend=None, **opts):
    return solve_etd34(problem, backend or DiagonalBackend(), options=ETD34Options(**opts))


def run_doubling(problem, backend=None, **opts):
    return solve_adaptive(problem, KROGSTAD, backend or DiagonalBackend(), options=AdaptiveOptions(**opts))


SOLVERS = [pytest.param(run_etd34, id="etd34"), pytest.param(run_doubling, id="doubling")]

COMMON_INVALID = [
    dict(rtol=float("nan")), dict(rtol=0.0), dict(atol=-1.0), dict(atol=float("inf")),
    dict(h0=0.0), dict(h0=float("nan")), dict(h_min=-1.0), dict(h_min=float("nan")),
    dict(h_max=float("nan")), dict(h_min=1.0, h_max=0.5), dict(safety=0.0), dict(safety=float("nan")),
    dict(min_factor=0.0), dict(min_factor=1.5), dict(max_factor=0.5), dict(max_factor=float("inf")),
    dict(max_steps=0), dict(max_steps=2.5), dict(norm="l2"), dict(action_rtol_fraction=0.0),
    dict(action_tol_floor=0.0), dict(action_tol_floor=1e-4, action_tol_ceiling=1e-6),
]


@pytest.mark.parametrize("kwargs", COMMON_INVALID + [
    dict(controller="other"), dict(cost_metric="other"), dict(cost_alpha=float("nan")),
    dict(cost_lambda=0.5), dict(cost_delta=1.5)])
def test_etd34_options_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        ETD34Options(**kwargs)


@pytest.mark.parametrize("kwargs", COMMON_INVALID + [dict(effective_order=0.0), dict(effective_order=float("nan"))])
def test_adaptive_options_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        AdaptiveOptions(**kwargs)


def test_default_options_remain_valid():
    ETD34Options()
    AdaptiveOptions()


def test_backend_failures_are_rejections_followed_by_acceptance():
    lam = np.linspace(-200.0, 0.0, 50)
    problem = SemilinearProblem(sp.diags(lam, format="csr"), lambda t, y: -0.5 * y**3,
                                np.linspace(1.0, 0.5, 50), (0.0, 1.0))
    backend = LejaBackend(spectral_bounds=(-200.0, 0.0), max_degree=16, min_degree=2)
    sol = run_etd34(problem, backend, rtol=1e-6, atol=1e-9, h0=0.1)
    st = sol.stats
    assert st["backend_failure_rejections"] > 0 and st["accepted_steps"] > 0
    assert sol.t[-1] == pytest.approx(1.0, abs=1e-14)
    assert st["nonlinear_evals"] >= st["nonlinear_evals_estimate"]
    assert sum(st["work_per_attempt"]) + sum(st["work_per_failed_attempt"]) == st["backend_stats"]["matvecs"]
    reference = run_etd34(SemilinearProblem(lam, problem.nonlinear, problem.y0, problem.t_span),
                          rtol=1e-6, atol=1e-9, h0=0.1)
    assert np.max(np.abs(sol.y[-1] - reference.y[-1])) < 1e-5


def jordan_problem():
    J = np.array([[0.0, 1.0], [0.0, 0.0]])
    calls = {"matvecs": 0}

    def matvec(x):
        calls["matvecs"] += 1
        return J @ np.ravel(x)

    op = LinearOperator((2, 2), matvec=matvec, dtype=float)
    problem = SemilinearProblem(op, lambda t, y: 0.0 * y, np.array([0.0, 1.0]), (0.0, 1.0))
    return problem, calls


@pytest.mark.parametrize("h_min", [1e-3, 0.0])
def test_persistent_backend_failure_terminates_at_the_minimum_step(h_min):
    problem, calls = jordan_problem()
    with pytest.raises(RuntimeError, match="minimum step|max_steps"):
        run_etd34(problem, LejaBackend(spectral_bounds=(0.0, 0.0)), h_min=h_min, max_steps=2000)
    assert calls["matvecs"] < 200


@pytest.mark.parametrize("solver", SOLVERS)
def test_error_test_failure_at_h_min_terminates(solver):
    problem, _ = logistic()
    with pytest.raises(RuntimeError, match="error test failed at the minimum step"):
        solver(problem, rtol=1e-14, atol=1e-16, h0=0.1, h_min=0.1, max_steps=2000)


@pytest.mark.parametrize("solver", SOLVERS)
def test_persistent_nonfinite_trials_terminate(solver):
    problem = SemilinearProblem(np.array([-1.0]),
                                lambda t, y: y * y if t < 0.3 else np.array([np.nan]),
                                np.array([0.4]), (0.0, 1.0))
    with pytest.raises(RuntimeError, match="non-finite"):
        solver(problem, rtol=1e-6, atol=1e-9, h_min=1e-3, max_steps=2000)


def test_nonfinite_initial_nonlinear_term_is_rejected():
    problem = SemilinearProblem(np.array([-1.0]), lambda t, y: np.array([np.inf]), np.array([0.4]), (0.0, 1.0))
    with pytest.raises(ValueError, match="non-finite"):
        run_etd34(problem, max_steps=2000)


@pytest.mark.parametrize("solver", SOLVERS)
def test_unresolvable_step_size_is_reported_before_integrating(solver):
    t0 = 1e16
    problem = SemilinearProblem(np.array([-1.0]), lambda t, y: 0.0 * y, np.array([1.0]), (t0, t0 + 64.0))
    with pytest.raises(ValueError, match="smallest resolvable step"):
        solver(problem, h_max=0.5, max_steps=2000)


@pytest.mark.parametrize("solver", SOLVERS)
def test_rejection_followed_by_acceptance(solver):
    problem, exact = logistic()
    sol = solver(problem, rtol=1e-9, atol=1e-12, h0=1.0)
    st = sol.stats
    assert st["rejected_steps"] >= 1 and st["accepted_steps"] >= 1
    assert st["attempted_steps"] == st["accepted_steps"] + st["rejected_steps"]
    assert abs(sol.y[-1, 0] - exact(1.0)[0]) < 1e-7


@pytest.mark.parametrize("solver", SOLVERS)
def test_nonlinear_evaluations_are_counted_exactly(solver):
    problem, _ = logistic()
    sol = solver(problem, rtol=1e-8, atol=1e-11)
    assert sol.stats["nonlinear_evals"] == sol.stats["nonlinear_evals_estimate"]


def test_etd34_estimator_vanishes_for_state_independent_forcing():
    """Documented limitation of the published ETD34 estimator.

    For y' = -y + cos(t) the estimate h b_4(hL)(N(t+h, Y_4) - N(t+h, y_{n+1})) is zero
    on every step, so the controller runs at h_max and the tolerance is not met,
    whereas step doubling with the same Krogstad scheme meets it.
    """
    exact = lambda t: np.array([(math.cos(t) + math.sin(t)) / 2.0])
    problem = SemilinearProblem(np.array([-1.0]), lambda t, y: np.array([math.cos(t)]), exact(0.0),
                                (0.0, 5.0), exact_solution=exact)
    embedded = run_etd34(problem, rtol=1e-10, atol=1e-12, h_max=0.5)
    assert max(embedded.stats["error_norms"]) <= 1e-6
    assert abs(embedded.y[-1, 0] - exact(5.0)[0]) > 1e-6
    doubling = run_doubling(problem, rtol=1e-10, atol=1e-12, h_max=0.5)
    assert abs(doubling.y[-1, 0] - exact(5.0)[0]) < 1e-8
