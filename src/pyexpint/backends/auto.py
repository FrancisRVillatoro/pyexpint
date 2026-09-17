from __future__ import annotations

"""Rule-based backend selector calibrated by backend crossover benchmarks."""

import numpy as np
from scipy.sparse import issparse

from .base import Backend
from .dense import DenseBackend
from .diagonal import DiagonalBackend
from .kiops import KiopsBackend
from .leja import LejaBackend


class AutoBackend(Backend):
    """Select a matrix-function engine from operator structure.

    Current selection policy:
      * 1-D ndarray -> DiagonalBackend;
      * small dense matrix -> DenseBackend;
      * Hermitian sparse operator with moderate scaled spectral width -> LejaBackend;
      * otherwise -> KiopsBackend.

    The Leja/KIOPS crossover threshold is deliberately exposed; calibration
    benchmarks record the machine-dependent crossover rather than pretending
    that one universal value is optimal.
    """

    name = "auto"

    def __init__(self, *, tol=1e-10, dense_cutoff=96, leja_min_size=512, leja_width_threshold=200.0,
                 leja_target_width=12.0):
        self.tol = float(tol)
        self.dense_cutoff = int(dense_cutoff)
        self.leja_min_size = int(leja_min_size)
        self.leja_width_threshold = float(leja_width_threshold)
        self.diagonal = DiagonalBackend()
        self.dense = DenseBackend()
        self.kiops = KiopsBackend(tol=tol)
        self.leja = LejaBackend(tol=tol, target_width=leja_target_width)
        self._last = None
        self._selection_counts = {}

    def reset_stats(self):
        self.kiops.reset_stats()
        self.leja.reset_stats()
        self._last = None
        self._selection_counts = {}

    @staticmethod
    def _is_hermitian_sparse(A):
        if not issparse(A):
            return False
        D = A - A.T.conjugate()
        return D.nnz == 0 or np.max(np.abs(D.data)) <= 1e-12

    def _select(self, A, h):
        if isinstance(A, np.ndarray) and A.ndim == 1:
            return self.diagonal
        if isinstance(A, np.ndarray) and A.ndim == 2 and A.shape[0] <= self.dense_cutoff:
            return self.dense
        if self._is_hermitian_sparse(A) and A.shape[0] >= self.leja_min_size:
            lo, hi = self.leja._infer_bounds(A)
            width = abs(float(h)) * abs(hi - lo)
            if width <= self.leja_width_threshold:
                return self.leja
        return self.kiops

    def bind(self, linear_operator, h: float):
        backend = self._select(linear_operator, h)
        self._last = backend
        self._selection_counts[backend.name] = self._selection_counts.get(backend.name, 0) + 1
        return backend.bind(linear_operator, h)

    def stats(self):
        details = {}
        if self._last is not None and hasattr(self._last, "stats"):
            details = self._last.stats()
        ks = self.kiops.stats()
        ls = self.leja.stats()
        return {
            "selection_counts": dict(self._selection_counts),
            "last_selected": None if self._last is None else self._last.name,
            "selected_backend_stats": details,
            "kiops_stats": ks,
            "leja_stats": ls,
            "matvecs": ks.get("matvecs", 0) + ls.get("matvecs", 0),
            "leja_min_size": self.leja_min_size,
            "leja_width_threshold": self.leja_width_threshold,
        }
