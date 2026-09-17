import numpy as np
from numpy.testing import assert_allclose
from scipy.sparse import diags

from pyexpint import KrylovBackend, DiagonalBackend
from pyexpint.expressions import phi


def test_krylov_tolerance_and_stats_are_exposed():
    n = 120
    lam = np.linspace(-30.0, 1.0, n)
    A = diags(lam, format="csr")
    v = np.exp(-np.linspace(0, 2, n))
    h = 0.025
    expr = phi(1) - 3*phi(2) + 4*phi(3)

    kb = KrylovBackend(tol=1e-10, min_dim=8, max_dim=44, check_every=4)
    got = expr.apply(kb.bind(A,h), v)
    ref = expr.apply(DiagonalBackend().bind(lam,h), v)
    assert_allclose(got, ref, rtol=2e-9, atol=2e-11)

    st = kb.stats()
    assert st["tolerance"] == 1e-10
    assert 1 <= st["max_krylov_dim_used"] <= 44
    assert st["mean_krylov_dim"] > 0
    assert st["nonconverged_actions"] == 0
