from __future__ import annotations

"""Real-Leja polynomial interpolation backend for phi actions.

The implementation is independent and deliberately conservative: it targets
operators with a real spectral interval (especially symmetric dissipative PDE
operators).  Phi combinations are converted to one augmented exponential and
evaluated by Newton interpolation at a real Leja sequence.  Large spectral
intervals are handled by semigroup substepping of the augmented exponential.
"""

from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import issparse
from scipy.sparse.linalg import LinearOperator, aslinearoperator, eigsh

from .base import Backend
from ._scipy_compat import gmres_compat


class LejaConvergenceError(RuntimeError):
    pass


_LEJA_CACHE: dict[tuple[int, int], np.ndarray] = {}


def _real_leja_nodes(count: int, candidates: int = 4097) -> np.ndarray:
    key = (count, candidates)
    if key in _LEJA_CACHE:
        return _LEJA_CACHE[key]
    # Dense Chebyshev-Lobatto candidate set on [-1,1].
    grid = np.cos(np.linspace(0.0, np.pi, candidates))
    selected = np.zeros(candidates, dtype=bool)
    nodes = np.empty(count, dtype=float)
    idx = 0  # start at +1
    nodes[0] = grid[idx]
    selected[idx] = True
    logprod = np.log(np.maximum(np.abs(grid - nodes[0]), np.finfo(float).tiny))
    logprod[selected] = -np.inf
    for j in range(1, count):
        idx = int(np.argmax(logprod))
        nodes[j] = grid[idx]
        selected[idx] = True
        logprod += np.log(np.maximum(np.abs(grid - nodes[j]), np.finfo(float).tiny))
        logprod[selected] = -np.inf
    _LEJA_CACHE[key] = nodes
    return nodes


def _newton_coefficients(nodes: np.ndarray, values: np.ndarray) -> np.ndarray:
    c = np.asarray(values, dtype=np.complex128).copy()
    n = len(nodes)
    for j in range(1, n):
        c[j:n] = (c[j:n] - c[j-1:n-1]) / (nodes[j:n] - nodes[:n-j])
    return c


@dataclass(frozen=True)
class LejaOptions:
    tol: float = 1e-10
    min_degree: int = 8
    max_degree: int = 80
    target_width: float = 12.0
    candidate_count: int = 4097
    consecutive_small: int = 2

    def __post_init__(self):
        if self.tol <= 0:
            raise ValueError("tol must be positive")
        if self.min_degree < 2 or self.max_degree < self.min_degree:
            raise ValueError("invalid degree range")
        if self.target_width <= 0:
            raise ValueError("target_width must be positive")


class _CountingOperator:
    def __init__(self, op, counter):
        self.op = aslinearoperator(op)
        if self.op.shape[0] != self.op.shape[1]:
            raise ValueError("LejaBackend requires a square operator")
        self.shape = self.op.shape
        self.dtype = self.op.dtype
        self.counter = counter

    def matvec(self, x):
        self.counter()
        return np.asarray(self.op.matvec(x))


