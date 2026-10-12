"""End-to-end convergence with numerical startup (block C4).

For every history method of classical order p >= 4, the final error on the
non-stiff logistic test y' = -y + y^2, y(0) = 0.4, t in [0, 1], whose exact
solution is y(t) = 1/(1 + 1.5 e^t), is measured twice: with the exact history
(ExactStartup) and with the default numerical startup (OneStepStartup with
HochOst4, one starter step per startup interval).  The exact solution is used
only to measure errors.  Adjacent slopes log2(e(h)/e(h/2)) are reported.
"""

import json
import sys

import numpy as np

from pyexpint import (ALL_METHODS, DiagonalBackend, ExactStartup, OneStepStartup,
                      SemilinearProblem, HOCHOST4, solve_fixed)

HS = (0.1, 0.05, 0.025, 0.0125)


def exact(t):
    return np.array([1.0 / (1.0 + 1.5 * np.exp(t))])


PROBLEM = SemilinearProblem(np.array([-1.0]), lambda t, y: y * y, exact(0.0), (0.0, 1.0),
                           exact_solution=exact)


def final_error(method, h, startup):
    sol = solve_fixed(PROBLEM, method, h, DiagonalBackend(), startup=startup)
    return float(abs(sol.y[-1, 0] - exact(1.0)[0]))


def slopes(errors):
    e = np.asarray(errors)
    return [float(x) for x in np.log2(e[:-1] / e[1:])]


def main(out_json=None):
    rows = []
    methods = sorted((m for m in ALL_METHODS if m.history_length > 0 and m.classical_order >= 4),
                     key=lambda m: (m.classical_order, m.name))
    print(f"{'method':16s} p   exact-history slopes        default-startup slopes      e_def/e_exact at h={HS[-1]}")
    for m in methods:
        ex = [final_error(m, h, ExactStartup()) for h in HS]
        df = [final_error(m, h, OneStepStartup(HOCHOST4)) for h in HS]
        sx, sd = slopes(ex), slopes(df)
        ratio = df[-1] / ex[-1]
        rows.append({"method": m.name, "classical_order": m.classical_order, "h": list(HS),
                     "error_exact_history": ex, "error_default_startup": df,
                     "slopes_exact_history": sx, "slopes_default_startup": sd,
                     "ratio_default_over_exact_finest": ratio})
        print(f"{m.name:16s} {m.classical_order}   {' '.join(f'{x:5.2f}' for x in sx):27s} "
              f"{' '.join(f'{x:5.2f}' for x in sd):27s} {ratio:9.2e}")
    if out_json:
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump({"problem": "logistic y'=-y+y^2, y(0)=0.4, t in [0,1]",
                       "backend": "DiagonalBackend", "starter": "HochOst4, one step per interval",
                       "rows": rows}, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
