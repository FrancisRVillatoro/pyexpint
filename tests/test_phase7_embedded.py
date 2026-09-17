import numpy as np
from numpy.testing import assert_allclose

from pyexpint import (
    DiagonalBackend,
    ETD34Options,
    KROGSTAD,
    SemilinearProblem,
    solve_etd34,
    solve_fixed,
)
from pyexpint.embedded import _cost_proposal, _etd34_trial


def riccati_exact(t):
    return np.array([1.0 / (1.0 + 4.0*np.exp(t))])


def riccati_problem(T=1.0):
    return SemilinearProblem(
        np.array([-1.0]),
        lambda t, y: y*y,
        np.array([0.2]),
        (0.0, T),
        exact_solution=riccati_exact,
    )


def test_etd34_high_candidate_is_krogstad_step():
    p = riccati_problem(T=0.1)
    h = 0.1
    y0 = p.y0.copy()
    n1 = p.nonlinear(0.0, y0)
    high, err, _ = _etd34_trial(p, 0.0, y0, h, DiagonalBackend(), n1)
    ref = solve_fixed(p, KROGSTAD, h, DiagonalBackend()).y[-1]
    assert_allclose(high, ref, rtol=2e-14, atol=2e-15)
    assert np.linalg.norm(err) > 0


def test_etd34_adaptive_accuracy_and_fsal_work():
    p = riccati_problem(T=2.0)
    sol = solve_etd34(
        p,
        DiagonalBackend(),
        options=ETD34Options(rtol=1e-7, atol=1e-10, h0=0.2, h_max=0.5),
    )
    err = abs(sol.y[-1,0] - riccati_exact(2.0)[0])
    assert err < 8e-8
    # Initial N plus exactly 4 new N evaluations per attempt.
    assert sol.stats["nonlinear_evals_estimate"] == 1 + 4*sol.stats["attempted_steps"]


def test_cost_controller_formula_direction():
    # If work/unit time increases with h, the cost proposal should reduce h.
    h = _cost_proposal(
        0.2, 40.0, 0.1, 10.0,
        alpha=0.65241444, beta=0.26862269,
        lambd=1.37412002, delta=0.64446017,
    )
    assert h is not None
    assert h < 0.2

    # If work/unit time decreases with h, proposal should increase h.
    h2 = _cost_proposal(
        0.2, 15.0, 0.1, 10.0,
        alpha=0.65241444, beta=0.26862269,
        lambd=1.37412002, delta=0.64446017,
    )
    assert h2 is not None
    assert h2 > 0.2


def test_etd34_embedded_estimator_has_fourth_power_local_scaling():
    p = riccati_problem(T=0.2)
    hs = np.array([0.2, 0.1, 0.05, 0.025])
    est = []
    for h in hs:
        _, e, _ = _etd34_trial(p, 0.0, p.y0, float(h), DiagonalBackend(), p.nonlinear(0.0,p.y0))
        est.append(abs(e[0]))
    slopes = np.log2(np.array(est[:-1]) / np.array(est[1:]))
    # The high-low difference of a 4(3) embedded pair is O(h^4).
    assert slopes[-1] > 3.8
    assert slopes[-1] < 4.2