class _LejaContext:
    def __init__(self, backend: "LejaBackend", operator, h: float, bounds):
        self.backend = backend
        self.h = float(h)
        self.op = _CountingOperator(operator, self._count)
        self.n = self.op.shape[0]
        self.bounds = tuple(map(float, bounds))

    def _count(self):
        self.backend._stats["matvecs"] += 1

    def _exp_step(self, matvec, dimension: int, x: np.ndarray, lo: float, hi: float):
        opts = self.backend.options
        center = 0.5 * (lo + hi)
        radius = 0.5 * (hi - lo)
        if radius <= 100 * np.finfo(float).eps * max(1.0, abs(center)):
            # Only safe for a genuinely scalar operator; augmented nilpotent zero-spectrum
            # cases are handled exactly before reaching here.
            return np.exp(center) * np.asarray(x), 0

        nodes = _real_leja_nodes(opts.max_degree + 1, opts.candidate_count)
        values = np.exp(center + radius * nodes)
        coeff = _newton_coefficients(nodes, values)

        x = np.asarray(x, dtype=np.result_type(x.dtype, np.complex128))
        out = coeff[0] * x
        newton_vec = x.copy()
        small_count = 0
        used = 0

        def Bmv(v):
            return (np.asarray(matvec(v)) - center * v) / radius

        for j in range(1, opts.max_degree + 1):
            newton_vec = Bmv(newton_vec) - nodes[j-1] * newton_vec
            inc = coeff[j] * newton_vec
            out = out + inc
            used = j
            if j >= opts.min_degree:
                denom = max(float(np.linalg.norm(out)), float(np.linalg.norm(x)), 1.0)
                rel = float(np.linalg.norm(inc)) / denom
                if rel <= opts.tol:
                    small_count += 1
                    if small_count >= opts.consecutive_small:
                        self.backend._stats["last_increment_estimate"] = rel
                        return np.real_if_close(out), used
                else:
                    small_count = 0

        self.backend._stats["nonconverged_actions"] += 1
        raise LejaConvergenceError(
            f"Real-Leja interpolation failed to reach tol={opts.tol:g} by degree {opts.max_degree}."
        )

    def _adaptive_exp_action(self, matvec, dimension: int, x0: np.ndarray, lo: float, hi: float, output_size: int):
        width = max(0.0, hi - lo)
        nsub = max(1, int(math.ceil(width / self.backend.options.target_width)))
        x = np.asarray(x0, dtype=np.result_type(x0.dtype, np.complex128))
        slo, shi = lo / nsub, hi / nsub

        def scaled_mv(v):
            return np.asarray(matvec(v)) / nsub

        for _ in range(nsub):
            x, degree = self._exp_step(scaled_mv, dimension, x, slo, shi)
            self.backend._stats["polynomial_steps"] += 1
            self.backend._stats["degree_sum"] += degree
            self.backend._stats["max_degree_used"] = max(self.backend._stats["max_degree_used"], degree)
        self.backend._stats["substeps"] += nsub
        return np.asarray(np.real_if_close(x[:output_size]))

    def _function_action(self, terms, v: np.ndarray):
        """Interpolate a scalar analytic coefficient f(A)v directly on spec(A)."""
        from .diagonal import _phi_scalar_array
        opts = self.backend.options
        v = np.asarray(v)
        if v.ndim != 1 or v.size != self.n:
            raise ValueError("vector must match operator dimension")
        if not terms:
            return np.zeros_like(v)

        a, b = self.bounds
        center = 0.5 * (a + b)
        radius = 0.5 * (b - a)
        if radius <= 100*np.finfo(float).eps*max(1.0, abs(center)):
            val = 0.0 + 0.0j
            for alpha, k, scale in terms:
                z = np.array([scale*self.h*center], dtype=np.complex128)
                val += alpha * _phi_scalar_array(k, z)[0]
            return np.real_if_close(val * v)

        nodes = _real_leja_nodes(opts.max_degree + 1, opts.candidate_count)
        lambdas = center + radius * nodes
        values = np.zeros(nodes.size, dtype=np.complex128)
        for alpha, k, scale in terms:
            values += alpha * _phi_scalar_array(k, scale*self.h*lambdas)
        coeff = _newton_coefficients(nodes, values)

        dtype = np.result_type(v.dtype, np.complex128)
        vv = np.asarray(v, dtype=dtype)
        out = coeff[0]*vv
        newton_vec = vv.copy()
        small_count = 0
        used = 0

        def Bmv(x):
            return (self.op.matvec(x) - center*x)/radius

        for j in range(1, opts.max_degree + 1):
            newton_vec = Bmv(newton_vec) - nodes[j-1]*newton_vec
            inc = coeff[j]*newton_vec
            out += inc
            used = j
            if j >= opts.min_degree:
                denom = max(float(np.linalg.norm(out)), float(np.linalg.norm(vv)), 1.0)
                rel = float(np.linalg.norm(inc))/denom
                if rel <= opts.tol:
                    small_count += 1
                    if small_count >= opts.consecutive_small:
                        self.backend._stats["polynomial_steps"] += 1
                        self.backend._stats["degree_sum"] += used
                        self.backend._stats["max_degree_used"] = max(self.backend._stats["max_degree_used"], used)
                        self.backend._stats["last_increment_estimate"] = rel
                        return np.real_if_close(out)
                else:
                    small_count = 0
        self.backend._stats["nonconverged_actions"] += 1
        raise LejaConvergenceError(
            f"Real-Leja coefficient interpolation failed to reach tol={opts.tol:g} by degree {opts.max_degree}."
        )

    def phi_linear_combination_action(self, vectors_by_k: dict[int, np.ndarray], *, scale: float = 1.0):
        """Compute sum_k phi_k(scale*h*A)b_k without augmented nonnormal blocks.

        Leja interpolation is applied separately to each distinct right-hand side.
        This intentionally trades more matvecs for robustness on high-order phi
        combinations; unlike the Krylov backends, Phase-5 Leja does not fuse RHSs.
        """
        clean = {int(k): np.asarray(v) for k, v in vectors_by_k.items() if np.linalg.norm(v) != 0.0}
        if not clean:
            return np.zeros(self.n)
        self.backend._stats["linear_combination_actions"] += 1
        out = np.zeros(self.n, dtype=np.result_type(*[v.dtype for v in clean.values()], np.complex128))
        for k, v in clean.items():
            out += self._function_action(((1.0, k, float(scale)),), v)
        return np.real_if_close(out)

    def phi_combination_action(self, terms, v: np.ndarray):
        packed = tuple((float(t.alpha), int(t.k), float(t.scale)) for t in terms if t.alpha != 0.0)
        self.backend._stats["combination_actions"] += 1
        return self._function_action(packed, np.asarray(v))

    def phi_action(self, k: int, scale: float, v: np.ndarray):
        self.backend._stats["single_phi_actions"] += 1
        return self._function_action(((1.0, int(k), float(scale)),), np.asarray(v))

    def sum_operator_actions(self, exprs, vectors):
        # Do not fuse distinct right-hand sides in the Phase-5 real-Leja backend.
        # The solver will apply each analytic coefficient independently.
        return None

    def shifted_solve_action(self, alpha: float, v: np.ndarray):
        a = float(alpha)
        v = np.asarray(v)
        dtype = np.result_type(v.dtype, self.op.dtype if self.op.dtype is not None else float)
        def mv(x):
            return np.asarray(x) - a * self.h * self.op.matvec(x)
        M = LinearOperator((self.n, self.n), matvec=mv, dtype=dtype)
        x, info = gmres_compat(M, v, rtol=self.backend.options.tol, atol=0.0, restart=min(40, self.n))
        if info != 0:
            raise LejaConvergenceError(f"GMRES shifted solve failed with info={info}")
        self.backend._stats["shifted_solves"] += 1
        return np.real_if_close(x)


