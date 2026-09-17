import numpy as np
from numpy.testing import assert_allclose
from scipy.linalg import expm

from pyexpint import SemilinearProblem, solve_fixed, DiagonalBackend, DenseBackend, ALL_METHODS

EXPONENTIAL_METHODS = tuple(m for m in ALL_METHODS if not m.historical_comparator)
CRANK = next(m for m in ALL_METHODS if m.name == "CrankNicolson")


def test_exact_linear_propagation_all_exponential_methods_diagonal():
    lam=np.array([-2.0,-0.3,0.4]); y0=np.array([1.0,-2.0,0.7]); T=0.8
    exact=np.exp(T*lam)*y0
    p=SemilinearProblem(lam,lambda t,y:np.zeros_like(y),y0,(0.0,T), exact_solution=lambda t:np.exp(t*lam)*y0)
    for m in EXPONENTIAL_METHODS:
        sol=solve_fixed(p,m,0.1,DiagonalBackend())
        assert_allclose(sol.y[-1],exact,rtol=4e-12,atol=5e-13,err_msg=m.name)


def test_exact_linear_propagation_all_exponential_methods_dense_nondiagonal():
    A=np.array([[-2.0,0.7],[-0.2,-0.5]]); y0=np.array([1.0,-0.4]); T=0.6
    exact=lambda t: expm(t*A)@y0
    p=SemilinearProblem(A,lambda t,y:np.zeros_like(y),y0,(0.0,T),exact_solution=exact)
    for m in EXPONENTIAL_METHODS:
        sol=solve_fixed(p,m,0.1,DenseBackend())
        assert_allclose(sol.y[-1],exact(T),rtol=8e-12,atol=8e-13,err_msg=m.name)


def test_crank_nicolson_linear_second_order():
    lam=np.array([-2.0,-0.3]); y0=np.array([1.0,-0.4]); T=0.8
    exact=np.exp(T*lam)*y0
    p=SemilinearProblem(lam,lambda t,y:np.zeros_like(y),y0,(0.0,T))
    hs=np.array([0.2,0.1,0.05,0.025])
    errs=[]
    for h in hs:
        sol=solve_fixed(p,CRANK,float(h),DiagonalBackend())
        errs.append(np.linalg.norm(sol.y[-1]-exact))
    slopes=np.log(np.array(errs[:-1])/np.array(errs[1:]))/np.log(2.0)
    assert slopes[-1] > 1.9, (slopes, errs)
