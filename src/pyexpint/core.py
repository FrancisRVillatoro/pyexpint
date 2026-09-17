from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any, Mapping
import numpy as np

Array = np.ndarray
Nonlinear = Callable[[float, Array], Array]
ExactSolution = Callable[[float], Array]


@dataclass(frozen=True)
class SemilinearProblem:
    """Semilinear IVP ``y' = L y + N(t, y)``."""

    linear_operator: Any
    nonlinear: Nonlinear
    y0: Array
    t_span: tuple[float, float]
    exact_solution: ExactSolution | None = None

    def __post_init__(self) -> None:
        y0 = np.asarray(self.y0)
        if y0.ndim != 1:
            raise ValueError("y0 must be a one-dimensional state vector.")
        if not self.t_span[1] > self.t_span[0]:
            raise ValueError("Require t_span[1] > t_span[0].")
        if self.exact_solution is not None:
            yex = np.asarray(self.exact_solution(float(self.t_span[0])))
            if yex.shape != y0.shape:
                raise ValueError("exact_solution(t) must return the same shape as y0.")


@dataclass(frozen=True)
class ExternalState:
    """External GLM state at one grid time.

    ``values[j]`` is the j-th external vector.  The first component is always
    the physical numerical solution in the current PyEXPINT method catalogue.
    Auxiliary components are method-defined; multistep methods may use nonlinear-history
    components for all r>1 P0 methods.
    """

    t: float
    values: Array

    def __post_init__(self):
        values = np.asarray(self.values)
        if values.ndim != 2:
            raise ValueError("ExternalState.values must have shape (r, nstate).")

    @property
    def y(self) -> Array:
        return self.values[0]

    @property
    def outputs(self) -> int:
        return self.values.shape[0]


@dataclass(frozen=True)
class Solution:
    t: Array
    y: Array
    method: str
    backend: str
    step_size: float
    stats: Mapping[str, Any] = field(default_factory=dict)
