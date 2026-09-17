import numpy as np

from pyexpint import (
    SemilinearProblem,
    solve_fixed,
    DiagonalBackend,
    ETD4RK,
)

problem = SemilinearProblem(
    linear_operator=np.array([-1.0]),
    nonlinear=lambda t, y: y*y,
    y0=np.array([0.2]),
    t_span=(0.0, 0.8),
)

sol = solve_fixed(problem, ETD4RK, 0.025, DiagonalBackend())
exact = 1.0 / (1.0 + 4.0*np.exp(0.8))

print("numerical:", sol.y[-1, 0])
print("exact:    ", exact)
print("error:    ", abs(sol.y[-1, 0] - exact))
