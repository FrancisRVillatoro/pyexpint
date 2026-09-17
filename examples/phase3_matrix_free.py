"""Matrix-free Phase-3 example using scipy LinearOperator."""
import numpy as np
from scipy.sparse.linalg import LinearOperator

from pyexpint import SemilinearProblem, solve_fixed, KrylovBackend, KROGSTAD

n = 10_000

def laplacian_like(x):
    y = -2.0*x.copy()
    y[1:] += x[:-1]
    y[:-1] += x[1:]
    return y

L = LinearOperator((n, n), matvec=laplacian_like, dtype=float)
x = np.linspace(0.0, 1.0, n)
y0 = 0.05 + 0.01*np.sin(np.pi*x)
problem = SemilinearProblem(L, lambda t, y: 0.05*y*y, y0, (0.0, 0.05))
backend = KrylovBackend(tol=1e-9, min_dim=6, max_dim=24, check_every=3)
sol = solve_fixed(problem, KROGSTAD, 0.05, backend)

print("||y(T)||_2 =", np.linalg.norm(sol.y[-1]))
print(sol.stats["backend_stats"])
