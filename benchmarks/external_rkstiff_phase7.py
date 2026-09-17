#!/usr/bin/env python3
"""Optional external ETD34 comparison against Patrick Whalen's MIT `rkstiff`.

This script is intentionally NOT part of the PyEXPINT test suite.  It runs only
when the external package is installed and keeps the external dependency out of
the core package.

Install separately:
    python -m pip install rkstiff

The comparison uses an autonomous scalar semilinear problem so both libraries
receive exactly the same L and N.
"""
import json
import numpy as np

from pyexpint import DiagonalBackend, ETD34Options, SemilinearProblem, solve_etd34


def exact(t):
    return np.array([1.0/(1.0+4.0*np.exp(t))])


def main():
    try:
        from rkstiff.etd34 import ETD34
        from rkstiff.solveras import SolverConfig
    except ImportError:
        print("SKIP: rkstiff is not installed.")
        return 77

    L=np.array([-1.0])
    nl=lambda u: u*u
    p=SemilinearProblem(L,lambda t,u:nl(u),exact(0.0),(0.0,2.0),exact_solution=exact)

    rows=[]
    for tol in (1e-4,1e-6,1e-8):
        ours=solve_etd34(
            p,DiagonalBackend(),
            options=ETD34Options(rtol=tol,atol=tol*1e-3,h0=0.1,h_max=0.5),
        )
        ext=ETD34(L,nl,config=SolverConfig(epsilon=tol,safety_f=0.9))
        uext=np.asarray(ext.evolve(exact(0.0),t0=0.0,tf=2.0))
        if uext.ndim > 1:
            uext=uext[-1]
        rows.append({
            "tol":tol,
            "pyexpint_final":float(np.real(ours.y[-1,0])),
            "rkstiff_final":float(np.real(uext.reshape(-1)[0])),
            "difference":float(abs(ours.y[-1,0]-uext.reshape(-1)[0])),
            "exact_error_pyexpint":float(abs(ours.y[-1,0]-exact(2.0)[0])),
            "exact_error_rkstiff":float(abs(uext.reshape(-1)[0]-exact(2.0)[0])),
        })
    with open("phase7_external_rkstiff.json","w",encoding="utf-8") as f:
        json.dump({"comparator":"rkstiff ETD34","cases":rows},f,indent=2)
    print(json.dumps(rows,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
