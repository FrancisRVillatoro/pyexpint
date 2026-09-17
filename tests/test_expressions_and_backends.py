import math
import numpy as np
from numpy.testing import assert_allclose

from pyexpint.backends.diagonal import DiagonalBackend
from pyexpint.backends.dense import DenseBackend
from pyexpint.expressions import phi, I


def test_phi_values_at_zero_diagonal():
    ctx = DiagonalBackend().bind(np.zeros(4), 0.3)
    v = np.arange(1.0, 5.0)
    for k in range(6):
        assert_allclose(ctx.phi_action(k, 1.0, v), v / math.factorial(k), rtol=0, atol=2e-15)


def test_dense_diagonal_agreement():
    lam = np.array([-4.0, -0.7, 0.0, 1.2])
    A = np.diag(lam)
    v = np.array([1.0, -2.0, 0.5, 3.0])
    h = 0.17

    dctx = DiagonalBackend().bind(lam, h)
    mctx = DenseBackend().bind(A, h)

    exprs = [
        phi(0, 1.0),
        phi(1, 0.5),
        phi(1) - 3*phi(2) + 4*phi(3),
        0.5 * (phi(1, 0.5) @ (phi(0, 0.5) - I)),
    ]
    for expr in exprs:
        assert_allclose(expr.apply(dctx, v), expr.apply(mctx, v), rtol=2e-12, atol=2e-13)
