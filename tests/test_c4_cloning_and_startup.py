"""C4: backend cloning in the adaptive solvers and end-to-end order with numerical startup."""

import math

import numpy as np
import pytest

from pyexpint import (
    KROGSTAD, PEC726, AdaptiveOptions, CalibratedAutoBackend, DiagonalBackend, ETD34Options,
    ExactStartup, OneStepStartup, SelectorCalibration, SemilinearProblem, HOCHOST4,
    solve_adaptive, solve_etd34, solve_fixed,
)
from pyexpint.adaptive import _clone_backend_with_tol


def logistic(T=1.0):
    exact = lambda t: np.array([1.0 / (1.0 + 1.5 * np.exp(t))])
    return SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, exact(0.0), (0.0, T),
                             exact_solution=exact), exact


CALIBRATION = SelectorCalibration(leja_min_size=1024, leja_width_threshold=55.0, dense_cutoff=64,
                                  training_cases=12, machine_label="test-machine")


def test_calibrated_auto_keeps_type_calibration_and_thresholds_when_cloned():
    backend = CalibratedAutoBackend(CALIBRATION, tol=1e-8, leja_target_width=10.0)
    backend.leja_width_threshold = 60.0          # a later manual adjustment must survive
    clone = _clone_backend_with_tol(backend, 1e-11)
    assert type(clone) is CalibratedAutoBackend and clone.name == "auto-calibrated"
    assert clone.calibration == CALIBRATION
    assert (clone.dense_cutoff, clone.leja_min_size, clone.leja_width_threshold) == (64, 1024, 60.0)
    assert clone.tol == pytest.approx(1e-11) and clone.leja.options.target_width == 10.0


def test_calibrated_auto_provenance_reaches_the_solution_statistics():
    p, _ = logistic()
    sol = solve_etd34(p, CalibratedAutoBackend(CALIBRATION), options=ETD34Options(rtol=1e-6))
    assert sol.backend == "adaptive-etd34:auto-calibrated"
    assert sol.stats["backend_stats"]["calibration"]["machine_label"] == "test-machine"


class ExternalDiagonal:
    """Minimal backend outside PyEXPINT, implementing the tolerance hook."""

    name = "external-diagonal"

    def __init__(self, tol=None, log=None):
        self.tol = tol
        self.log = [] if log is None else log
        self.inner = DiagonalBackend()

    def bind(self, linear_operator, h):
        return self.inner.bind(linear_operator, h)

    def reset_stats(self):
        pass

    def stats(self):
        return {}

    def with_tolerance(self, tol):
        self.log.append(tol)
        return ExternalDiagonal(tol, self.log)


@pytest.mark.parametrize("solver", ["etd34", "doubling"])
def test_external_backend_with_tolerance_hook_is_admitted(solver):
    p, _ = logistic()
    external = ExternalDiagonal()
    if solver == "etd34":
        run = lambda b: solve_etd34(p, b, options=ETD34Options(rtol=1e-7, action_rtol_fraction=0.01))
    else:
        run = lambda b: solve_adaptive(p, KROGSTAD, b, options=AdaptiveOptions(rtol=1e-7, action_rtol_fraction=0.01))
    got, ref = run(external), run(DiagonalBackend())
    np.testing.assert_array_equal(got.y, ref.y)
    assert external.log == [pytest.approx(1e-9)]


def test_backend_without_hook_is_rejected_with_guidance():
    class Bare:
        name = "bare"

        def bind(self, linear_operator, h):
            return DiagonalBackend().bind(linear_operator, h)

    p, _ = logistic()
    with pytest.raises(TypeError, match="with_tolerance"):
        solve_etd34(p, Bare())


def test_decreasing_matvec_counter_is_reported():
    class Decreasing(ExternalDiagonal):
        count = 10**6

        def stats(self):
            Decreasing.count -= 1
            return {"matvecs": Decreasing.count}

        def with_tolerance(self, tol):
            return Decreasing(tol)

    p, _ = logistic()
    with pytest.raises(RuntimeError, match="counter decreased"):
        solve_etd34(p, Decreasing())


def test_default_startup_limits_the_end_to_end_order_to_five():
    """PEC726 (order 7) with one HochOst4 step per startup interval converges with order five."""
    p, exact = logistic()

    def error(h, startup):
        return abs(solve_fixed(p, PEC726, h, DiagonalBackend(), startup=startup).y[-1, 0] - exact(1.0)[0])

    e_num = [error(h, OneStepStartup(HOCHOST4)) for h in (0.05, 0.025)]
    e_exact = [error(h, ExactStartup()) for h in (0.05, 0.025)]
    slope_num = math.log2(e_num[0] / e_num[1])
    slope_exact = math.log2(e_exact[0] / e_exact[1])
    assert 4.0 < slope_num < 5.5 < 6.0 < slope_exact
    assert e_num[1] > 10.0 * e_exact[1]
