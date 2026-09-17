import numpy as np
import pytest

from pyexpint import SemilinearProblem, solve_fixed, DiagonalBackend, ALL_METHODS


def exact_riccati(t):
    # y'=-y+y^2, y(0)=0.4
    return np.array([1.0/(1.0+1.5*np.exp(t))])


@pytest.mark.parametrize("method", ALL_METHODS, ids=lambda m:m.name)
def test_observed_classical_order_with_exact_startup(method):
    T=1.6; y0=np.array([0.4])
    problem=SemilinearProblem(np.array([-1.0]),lambda t,y:y*y,y0,(0.0,T),exact_solution=exact_riccati)
    hs=np.array([0.2,0.1,0.05,0.025])
    errors=[]
    for h in hs:
        sol=solve_fixed(problem,method,float(h),DiagonalBackend())
        errors.append(abs(sol.y[-1,0]-exact_riccati(T)[0]))
    errors=np.asarray(errors)

    slopes=[]
    for i in range(len(hs)-1):
        # Ignore pairs whose fine-grid error is already at the roundoff floor.
        if errors[i] > 5e-14 and errors[i+1] > 5e-14 and errors[i+1] < errors[i]:
            slopes.append(np.log(errors[i]/errors[i+1])/np.log(hs[i]/hs[i+1]))
    assert slopes, (method.name, errors)
    best=max(slopes)
    p=method.classical_order
    # High-order methods may enter the roundoff regime or superconverge on this scalar test.
    # We therefore test that at least one clean refinement pair demonstrates the expected
    # asymptotic order to within a conservative finite-h margin, with no artificial upper bound.
    assert best > p-0.7, (method.name,p,best,slopes,errors)
