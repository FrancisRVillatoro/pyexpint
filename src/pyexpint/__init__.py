"""PyEXPINT: backend-independent exponential integrators and the EXPINT method catalogue."""

from .core import SemilinearProblem, Solution, ExternalState
from .expressions import (
    OperatorExpr, PhiTerm, PhiCombination, ProductExpr, ResolventExpr,
    ZERO, I, phi, resolvent,
)
from .methods import *  # re-export catalogue constants for research convenience
from .methods import MethodSpec, get_method, list_methods, ALL_METHODS
from .solve import solve_fixed, step_external
from .adaptive import AdaptiveOptions, solve_adaptive
from .embedded import ETD34Options, solve_etd34
from .startup import ExactStartup, OneStepStartup
from .backends import DenseBackend, DiagonalBackend, KrylovBackend, KrylovOptions, KrylovConvergenceError, KiopsBackend, KiopsOptions, KiopsConvergenceError, LejaBackend, LejaOptions, LejaConvergenceError, AutoBackend, SelectorCalibration, fit_threshold_selector, CalibratedAutoBackend, ScipyKiopsBackend
from .metrics import estimated_backend_workspace_bytes

__all__ = [
    "SemilinearProblem", "Solution", "ExternalState",
    "OperatorExpr", "PhiTerm", "PhiCombination", "ProductExpr", "ResolventExpr",
    "ZERO", "I", "phi", "resolvent",
    "MethodSpec", "get_method", "list_methods", "ALL_METHODS",
    "solve_fixed", "step_external", "AdaptiveOptions", "solve_adaptive", "ETD34Options", "solve_etd34", "ExactStartup", "OneStepStartup",
    "DenseBackend", "DiagonalBackend", "KrylovBackend", "KrylovOptions", "KrylovConvergenceError", "KiopsBackend", "KiopsOptions", "KiopsConvergenceError", "LejaBackend", "LejaOptions", "LejaConvergenceError", "AutoBackend", "SelectorCalibration", "fit_threshold_selector", "CalibratedAutoBackend", "ScipyKiopsBackend", "estimated_backend_workspace_bytes",
]
# Include public all-caps method constants imported from methods.py.
__all__ += [
    name
    for name in globals()
    if name.isupper()
    and not name.startswith("__")
    and name not in __all__
]
