
import math
import numpy as np
from numpy.testing import assert_allclose

from pyexpint.backends.diagonal import DiagonalBackend


def _series_phi(k, z, nterms=80):
    # Independent power-series oracle for moderate/small scalar z.
    s = 0.0 + 0.0j
    term = 1.0 / math.factorial(k)
    s += term
    for m in range(1, nterms):
        term *= z / (k + m)
        s += term
    return s


def test_phi_near_zero_through_k7():
    zs = np.array([
        0.0,
        1e-16,
        -1e-12,
        1e-8,
        -1e-5,
        1e-3,
        -0.1,
        0.7,
    ], dtype=float)
    ctx = DiagonalBackend().bind(zs, 1.0)
    ones = np.ones_like(zs)
    for k in range(8):
        got = ctx.phi_action(k, 1.0, ones)
        ref = np.array([_series_phi(k, complex(z)).real for z in zs])
        assert_allclose(got, ref, rtol=3e-14, atol=3e-16)


def test_phi_complex_small_arguments():
    lam = np.array([1e-10j, -1e-5j, 0.2j, -0.8j], dtype=complex)
    ctx = DiagonalBackend().bind(lam, 1.0)
    ones = np.ones(lam.shape, dtype=complex)
    for k in range(6):
        got = ctx.phi_action(k, 1.0, ones)
        ref = np.array([_series_phi(k, complex(z)) for z in lam])
        assert_allclose(got, ref, rtol=5e-14, atol=5e-16)
