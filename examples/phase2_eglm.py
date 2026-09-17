import numpy as np
from pyexpint import SemilinearProblem, DiagonalBackend, solve_fixed, EGLM433, GENLAWSON43

exact=lambda t: np.array([1.0/(1.0+4.0*np.exp(t))])
problem=SemilinearProblem(np.array([-1.0]),lambda t,y:y*y,np.array([0.2]),(0.0,0.8),exact_solution=exact)
for method in (EGLM433,GENLAWSON43):
    sol=solve_fixed(problem,method,0.025,DiagonalBackend())
    print(method.name, 'error=', abs(sol.y[-1,0]-exact(0.8)[0]), 'stats=', dict(sol.stats))
