from __future__ import annotations

"""Compatibility helpers for supported SciPy releases.

SciPy <=1.13 exposes GMRES relative tolerance as ``tol``; newer releases
use ``rtol``. PyEXPINT supports both without version branching elsewhere.
"""

import inspect
from scipy.sparse.linalg import gmres as _scipy_gmres

_GMRES_PARAMETERS = inspect.signature(_scipy_gmres).parameters
_GMRES_USES_RTOL = "rtol" in _GMRES_PARAMETERS

def gmres_compat(A, b, *, rtol: float, atol: float = 0.0, restart=None, **kwargs):
    call = dict(atol=atol, restart=restart, **kwargs)
    if _GMRES_USES_RTOL:
        call["rtol"] = rtol
    else:
        call["tol"] = rtol
    return _scipy_gmres(A, b, **call)
