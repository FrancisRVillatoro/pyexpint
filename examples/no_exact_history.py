"""History method and adaptive ETD34 on a problem without exact solution.

Allen-Cahn type reaction-diffusion u_t = eps u_xx + u - u^3 on (0, 1) with
homogeneous Dirichlet conditions, second differences on n = 127 interior points,
eps = 0.01 and u0 = 0.5 sin(pi x) + 0.25 sin(3 pi x).  ABNorsett4 starts from the
default numerical startup (one HochOst4 step per startup interval), and ETD34
controls the error adaptively.  Both are compared with a fixed-step HochOst4
reference with a smaller time step.
"""
import numpy as np
import scipy.sparse as sp
from pyexpint import (ABNORSETT4, HOCHOST4, ETD34Options,
                      KiopsBackend, SemilinearProblem,
                      solve_etd34, solve_fixed)

n, eps = 127, 0.01
dx = 1.0 / (n + 1)
x = np.linspace(dx, 1.0 - dx, n)
e = np.ones(n)
L = (eps / dx**2) * sp.diags([e[1:], -2.0 * e, e[1:]],
                             [-1, 0, 1], format="csr")
u0 = 0.5 * np.sin(np.pi * x) + 0.25 * np.sin(3.0 * np.pi * x)
problem = SemilinearProblem(L, lambda t, u: u - u**3, u0,
                            (0.0, 2.0))

reference = solve_fixed(problem, HOCHOST4, 2.0 / 512,
                        KiopsBackend(tol=1e-12)).y[-1]
multistep = solve_fixed(problem, ABNORSETT4, 2.0 / 128,
                        KiopsBackend(tol=1e-11))
adaptive = solve_etd34(problem, KiopsBackend(tol=1e-11),
                       options=ETD34Options(rtol=1e-8,
                                            atol=1e-10))

d1 = np.max(np.abs(multistep.y[-1] - reference))
d2 = np.max(np.abs(adaptive.y[-1] - reference))
print(f"ABNorsett4, h = 2/128, numerical startup: "
      f"max difference {d1:.2e}")
print(f"ETD34, rtol = 1e-8: max difference {d2:.2e}, "
      f"{adaptive.stats['accepted_steps']} accepted and "
      f"{adaptive.stats['rejected_steps']} rejected steps")
