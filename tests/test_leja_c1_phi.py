"""
C1 regressions for the real-Leja backend: phi_k actions for k = 0, 1, 2, 3.

Every reference value is computed independently of PyEXPINT.  For
W = [[A, v e_1^T], [0, J_k]], with J_k the k x k upper shift matrix, the last
column of the top-right block of expm(W) equals phi_k(A) v.

The tests cover the defect found in v0.9.0 (a zero-width shortcut whose
threshold ignored h) and its neighbourhood:

* accuracy and argument semantics of phi_action(k, sigma, v) on a normal
  operator, compared with phi_k(sigma*h*A) v;
* invariance under the reciprocal rescaling (s*A, h/s) for every phi_k;
* zero-width bounds on a genuinely scalar operator (the legitimate shortcut);
* zero-width bounds on a Jordan block: exact result or explicit failure,
  never a silently scalarized action; exact result on its eigenvector;
* an operator equal to c*I only up to rounding, with zero or tight bounds.
"""

import math

import numpy as np
import pytest
from scipy.linalg import expm
from scipy.sparse.linalg import LinearOperator

from pyexpint import LejaBackend, LejaConvergenceError

KS = (0, 1, 2, 3)
BACKEND_TOL = 1e-12
CHECK = 1e-9  # relative to max(1, ||reference||)
EXPLICIT_FAILURES = (ValueError, LejaConvergenceError)


def phi_ref(A, v, k):
    """phi_k(A) v from the exponential of an augmented matrix."""
    A = np.atleast_2d(np.asarray(A, dtype=float))
    v = np.asarray(v, dtype=float)
    n = A.shape[0]
    if k == 0:
        return expm(A) @ v
    W = np.zeros((n + k, n + k))
    W[:n, :n] = A
    W[:n, n] = v
    for j in range(k - 1):
        W[n + j, n + j + 1] = 1.0
    return expm(W)[:n, n + k - 1]


def phi_scalar(z, k):
    return phi_ref([[z]], [1.0], k)[0]


def matrix_op(M):
    M = np.asarray(M, dtype=float)
    return LinearOperator(M.shape, matvec=lambda x: M @ np.ravel(x), dtype=float)


def leja(bounds):
    return LejaBackend(tol=BACKEND_TOL, spectral_bounds=bounds, max_degree=80)


def rel_err(got, ref):
    got = np.asarray(got)
    assert got.shape == ref.shape, f"shape {got.shape} differs from {ref.shape}"
    assert np.all(np.isfinite(got)), "the action contains non-finite entries"
    return float(np.linalg.norm(got - ref) / max(1.0, np.linalg.norm(ref)))


# Normal operator: accuracy and meaning of the sigma argument.
LAM9 = np.linspace(-4.0, 0.0, 9)
V9 = np.random.default_rng(20261001).standard_normal(9)


@pytest.mark.parametrize("sigma", [1.0, 0.5, 1.0 / 3.0])
@pytest.mark.parametrize("k", KS)
def test_phi_action_matches_dense_reference(k, sigma):
    h = 0.7
    A = np.diag(LAM9)
    got = leja((LAM9.min(), LAM9.max())).bind(matrix_op(A), h).phi_action(k, sigma, V9)
    assert rel_err(got, phi_ref(sigma * h * A, V9, k)) <= CHECK


# Reciprocal rescaling: (s*A, h/s) is the same matrix argument for every s > 0.
LAM4 = np.array([-1.0, -0.6, -0.25, 0.0])
V4 = np.array([1.0, -0.5, 2.0, 0.75])


@pytest.mark.parametrize("s", [1e-14, 1e-7, 1.0, 1e7, 1e14])
@pytest.mark.parametrize("k", KS)
def test_phi_action_is_invariant_under_reciprocal_rescaling(k, s):
    A = s * np.diag(LAM4)
    bounds = (s * LAM4.min(), s * LAM4.max())
    got = leja(bounds).bind(matrix_op(A), 1.0 / s).phi_action(k, 1.0, V4)
    assert rel_err(got, phi_ref(np.diag(LAM4), V4, k)) <= CHECK


# Zero-width bounds on a genuinely scalar operator: the shortcut must survive.
@pytest.mark.parametrize("c", [-2.0, 0.0])
@pytest.mark.parametrize("sigma", [1.0, 0.5])
@pytest.mark.parametrize("k", KS)
def test_zero_width_bounds_on_scalar_operator(k, sigma, c):
    h = 0.4
    v = np.array([1.0, -2.0, 0.5])
    got = leja((c, c)).bind(matrix_op(c * np.eye(3)), h).phi_action(k, sigma, v)
    assert rel_err(got, phi_scalar(sigma * h * c, k) * v) <= CHECK


# Zero-width bounds on a Jordan block: point spectrum is not a scalar operator.
JORDAN = np.array([[0.0, 1.0], [0.0, 0.0]])


@pytest.mark.parametrize("k", KS)
def test_zero_width_bounds_on_jordan_block_are_exact_or_fail_explicitly(k):
    v = np.array([0.0, 1.0])
    try:
        got = leja((0.0, 0.0)).bind(matrix_op(JORDAN), 1.0).phi_action(k, 1.0, v)
    except EXPLICIT_FAILURES:
        return
    assert rel_err(got, phi_ref(JORDAN, v, k)) <= CHECK


@pytest.mark.parametrize("k", KS)
def test_zero_width_bounds_on_jordan_eigenvector_are_exact(k):
    v = np.array([1.0, 0.0])
    got = leja((0.0, 0.0)).bind(matrix_op(JORDAN), 1.0).phi_action(k, 1.0, v)
    assert rel_err(got, v / math.factorial(k)) <= CHECK


# Operator equal to c*I only up to rounding, with zero or tight bounds.
_Q, _ = np.linalg.qr(np.random.default_rng(7).standard_normal((6, 6)))
V6 = np.random.default_rng(8).standard_normal(6)


@pytest.mark.parametrize("width_ulps", [0, 1000])
@pytest.mark.parametrize("k", KS)
def test_rounded_scalar_operator_with_tight_bounds(k, width_ulps):
    c, h = -2.0, 0.5
    A = _Q @ (c * np.eye(6)) @ _Q.T
    w = width_ulps * np.spacing(abs(c))
    try:
        got = leja((c - w, c + w)).bind(matrix_op(A), h).phi_action(k, 1.0, V6)
    except EXPLICIT_FAILURES:
        return
    assert rel_err(got, phi_ref(h * A, V6, k)) <= CHECK
