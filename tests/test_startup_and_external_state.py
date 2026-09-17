import numpy as np
from numpy.testing import assert_allclose

from pyexpint import (
    SemilinearProblem, DiagonalBackend, ExactStartup, OneStepStartup,
    HOCHOST4, ABNORSETT4, PEC423, PECEC433, EGLM332, EGLM433,
    GENLAWSON43, MODGENLAWSON43, solve_fixed, step_external,
)

MULTI=(ABNORSETT4,PEC423,PECEC433,EGLM332,EGLM433,GENLAWSON43,MODGENLAWSON43)


def exact(t):
    return np.array([1.0/(1.0+4.0*np.exp(t))])


def problem(with_exact=True):
    return SemilinearProblem(np.array([-1.0]),lambda t,y:y*y,np.array([0.2]),(0.0,0.8),exact if with_exact else None)


def test_exact_startup_external_history_semantics():
    p=problem(True); h=0.1
    for m in MULTI:
        init=ExactStartup().initialize(p,m,h,DiagonalBackend(),None)
        r=m.outputs; t=init.state.t
        assert init.state.values.shape==(r,1)
        assert_allclose(init.state.values[0],exact(t),rtol=0,atol=1e-15)
        for lag in range(1,r):
            tl=t-lag*h
            expected=h*exact(tl)**2
            assert_allclose(init.state.values[lag],expected,rtol=1e-14,atol=1e-15)


def test_default_hochost_startup_preserves_fourth_order_for_multistep_p0():
    p=problem(False); T=0.8
    for m in MULTI:
        hs=np.array([0.1,0.05,0.025,0.0125])
        err=[]
        for h in hs:
            sol=solve_fixed(p,m,float(h),DiagonalBackend())
            err.append(abs(sol.y[-1,0]-exact(T)[0]))
            assert sol.stats['starter_method']=='HochOst4'
        slope=np.polyfit(np.log(hs[-3:]),np.log(np.asarray(err[-3:])),1)[0]
        assert slope>m.classical_order-0.55,(m.name,slope,err)


def test_abnorsett4_uses_one_nonlinear_eval_per_main_step_metadata():
    assert ABNORSETT4.stages==1
    assert ABNORSETT4.nonlinear_evals_per_step==1
    sol=solve_fixed(problem(False),ABNORSETT4,0.1,DiagonalBackend())
    assert sol.stats['main_steps']==5
    assert sol.stats['startup_steps']==3


def test_external_history_is_shifted_by_engine_for_all_multistep_p0():
    p=problem(True); h=0.1
    for m in MULTI:
        init=ExactStartup().initialize(p,m,h,DiagonalBackend(),None)
        old=init.state
        new=step_external(p,m,old,h,DiagonalBackend())
        # First auxiliary output is h*N(y_n); later auxiliary outputs shift old history.
        assert_allclose(new.values[1], h*p.nonlinear(old.t, old.y), rtol=3e-13, atol=3e-15, err_msg=m.name)
        for j in range(2,m.outputs):
            assert_allclose(new.values[j], old.values[j-1], rtol=3e-13, atol=3e-15, err_msg=m.name)
