import numpy as np
from numpy.testing import assert_allclose
from scipy.sparse import diags
from scipy.sparse.linalg import expm_multiply
from pyexpint import ScipyKiopsBackend, SemilinearProblem, get_method, solve_fixed


def test_hybrid_exp_action_matches_scipy():
    n=64; A=diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],format='csr')
    v=np.linspace(-1,1,n); h=.2
    b=ScipyKiopsBackend(tol=1e-11); got=b.bind(A,h).phi_action(0,1.0,v)
    assert_allclose(got,expm_multiply(h*A,v),rtol=2e-13,atol=2e-14)
    assert b.stats()['scipy_expm_calls']==1


def test_hybrid_executes_krogstad():
    n=64; A=20*diags([np.ones(n-1),-2*np.ones(n),np.ones(n-1)],[-1,0,1],format='csr')
    x=np.linspace(0,1,n+2)[1:-1]; y0=.1*np.sin(np.pi*x)
    p=SemilinearProblem(A,lambda t,y:.1*y*y,y0,(0,.1))
    sol=solve_fixed(p,get_method('Krogstad'),.05,ScipyKiopsBackend(tol=1e-10))
    assert np.all(np.isfinite(sol.y))
    assert sol.stats['backend_stats']['scipy_expm_calls']>0
    assert sol.stats['backend_stats']['linear_combination_actions']>0
