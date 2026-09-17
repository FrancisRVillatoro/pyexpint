from __future__ import annotations

import math
import numpy as np

from .base import Backend


def _phi_scalar_array(k: int, z: np.ndarray) -> np.ndarray:
    """Stable elementwise phi_k(z), using series near z=0."""
    z = np.asarray(z)
    dtype = np.result_type(z.dtype, np.complex128)
    zz = z.astype(dtype, copy=False)
    out = np.empty_like(zz)

    small = np.abs(zz) <= 1.0
    large = ~small

    if np.any(small):
        zs = zz[small]
        term = np.full_like(zs, 1.0 / math.factorial(k), dtype=dtype)
        s = term.copy()
        # term_m = z^m/(m+k)!.
        for m in range(1, 80):
            term = term * zs / (k + m)
            s_new = s + term
            if np.all(np.abs(term) <= 4*np.finfo(float).eps * np.maximum(1.0, np.abs(s_new))):
                s = s_new
                break
            s = s_new
        out[small] = s

    if np.any(large):
        zl = zz[large]
        if k == 0:
            out[large] = np.exp(zl)
        elif k == 1:
            out[large] = np.expm1(zl) / zl
        else:
            p = np.expm1(zl) / zl
            for j in range(1, k):
                p = (p - 1.0 / math.factorial(j)) / zl
            out[large] = p

    return np.real_if_close(out)


class _DiagonalContext:
    def __init__(self, diagonal: np.ndarray, h: float):
        self.diagonal = np.asarray(diagonal)
        if self.diagonal.ndim != 1:
            raise ValueError("DiagonalBackend expects the diagonal as a 1-D array.")
        self.h = float(h)
        self._cache: dict[tuple[int, float], np.ndarray] = {}

    def phi_values(self, k: int, scale: float):
        key = (int(k), float(scale))
        if key not in self._cache:
            z = scale * self.h * self.diagonal
            self._cache[key] = _phi_scalar_array(k, z)
        return self._cache[key]

    def phi_action(self, k: int, scale: float, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v)
        if v.shape != self.diagonal.shape:
            raise ValueError("Vector shape does not match diagonal operator.")
        return self.phi_values(k, scale) * v

    def shifted_solve_action(self, alpha: float, v: np.ndarray) -> np.ndarray:
        v = np.asarray(v)
        if v.shape != self.diagonal.shape:
            raise ValueError("Vector shape does not match diagonal operator.")
        denom = 1.0 - float(alpha) * self.h * self.diagonal
        return np.real_if_close(v / denom)


class DiagonalBackend(Backend):
    """Reference/fast backend when L is supplied by its diagonal."""

    name = "diagonal"

    def bind(self, linear_operator, h: float):
        return _DiagonalContext(np.asarray(linear_operator), h)
