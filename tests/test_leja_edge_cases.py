import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.sparse.linalg import LinearOperator

from pyexpint import LejaBackend, LejaConvergenceError


def _diag_op(lam):
    lam = np.asarray(lam, dtype=float)
    return LinearOperator(
        (lam.size, lam.size),
        matvec=lambda x: lam * x,
        dtype=float,
    )


def test_leja_is_invariant_under_equivalent_operator_time_rescaling():
    """
    Equivalent representations of the same matrix argument h*A
    must give the same exponential action.
    """
    lam1 = np.array([-1.0, 0.0])
    h1 = 1.0

    lam2 = 1.0e-14 * lam1
    h2 = 1.0e14

    v = np.array([1.0, 1.0])
    reference = np.array([np.exp(-1.0), 1.0])

    b1 = LejaBackend(
        tol=1e-12,
        spectral_bounds=(lam1.min(), lam1.max()),
        max_degree=80,
    )
    b2 = LejaBackend(
        tol=1e-12,
        spectral_bounds=(lam2.min(), lam2.max()),
        max_degree=80,
    )

    got1 = b1.bind(_diag_op(lam1), h1).phi_action(0, 1.0, v)
    got2 = b2.bind(_diag_op(lam2), h2).phi_action(0, 1.0, v)

    assert_allclose(got1, reference, rtol=2e-12, atol=2e-13)
    assert_allclose(got2, reference, rtol=2e-12, atol=2e-13)
    assert_allclose(got2, got1, rtol=2e-12, atol=2e-13)


def test_zero_width_bounds_must_not_silently_scalarize_a_nonscalar_operator():
    """
    A zero-width spectral hint must not silently replace a nonscalar
    operator by center*I.

    For J=[[0,1],[0,0]], exp(J)[0,1]^T = [1,1]^T.
    The current Leja backend need not support this nonnormal case,
    but it must fail explicitly rather than return an incorrect action.
    """
    J = np.array([
        [0.0, 1.0],
        [0.0, 0.0],
    ])
    v = np.array([0.0, 1.0])

    op = LinearOperator(
        (2, 2),
        matvec=lambda x: J @ x,
        dtype=float,
    )

    backend = LejaBackend(
        tol=1e-12,
        spectral_bounds=(0.0, 0.0),
        max_degree=80,
    )

    with pytest.raises((ValueError, LejaConvergenceError)):
        backend.bind(op, 1.0).phi_action(0, 1.0, v)


def test_zero_width_bounds_remain_valid_for_true_scalar_operator():
    """
    Preserve the legitimate scalar-operator case A=lambda*I.
    """
    lam = np.array([-2.0, -2.0, -2.0])
    h = 0.4
    v = np.array([1.0, -2.0, 0.5])

    backend = LejaBackend(
        tol=1e-12,
        spectral_bounds=(-2.0, -2.0),
        max_degree=80,
    )

    got = backend.bind(_diag_op(lam), h).phi_action(0, 1.0, v)
    reference = np.exp(-0.8) * v

    assert_allclose(got, reference, rtol=2e-13, atol=2e-14)
