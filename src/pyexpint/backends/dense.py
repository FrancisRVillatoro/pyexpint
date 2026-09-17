from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from .base import Backend


class _DenseContext:
    """Dense reference evaluator using augmented matrix exponentials."""

    def __init__(self, matrix: np.ndarray, h: float):
        A = np.asarray(matrix)
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError("DenseBackend expects a square 2-D matrix.")
        self.A = A
        self.h = float(h)
        self.n = A.shape[0]
        self._cache: dict[tuple[int, float], np.ndarray] = {}

    def _ensure_phi_through(self, kmax: int, scale: float):
        # If all required keys already exist, nothing to do.
        if all((k, float(scale)) in self._cache for k in range(kmax + 1)):
            return

        n = self.n
        if scale == 0.0:
            I = np.eye(n, dtype=np.result_type(self.A.dtype, float))
            for k in range(kmax + 1):
                # phi_k(0)=1/k! I
                import math
                self._cache[(k, 0.0)] = I / math.factorial(k)
            return

        dtype = np.result_type(self.A.dtype, np.complex128)
        M = np.zeros(((kmax + 1) * n, (kmax + 1) * n), dtype=dtype)
        M[:n, :n] = scale * self.h * self.A
        I = np.eye(n, dtype=dtype)
        for j in range(kmax):
            M[j*n:(j+1)*n, (j+1)*n:(j+2)*n] = I

        E = expm(M)
        # Top row blocks are phi_j(scale*h*A).
        for k in range(kmax + 1):
            self._cache[(k, float(scale))] = E[:n, k*n:(k+1)*n]

    def phi_matrix(self, k: int, scale: float):
        self._ensure_phi_through(k, scale)
        return self._cache[(int(k), float(scale))]

    def phi_action(self, k: int, scale: float, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v)
        if v.ndim != 1 or v.shape[0] != self.n:
            raise ValueError("Vector shape does not match dense operator.")
        return np.real_if_close(self.phi_matrix(k, scale) @ v)

    def shifted_solve_action(self, alpha: float, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v)
        if v.ndim != 1 or v.shape[0] != self.n:
            raise ValueError("Vector shape does not match dense operator.")
        I = np.eye(self.n, dtype=np.result_type(self.A.dtype, v.dtype))
        return np.real_if_close(np.linalg.solve(I - float(alpha)*self.h*self.A, v))


class DenseBackend(Backend):
    """Dense validation backend; not intended as the large-scale engine."""

    name = "dense"

    def bind(self, linear_operator, h: float):
        return _DenseContext(np.asarray(linear_operator), h)
