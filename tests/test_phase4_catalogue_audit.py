import math
import numpy as np
from numpy.testing import assert_allclose
import pytest

from pyexpint import ALL_METHODS, DiagonalBackend, get_method


EXPECTED_LEGACY_FILES = {
    'lawsoneuler.m','ablawson2.m','ablawson3.m','ablawson4.m','lawson2a.m','lawson2b.m','lawson4.m',
    'norsetteuler.m','abnorsett2.m','abnorsett3.m','abnorsett4.m',
    'pec322.m','pec423.m','pec524.m','pec625.m','pec726.m',
    'pecec332.m','pecec433.m','pecec534.m','pecec635.m','pecec736.m',
    'eglm332.m','eglm433.m','etd2rk.m','etd3rk.m','ehlelawson.m','etd4rk.m','krogstad.m',
    'strehmelweiner.m','friedli.m','hochost4.m','etd5rkf.m',
    'rkmk2e.m','etd2cf3.m','cfree4.m','rkmk4t.m',
    'genlawson41.m','genlawson42.m','genlawson43.m','genlawson44.m','genlawson45.m',
    'modgenlawson41.m','modgenlawson42.m','modgenlawson43.m','modgenlawson44.m','modgenlawson45.m',
    'cranknicolson.m',
}


def _value(expr, z):
    ctx = DiagonalBackend().bind(np.array([z], dtype=complex), 1.0)
    return complex(expr.apply(ctx, np.array([1.0+0j]))[0])


def _phi(k, scale, z):
    ctx = DiagonalBackend().bind(np.array([z], dtype=complex), 1.0)
    return complex(ctx.phi_action(k, scale, np.array([1.0+0j]))[0])


def _stage_residual(method, i, ell, z):
    fac = math.factorial(ell-1)
    lhs = method.c[i]**ell * _phi(ell, method.c[i], z)
    rhs = 0j
    for j in range(i):
        rhs += method.c[j]**(ell-1)/fac * _value(method.A[i][j], z)
    # External state columns 1... are h*N(y_{n-k}), k=1,...,q-1.
    for k in range(1, method.outputs):
        rhs += (-k)**(ell-1)/fac * _value(method.U[i][k], z)
    return lhs-rhs


def _quadrature_residual(method, ell, z):
    fac = math.factorial(ell-1)
    lhs = _phi(ell, 1.0, z)
    rhs = 0j
    for i, ci in enumerate(method.c):
        rhs += ci**(ell-1)/fac * _value(method.B[0][i], z)
    for k in range(1, method.outputs):
        rhs += (-k)**(ell-1)/fac * _value(method.V[0][k], z)
    return lhs-rhs


def test_catalogue_is_exactly_47_historical_scheme_files():
    assert len(ALL_METHODS) == 47
    assert {m.legacy_file for m in ALL_METHODS} == EXPECTED_LEGACY_FILES
    assert len({m.name.lower() for m in ALL_METHODS}) == 47


@pytest.mark.parametrize('p', [2,3,4])
def test_generated_abnorsett_full_quadrature_order(p):
    m=get_method(f'ABNorsett{p}')
    for z in (-0.73, 0.31+0.27j):
        for ell in range(1,p+1):
            assert abs(_quadrature_residual(m,ell,z)) < 3e-11


@pytest.mark.parametrize('prefix,p', [
    ('PEC',3),('PEC',4),('PEC',5),('PEC',6),('PEC',7),
    ('PECEC',3),('PECEC',4),('PECEC',5),('PECEC',6),('PECEC',7),
])
def test_generated_pec_families_satisfy_otw_orders(prefix,p):
    q=p-1
    s=2 if prefix=='PEC' else 3
    name=f'{prefix}{p}{s}{q}'
    m=get_method(name)
    assert m.stage_order == p-1
    assert m.quadrature_order == p
    for z in (-0.61, 0.23+0.19j):
        for i in range(1,m.stages):
            for ell in range(1,p):
                assert abs(_stage_residual(m,i,ell,z)) < 2e-10, (name,i,ell,z)
        for ell in range(1,p+1):
            assert abs(_quadrature_residual(m,ell,z)) < 2e-10, (name,ell,z)


@pytest.mark.parametrize('q', [1,2,3,4,5])
def test_generated_generalized_lawson_order_conditions(q):
    m=get_method(f'GenLawson4{q}')
    for z in (-0.57, 0.21+0.17j):
        for i in range(1,m.stages):
            for ell in range(1,q+1):
                assert abs(_stage_residual(m,i,ell,z)) < 3e-10, (m.name,i,ell,z)
        for ell in range(1,q+1):
            assert abs(_quadrature_residual(m,ell,z)) < 3e-10, (m.name,ell,z)
    if q <= 3:
        # The next quadrature condition is weak: it is required only at L=0.
        assert abs(_quadrature_residual(m,q+1,0.0)) < 3e-12
        assert abs(_quadrature_residual(m,q+1,-0.57)) > 1e-9


@pytest.mark.parametrize('q', [1,2,3,4,5])
def test_generated_modified_lawson_has_strong_q_plus_one_quadrature(q):
    m=get_method(f'ModGenLawson4{q}')
    assert m.quadrature_order == q+1
    for z in (-0.57, 0.21+0.17j):
        for i in range(1,m.stages):
            for ell in range(1,q+1):
                assert abs(_stage_residual(m,i,ell,z)) < 3e-10, (m.name,i,ell,z)
        for ell in range(1,q+2):
            assert abs(_quadrature_residual(m,ell,z)) < 3e-10, (m.name,ell,z)


def test_etd2cf3_uses_documented_one_third_stage_not_legacy_half_phi_bug():
    m=get_method('ETD2CF3')
    z=-0.83+0.14j
    got=_value(m.A[1][0],z)
    want=(1/3)*_phi(1,1/3,z)
    wrong=(1/3)*_phi(1,1/2,z)
    assert_allclose(got,want,rtol=2e-13,atol=2e-14)
    assert abs(got-wrong) > 1e-3


def test_etd5rkf_fourth_stage_uses_documented_c_three_quarters():
    m=get_method('ETD5RKF')
    assert m.c[3] == 0.75
    z=-0.91+0.12j
    got=_value(m.U[3][0],z)
    want=np.exp(0.75*z)
    wrong=np.exp(0.6*z)
    assert_allclose(got,want,rtol=2e-13,atol=2e-14)
    assert abs(got-wrong) > 1e-3
