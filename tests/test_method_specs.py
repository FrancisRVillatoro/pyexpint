import numpy as np
from numpy.testing import assert_allclose

from pyexpint import ALL_METHODS, ETD2RK, DiagonalBackend


def test_all_phase2_specs_validate():
    assert len(ALL_METHODS) == 47
    for method in ALL_METHODS:
        method.validate()


def test_etd2rk_published_regression_at_L_zero():
    ctx = DiagonalBackend().bind(np.array([0.0]), 1.0)
    one = np.array([1.0])
    b1 = ETD2RK.B[0][0].apply(ctx, one)[0]
    b2 = ETD2RK.B[0][1].apply(ctx, one)[0]
    assert_allclose([b1,b2],[0.5,0.5],rtol=0,atol=2e-15)
