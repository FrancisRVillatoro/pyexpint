import math
import numpy as np
from scipy.fft import dst, idst

from pyexpint import DiagonalBackend, SemilinearProblem, get_method, solve_fixed


def _problem(n=120, variant=1):
    x = np.arange(1,n+1)/(n+1)
    dx = 1/(n+1)
    k = np.arange(1,n+1)
    lam = -4/dx**2*np.sin(np.pi*k/(2*(n+1)))**2
    to_spec = lambda u: dst(np.asarray(u), type=1, norm="ortho")
    to_phys = lambda y: idst(np.asarray(y), type=1, norm="ortho")
    exact_phys = lambda t: x*(1-x)*np.exp(t)
    exact_spec = lambda t: to_spec(exact_phys(t))
    lap_exact = lambda t: to_phys(lam*exact_spec(t))
    if variant == 1:
        def N(t,y):
            u=to_phys(y); ue=exact_phys(t)
            Phi=ue-lap_exact(t)-1/(1+ue**2)
            return to_spec(1/(1+u**2)+Phi)
    else:
        def N(t,y):
            u=to_phys(y); ue=exact_phys(t)
            I=dx*np.sum(u); Ie=dx*np.sum(ue)
            Phi=ue-lap_exact(t)-Ie
            return to_spec(np.full(n,I)+Phi)
    return SemilinearProblem(lam,N,exact_spec(0),(0.,1.),exact_solution=exact_spec),to_phys,exact_phys


def _slope(name, variant, hs):
    p,to_phys,ue=_problem(120,variant)
    e=[]
    for h in hs:
        sol=solve_fixed(p,get_method(name),h,DiagonalBackend())
        e.append(np.max(np.abs(to_phys(sol.y[-1])-ue(1))))
    return math.log(e[-2]/e[-1],2)


def test_hochbruck_ostermann_local_signatures():
    hs=[1/20,1/40,1/80,1/160]
    assert _slope("ETD4RK",1,hs) > 2.8
    assert _slope("Krogstad",1,hs) > 3.8
    assert _slope("HochOst4",1,hs) > 3.8


def test_hochbruck_ostermann_nonlocal_order_reduction():
    hs=[1/40,1/80,1/160,1/320]
    s_cm=_slope("ETD4RK",2,hs)
    s_kr=_slope("Krogstad",2,hs)
    s_ho=_slope("HochOst4",2,hs)
    assert 2.3 < s_cm < 2.7
    assert 3.1 < s_kr < 3.7
    assert s_ho > 3.8


def test_rkmk_weak_second_order_observed():
    hs=[1/20,1/40,1/80,1/160]
    for name in ("RKMK2e","RKMK4t"):
        s=_slope(name,1,hs)
        assert 1.8 < s < 2.2


def test_rkmk_strong_second_order_condition_fails_but_weak_holds():
    # Strong ExpRK order 2 requires sum_i b_i(z)c_i = phi_2(z).
    # Evaluate at z=-1 and at z=0 using the diagonal backend.
    from pyexpint import DiagonalBackend
    for name in ("RKMK2e", "RKMK4t"):
        m = get_method(name)
        assert m.stiff_order == 1
        assert m.weak_stiff_order == 2
        c = np.asarray(m.c)
        v = np.array([1.0])
        ctx = DiagonalBackend().bind(np.array([-4.0]), 1.0)
        moment = sum(c[i] * m.B[0][i].apply(ctx, v)[0] for i in range(m.stages))
        phi2 = ctx.phi_action(2, 1.0, v)[0]
        assert abs(moment - phi2) > 1e-3

        ctx0 = DiagonalBackend().bind(np.array([0.0]), 1.0)
        moment0 = sum(c[i] * m.B[0][i].apply(ctx0, v)[0] for i in range(m.stages))
        assert abs(moment0 - 0.5) < 1e-14
