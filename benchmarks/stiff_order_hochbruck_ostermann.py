#!/usr/bin/env python3
"""Reproduce the two order-reduction examples of Hochbruck--Ostermann (2005).

The finite-difference Dirichlet Laplacian is diagonalized by an orthonormal DST-I,
so phi-actions are evaluated by PyEXPINT's DiagonalBackend without contamination
from a Krylov tolerance.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
from scipy.fft import dst, idst

from pyexpint import DiagonalBackend, SemilinearProblem, get_method, solve_fixed


def make_problem(n: int = 200, variant: int = 1):
    x = np.arange(1, n + 1, dtype=float) / (n + 1)
    dx = 1.0 / (n + 1)
    k = np.arange(1, n + 1, dtype=float)
    lam = -4.0 / dx**2 * np.sin(np.pi * k / (2.0 * (n + 1)))**2

    def to_spec(u):
        return dst(np.asarray(u), type=1, norm="ortho")

    def to_phys(y):
        return idst(np.asarray(y), type=1, norm="ortho")

    def exact_phys(t):
        return x * (1.0 - x) * np.exp(t)

    def exact_spec(t):
        return to_spec(exact_phys(t))

    def discrete_lap_exact(t):
        return to_phys(lam * exact_spec(t))

    if variant == 1:
        # U_t - U_xx = 1/(1+U^2) + Phi.
        def nonlinear(t, yhat):
            u = to_phys(yhat)
            ue = exact_phys(t)
            Phi = ue - discrete_lap_exact(t) - 1.0 / (1.0 + ue**2)
            return to_spec(1.0 / (1.0 + u**2) + Phi)
    elif variant == 2:
        # U_t - U_xx = int_0^1 U dx + Phi.
        # The semidiscrete source uses the same trapezoidal rule as the numerical N.
        def nonlinear(t, yhat):
            u = to_phys(yhat)
            ue = exact_phys(t)
            integ = dx * np.sum(u)   # boundary values are zero
            integ_e = dx * np.sum(ue)
            Phi = ue - discrete_lap_exact(t) - integ_e
            return to_spec(np.full(n, integ) + Phi)
    else:
        raise ValueError("variant must be 1 or 2")

    problem = SemilinearProblem(
        lam,
        nonlinear,
        exact_spec(0.0),
        (0.0, 1.0),
        exact_solution=exact_spec,
    )
    return problem, to_phys, exact_phys


def run(method_names=None, n=200):
    if method_names is None:
        method_names = ["ETD4RK", "Krogstad", "HochOst4", "RKMK2e", "RKMK4t", "Cfree4"]
    hs = np.array([1/20, 1/40, 1/80, 1/160, 1/320, 1/640], dtype=float)
    out = {"n": n, "hs": hs.tolist(), "problems": {}}

    for variant in (1, 2):
        problem, to_phys, exact_phys = make_problem(n=n, variant=variant)
        rows = []
        for name in method_names:
            method = get_method(name)
            errors = []
            for h in hs:
                sol = solve_fixed(problem, method, float(h), DiagonalBackend())
                err = np.max(np.abs(to_phys(sol.y[-1]) - exact_phys(1.0)))
                errors.append(float(err))
            slopes = [math.log(errors[i] / errors[i+1], 2.0) for i in range(len(errors)-1)]
            rows.append({
                "method": method.name,
                "metadata_stiff_order": method.stiff_order,
                "errors": errors,
                "slopes": slopes,
                "last_pair_slope": float(slopes[-1]),
                "last_two_mean_slope": float(np.mean(slopes[-2:])),
            })
        out["problems"][str(variant)] = rows
    return out


if __name__ == "__main__":
    result = run()
    path = Path("phase5_stiff_order.json")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(path)
    for v, rows in result["problems"].items():
        print("problem", v)
        for row in rows:
            print(row["method"], f"slope={row['last_pair_slope']:.3f}")
