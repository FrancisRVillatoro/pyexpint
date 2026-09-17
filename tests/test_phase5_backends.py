import numpy as np
from numpy.testing import assert_allclose
from scipy.sparse import diags
from scipy.sparse.linalg import LinearOperator

from pyexpint import (
    AutoBackend,
    DiagonalBackend,
    KiopsBackend,
    LejaBackend,
    SemilinearProblem,
    get_method,
    solve_fixed,
)


def _diag_op(lam):
    return LinearOperator((lam.size, lam.size), matvec=lambda x: lam*x, dtype=float)


def test_kiops_phi_actions_against_diagonal():
    lam = np.linspace(-20.0, -0.1, 64)
    v = np.cos(np.arange(lam.size))
    ref = DiagonalBackend().bind(lam, 0.1)
    kb = KiopsBackend(tol=2e-11, m_init=10, m_min=6, m_max=40)
    ctx = kb.bind(_diag_op(lam), 0.1)
    for k in range(4):
        assert_allclose(ctx.phi_action(k, 1.0, v), ref.phi_action(k, 1.0, v), rtol=5e-10, atol=2e-11)
    st = kb.stats()
    assert st["matvecs"] > 0
    assert st["accepted_substeps"] > 0
    assert st["orth_len"] == 2


def test_kiops_distinct_rhs_combination():
    lam = np.linspace(-8.0, -0.2, 48)
    op = _diag_op(lam)
    h = 0.15
    rng = np.random.default_rng(2)
    vecs = {k: rng.standard_normal(lam.size) for k in range(4)}
    kb = KiopsBackend(tol=1e-11, m_init=10, m_min=6, m_max=40)
    got = kb.bind(op, h).phi_linear_combination_action(vecs, scale=1.0)
    d = DiagonalBackend().bind(lam, h)
    ref = sum(d.phi_action(k, 1.0, v) for k, v in vecs.items())
    assert_allclose(got, ref, rtol=8e-10, atol=2e-10)


def test_leja_phi_actions_against_diagonal():
    lam = np.linspace(-20.0, -0.1, 64)
    v = np.sin(np.arange(lam.size))
    h = 0.1
    lb = LejaBackend(tol=1e-10, spectral_bounds=(lam.min(), lam.max()), max_degree=70, target_width=8.0)
    ctx = lb.bind(_diag_op(lam), h)
    d = DiagonalBackend().bind(lam, h)
    for k in range(4):
        assert_allclose(ctx.phi_action(k, 1.0, v), d.phi_action(k, 1.0, v), rtol=2e-8, atol=2e-10)
    st = lb.stats()
    assert st["matvecs"] > 0
    assert st["max_degree_used"] <= 70


def test_phase5_backends_integrate_krogstad():
    n = 80
    lam = np.linspace(-12.0, -0.2, n)
    y0 = 0.1 + 0.02*np.sin(np.linspace(0, np.pi, n))
    T, h = 0.2, 0.05
    f = lambda t, y: 0.1*y*y
    pref = SemilinearProblem(lam, f, y0, (0.0, T))
    pop = SemilinearProblem(_diag_op(lam), f, y0, (0.0, T))
    ref = solve_fixed(pref, get_method("Krogstad"), h, DiagonalBackend()).y[-1]

    kb = KiopsBackend(tol=2e-10, m_init=10, m_min=6, m_max=40)
    gotk = solve_fixed(pop, get_method("Krogstad"), h, kb).y[-1]
    assert_allclose(gotk, ref, rtol=3e-8, atol=3e-10)

    lb = LejaBackend(tol=1e-10, spectral_bounds=(lam.min(), lam.max()), max_degree=70, target_width=8.0)
    gotl = solve_fixed(pop, get_method("Krogstad"), h, lb).y[-1]
    assert_allclose(gotl, ref, rtol=2e-7, atol=2e-9)


def test_auto_backend_selection():
    auto = AutoBackend(tol=1e-9, dense_cutoff=32, leja_min_size=64, leja_width_threshold=200.0)
    # Diagonal array.
    auto.bind(np.array([-2.0, -1.0]), 0.1)
    assert auto.stats()["last_selected"] == "diagonal"

    # Small dense.
    auto.bind(np.diag([-2.0, -1.0]), 0.1)
    assert auto.stats()["last_selected"] == "dense"

    # Symmetric sparse with moderate scaled width -> Leja.
    A = diags([np.ones(79), -2*np.ones(80), np.ones(79)], [-1,0,1], format="csr")
    auto.bind(A, 0.05)
    assert auto.stats()["last_selected"] == "leja"

    # Generic LinearOperator -> KIOPS-style.
    op = LinearOperator((20,20), matvec=lambda x: -x, dtype=float)
    auto.bind(op, 0.05)
    assert auto.stats()["last_selected"] == "kiops"
