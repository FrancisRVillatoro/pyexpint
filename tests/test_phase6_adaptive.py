import numpy as np
import pytest

from pyexpint import (
    AdaptiveOptions,
    AutoBackend,
    DiagonalBackend,
    KiopsBackend,
    LejaBackend,
    SemilinearProblem,
    get_method,
    solve_adaptive,
)


def exact_riccati(t):
    return np.array([1.0 / (1.0 + 4.0*np.exp(t))])


def riccati_problem():
    return SemilinearProblem(
        np.array([-1.0]), lambda t,y: y*y,
        np.array([0.2]), (0.0, 2.0), exact_solution=exact_riccati,
    )


@pytest.mark.parametrize('name', ['ETD2RK','ETD4RK','Krogstad','HochOst4'])
def test_adaptive_reaches_requested_accuracy_diagonal(name):
    p=riccati_problem()
    sol=solve_adaptive(
        p, get_method(name), DiagonalBackend(),
        options=AdaptiveOptions(rtol=2e-6, atol=1e-10, h0=0.25),
    )
    err=float(np.max(np.abs(sol.y[-1]-exact_riccati(2.0))))
    assert err < 2e-6
    assert sol.stats['accepted_steps'] > 0
    assert sol.stats['attempted_steps'] >= sol.stats['accepted_steps']
    assert abs(sol.t[-1]-2.0) < 1e-14


def test_tighter_tolerance_increases_work_and_reduces_error():
    p=riccati_problem(); m=get_method('Krogstad')
    loose=solve_adaptive(p,m,DiagonalBackend(),options=AdaptiveOptions(rtol=1e-4,atol=1e-10,h0=0.3))
    tight=solve_adaptive(p,m,DiagonalBackend(),options=AdaptiveOptions(rtol=1e-7,atol=1e-12,h0=0.3))
    elo=float(np.max(np.abs(loose.y[-1]-exact_riccati(2.0))))
    eti=float(np.max(np.abs(tight.y[-1]-exact_riccati(2.0))))
    assert eti < elo
    assert tight.stats['accepted_steps'] >= loose.stats['accepted_steps']


def test_backend_tolerance_is_coupled_to_time_tolerance():
    p=riccati_problem(); m=get_method('ETD4RK')
    sol=solve_adaptive(p,m,KiopsBackend(tol=1e-3), options=AdaptiveOptions(rtol=1e-6,atol=1e-10,action_rtol_fraction=0.02))
    assert abs(sol.stats['action_tolerance']-2e-8) < 1e-18
    assert sol.stats['backend_stats']['tolerance'] == pytest.approx(2e-8)


def test_adaptive_multistep_is_explicitly_not_supported():
    p=riccati_problem()
    with pytest.raises(NotImplementedError):
        solve_adaptive(p,get_method('ABNorsett4'),DiagonalBackend())
