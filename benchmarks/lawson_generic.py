#!/usr/bin/env python3
"""Classical convergence of the generalized Lawson families on a generic test.

Six-dimensional semilinear system y' = A y + 0.3 sin(y) + f(t) with a random
symmetric negative definite A (seeds 1729 and 2718), manufactured exact solution
y_i(t) = a_i cos(w_i t + p_i), dense exact phi-actions and steps h = 0.2, 0.1,
0.05, 0.025.  Every method integrates the window [0.8, 1.6] with its own steps:
a method with history length r starts at 0.8 - r h, and its r exact startup
steps end at 0.8.  This driver replaces the measurements previously recovered
from a printed log.
"""
import json
import math
import sys

import numpy as np

from pyexpint import DenseBackend, SemilinearProblem, get_method, solve_fixed

METHODS = ("Krogstad", "HochOst4", "ETD5RKF",
           "GenLawson41", "GenLawson42", "GenLawson43", "GenLawson44", "GenLawson45",
           "ModGenLawson41", "ModGenLawson42", "ModGenLawson43", "ModGenLawson44", "ModGenLawson45")
HS = (0.2, 0.1, 0.05, 0.025)


def make_problem(seed, t_start=0.8, n=6):
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((n, n))
    A = -(M @ M.T) / n - 0.5 * np.eye(n)
    a = rng.uniform(0.5, 1.5, n)
    w = rng.uniform(0.5, 2.0, n)
    p = rng.uniform(0.0, 2.0 * np.pi, n)

    def exact(t):
        return a * np.cos(w * t + p)

    def nonlinear(t, y):
        ue = exact(t)
        source = -a * w * np.sin(w * t + p) - A @ ue - 0.3 * np.sin(ue)
        return 0.3 * np.sin(y) + source

    return SemilinearProblem(A, nonlinear, exact(t_start), (t_start, 1.6), exact_solution=exact), exact


def run():
    rows = []
    for seed in (1729, 2718):
        for name in METHODS:
            method = get_method(name)
            errors = []
            for h in HS:
                problem, exact = make_problem(seed, t_start=0.8 - method.history_length * h)
                sol = solve_fixed(problem, method, h, DenseBackend())
                errors.append(float(np.max(np.abs(sol.y[-1] - exact(1.6)))))
            slopes = [math.log2(errors[i] / errors[i + 1]) if min(errors[i], errors[i + 1]) > 0 else float("nan")
                      for i in range(len(HS) - 1)]
            rows.append({"seed": seed, "method": name, "classical_order": method.classical_order,
                         "errors": errors, "slopes": slopes})
    return {"hs": list(HS), "window": [0.8, 1.6], "rows": rows}


if __name__ == "__main__":
    out = run()
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(out, indent=1))
    for r in out["rows"]:
        print(f"{r['seed']} {r['method']:15s} p={r['classical_order']} slopes "
              + " ".join(f"{s:5.2f}" for s in r["slopes"]) + f"  finest {r['errors'][-1]:.2e}")
