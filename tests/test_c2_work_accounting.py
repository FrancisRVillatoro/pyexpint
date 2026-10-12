"""C2: authoritative work accounting in the adaptive ETD34 solver.

The matrix-vector work of an attempt is the increment of the top-level
``"matvecs"`` entry of the backend statistics.  Breakdowns are never added to it,
a missing counter is recorded as missing (NaN) rather than replaced by seconds,
and the recorded increments add up to the backend total.
"""

import math

import numpy as np
import pytest
import scipy.sparse as sp

from pyexpint import (
    ABNORSETT3, KROGSTAD, AutoBackend, DiagonalBackend, ETD34Options, KiopsBackend,
    OneStepStartup, SemilinearProblem, solve_etd34, solve_fixed,
)

def heat_problem(n=64, nu=0.01, T=2.0):
    dx = 1.0 / (n + 1)
    x = np.linspace(dx, 1.0 - dx, n)
    L = (nu / dx**2) * sp.diags([np.ones(n - 1), -2.0 * np.ones(n), np.ones(n - 1)],
                                [-1, 0, 1], format="csr")
    return SemilinearProblem(L, lambda t, y: 0.5 * y * (1.0 - y), 0.5 * np.sin(np.pi * x), (0.0, T))


def recorded_total(stats):
    return sum(stats["work_per_attempt"]) + sum(stats.get("work_per_failed_attempt", []))


def test_direct_backend_increments_add_up_to_backend_total():
    sol = solve_etd34(heat_problem(), KiopsBackend(tol=1e-10), options=ETD34Options(rtol=1e-5, atol=1e-8))
    works = sol.stats["work_per_attempt"]
    assert works and all(w >= 0 and float(w).is_integer() for w in works)
    assert recorded_total(sol.stats) == sol.stats["backend_stats"]["matvecs"]


def test_auto_alternating_between_kiops_and_leja_is_counted_once():
    auto = AutoBackend(tol=1e-10, leja_min_size=64, leja_width_threshold=20.0)
    sol = solve_etd34(heat_problem(), auto, options=ETD34Options(rtol=1e-4, atol=1e-8, h0=0.05))
    selections = sol.stats["backend_stats"]["selection_counts"]
    assert selections.get("kiops", 0) > 0 and selections.get("leja", 0) > 0
    works = sol.stats["work_per_attempt"]
    assert all(w >= 0 and float(w).is_integer() for w in works)
    assert recorded_total(sol.stats) == sol.stats["backend_stats"]["matvecs"]


def test_auto_counter_is_authoritative_and_monotone_under_manual_alternation():
    from pyexpint.embedded import _backend_matvecs

    n = 40
    dx = 1.0 / (n + 1)
    A = (1.0 / dx**2) * sp.diags([np.ones(n - 1), -2.0 * np.ones(n), np.ones(n - 1)],
                                 [-1, 0, 1], format="csr")
    v = np.sin(np.pi * np.linspace(dx, 1.0 - dx, n))
    auto = AutoBackend(tol=1e-10, leja_min_size=n, leja_width_threshold=20.0)
    width = 4.0 / dx**2          # Gershgorin width of A
    h_kiops, h_leja = 40.0 / width, 10.0 / width
    previous = _backend_matvecs(auto)
    assert previous == 0
    for h, engine in [(h_kiops, "kiops"), (h_leja, "leja"), (h_kiops, "kiops"), (h_leja, "leja")]:
        sub = getattr(auto, engine)
        before_sub = sub.stats()["matvecs"]
        auto.bind(A, h).phi_action(1, 1.0, v)
        assert auto.stats()["last_selected"] == engine
        current = _backend_matvecs(auto)
        assert current - previous == sub.stats()["matvecs"] - before_sub > 0
        previous = current
    assert previous == auto.kiops.stats()["matvecs"] + auto.leja.stats()["matvecs"]


def test_backend_without_counter_records_missing_work_not_seconds():
    p = SemilinearProblem(np.array([-1.0, -2.0]), lambda t, y: y * y, np.array([0.2, 0.1]), (0.0, 1.0))
    sol = solve_etd34(p, DiagonalBackend(), options=ETD34Options(rtol=1e-6, atol=1e-9))
    assert sol.stats["work_unit"] == "matvecs"
    assert all(math.isnan(w) for w in sol.stats["work_per_attempt"])
    assert sol.stats["work_missing_attempts"] == sol.stats["attempted_steps"]


def test_cost_controller_on_matvecs_requires_a_counting_backend():
    p = SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, np.array([0.2]), (0.0, 1.0))
    with pytest.raises(ValueError, match="matvecs"):
        solve_etd34(p, DiagonalBackend(), options=ETD34Options(controller="cost", cost_metric="matvecs"))
    sol = solve_etd34(p, DiagonalBackend(), options=ETD34Options(controller="cost", cost_metric="wall"))
    assert sol.stats["work_unit"] == "seconds"
    assert all(w > 0 and math.isfinite(w) for w in sol.stats["work_per_attempt"])


def test_startup_work_estimate_uses_the_actual_starter():
    p = SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, np.array([0.4]), (0.0, 1.0))
    sol = solve_fixed(p, ABNORSETT3, 0.1, DiagonalBackend(), startup=OneStepStartup(KROGSTAD))
    # Two startup intervals with Krogstad (4 evaluations each) and eight main steps (1 each).
    assert sol.stats["nonlinear_evals_estimate"] == 2 * 4 + 8 * 1