class LejaBackend(Backend):
    """Matrix-free real-Leja backend for operators with a real spectral interval."""

    name = "leja"

    def __init__(self, *, tol=1e-10, spectral_bounds=None, min_degree=8, max_degree=80,
                 target_width=12.0, candidate_count=4097):
        self.options = LejaOptions(tol, min_degree, max_degree, target_width, candidate_count)
        self.spectral_bounds = spectral_bounds
        self._bounds_cache = {}
        self.reset_stats()

    def reset_stats(self):
        self._stats = {
            "matvecs": 0,
            "polynomial_steps": 0,
            "substeps": 0,
            "degree_sum": 0,
            "max_degree_used": 0,
            "nonconverged_actions": 0,
            "linear_combination_actions": 0,
            "combination_actions": 0,
            "single_phi_actions": 0,
            "fused_sum_actions": 0,
            "shifted_solves": 0,
            "last_increment_estimate": None,
        }

    def stats(self):
        out = dict(self._stats)
        steps = out["polynomial_steps"]
        out["mean_degree"] = out["degree_sum"] / steps if steps else 0.0
        out["tolerance"] = self.options.tol
        return out

    def _infer_bounds(self, operator):
        if self.spectral_bounds is not None:
            a, b = map(float, self.spectral_bounds)
            if a > b:
                a, b = b, a
            return a, b
        key = id(operator)
        if key in self._bounds_cache:
            return self._bounds_cache[key]
        if isinstance(operator, np.ndarray) and operator.ndim == 1:
            bounds = (float(np.min(operator)), float(np.max(operator)))
        elif isinstance(operator, np.ndarray) and operator.ndim == 2:
            if not np.allclose(operator, operator.T.conj(), rtol=1e-11, atol=1e-13):
                raise ValueError("automatic Leja bounds require a Hermitian operator")
            ev = np.linalg.eigvalsh(operator)
            bounds = (float(ev[0]), float(ev[-1]))
        elif issparse(operator):
            # Real symmetric/Hermitian sparse path.
            diff = operator - operator.T.conjugate()
            if diff.nnz and np.max(np.abs(diff.data)) > 1e-12:
                raise ValueError("automatic Leja bounds require a Hermitian sparse operator")
            # Cheap conservative Gershgorin interval; avoids an eigenvalue solve
            # inside automatic backend selection.
            diag = np.asarray(operator.diagonal()).real
            row_abs = np.asarray(np.abs(operator).sum(axis=1)).ravel()
            radius = row_abs - np.abs(diag)
            bounds = (float(np.min(diag - radius)), float(np.max(diag + radius)))
        else:
            raise ValueError("LinearOperator use requires explicit spectral_bounds=(lambda_min, lambda_max)")
        self._bounds_cache[key] = bounds
        return bounds

    def bind(self, linear_operator, h: float):
        ctx = _LejaContext(self, linear_operator, h, self._infer_bounds(linear_operator))
        self._stats["max_operator_dimension"] = max(
            self._stats.get("max_operator_dimension", 0), ctx.n
        )
        return ctx
