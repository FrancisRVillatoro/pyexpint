from __future__ import annotations

"""Independent KIOPS-style backend.

This module implements the core numerical ideas of Gaudreault, Rainwater &
Tokman (2018): augmented-matrix evaluation of phi combinations, incomplete
orthogonalization with a short recurrence, residual-based local error
estimation, and adaptive Krylov dimension/substepping.

It is a fresh Python implementation from the published algorithmic description;
it is not a translation of the LGPL MATLAB reference implementation.
"""

from dataclasses import dataclass
import math
import numpy as np
from scipy.linalg import expm
from scipy.sparse.linalg import LinearOperator, aslinearoperator

from .base import Backend
from ._scipy_compat import gmres_compat


class KiopsConvergenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class KiopsOptions:
    tol: float = 1e-10
    m_init: int = 12
    m_min: int = 8
    m_max: int = 64
    orth_len: int = 2
    delta: float = 1.4
    breakdown_tol: float = 1e-14

    def __post_init__(self):
        if self.tol <= 0:
            raise ValueError("tol must be positive")
        if self.m_min < 2 or self.m_max < self.m_min:
            raise ValueError("require 2 <= m_min <= m_max")
        if self.orth_len < 1:
            raise ValueError("orth_len must be positive")


class _CountingOperator:
    def __init__(self, operator, counter):
        self.operator = aslinearoperator(operator)
        if self.operator.shape[0] != self.operator.shape[1]:
            raise ValueError("KiopsBackend requires a square operator")
        self.shape = self.operator.shape
        self.dtype = self.operator.dtype
        self._counter = counter

    def matvec(self, x):
        self._counter()
        return np.asarray(self.operator.matvec(x))


class _KiopsContext:
    def __init__(self, backend: "KiopsBackend", operator, h: float):
        self.backend = backend
        self.h = float(h)
        self.op = _CountingOperator(operator, self._count_matvec)
        self.n = self.op.shape[0]

    def _count_matvec(self):
        self.backend._stats["matvecs"] += 1

    def _iop_basis(self, matvec, dimension: int, x: np.ndarray, m: int):
        beta = float(np.linalg.norm(x))
        if beta == 0.0:
            return None, None, 0.0, 0, True
        dtype = np.result_type(x.dtype, np.complex128)
        V = np.zeros((dimension, m + 1), dtype=dtype)
        H = np.zeros((m + 1, m + 1), dtype=dtype)
        V[:, 0] = x / beta
        used = 0
        happy = False
        for j in range(m):
            w = np.asarray(matvec(V[:, j]), dtype=dtype)
            i0 = max(0, j - self.backend.options.orth_len + 1)
            for i in range(i0, j + 1):
                hij = np.vdot(V[:, i], w)
                H[i, j] = hij
                w -= hij * V[:, i]
            nrm = float(np.linalg.norm(w))
            H[j + 1, j] = nrm
            used = j + 1
            self.backend._stats["krylov_steps"] += 1
            if nrm <= self.backend.options.breakdown_tol:
                happy = True
                break
            V[:, j + 1] = w / nrm
        return V, H, beta, used, happy

    def _adaptive_exp_action(self, matvec, dimension: int, x0: np.ndarray, *, output_size: int):
        """Approximate exp(M)x0 by adaptive IOP substeps over unit time."""
        opts = self.backend.options
        x = np.asarray(x0, dtype=np.result_type(x0.dtype, np.complex128))
        if np.linalg.norm(x) == 0:
            return np.zeros(output_size, dtype=x.dtype)

        tnow = 0.0
        tau = 1.0
        m = max(opts.m_min, min(opts.m_init, opts.m_max, dimension))
        gamma = 0.9
        gamma_mmax = 0.6
        eps = np.finfo(float).eps

        while tnow < 1.0 - 16 * eps:
            remaining = 1.0 - tnow
            tau = min(tau, remaining)
            accepted = False
            rejects_here = 0

            while not accepted:
                V, H, beta, used, happy = self._iop_basis(matvec, dimension, x, m)
                if used == 0:
                    return np.zeros(output_size, dtype=x.dtype)

                # KIOPS residual estimator: append a phi_1 column to projected H.
                Hp = np.array(H[:used + 1, :used + 1], copy=True)
                hnext = Hp[used, used - 1] if used < H.shape[0] else 0.0
                Hp[used, used - 1] = 0.0
                Hp[0, used] = 1.0
                F = expm(tau * Hp)
                self.backend._stats["small_exponentials"] += 1
                approx = beta * (V[:, :used] @ F[:used, 0])

                if happy:
                    omega = 0.0
                    err = 0.0
                else:
                    err = abs(beta * hnext * F[used - 1, used])
                    omega = err / max(tau * opts.tol, np.finfo(float).tiny)

                self.backend._stats["last_local_error"] = float(err)
                self.backend._stats["last_omega"] = float(omega)
                self.backend._stats["max_krylov_dim_used"] = max(
                    self.backend._stats["max_krylov_dim_used"], used
                )
                self.backend._stats["krylov_dim_sum"] += used
                self.backend._stats["projections"] += 1

                if happy or omega <= opts.delta:
                    x = np.asarray(approx)
                    tnow += tau
                    self.backend._stats["accepted_substeps"] += 1
                    accepted = True

                    # Residual-based next-step proposal, with conservative clipping.
                    if omega <= 1e-14:
                        fac = 2.0
                    else:
                        order_est = max(1.0, used / 4.0)
                        fac = (gamma / omega) ** (1.0 / order_est)
                        fac = min(2.5, max(0.5, fac))
                    tau *= fac

                    # Keep dimensions moderate: reduce after very easy steps, grow near limit.
                    if omega < 0.05 and m > opts.m_min:
                        m = max(opts.m_min, int(math.floor(0.85 * m)))
                    elif omega > 0.8 and m < opts.m_max:
                        m = min(opts.m_max, int(math.ceil(1.2 * m)))
                else:
                    rejects_here += 1
                    self.backend._stats["rejected_substeps"] += 1
                    if m < opts.m_max:
                        m_new = max(m + 2, int(math.ceil(1.25 * m)))
                        m = min(opts.m_max, m_new)
                    else:
                        order_est = max(1.0, used / 4.0)
                        fac = (gamma_mmax / omega) ** (1.0 / order_est)
                        tau *= min(0.8, max(0.2, fac))
                    if rejects_here > 20:
                        raise KiopsConvergenceError(
                            f"KIOPS-style action failed after {rejects_here} rejections; "
                            f"last omega={omega:.3e}, m={m}, tau={tau:.3e}."
                        )

        return np.asarray(np.real_if_close(x[:output_size]))

    def phi_linear_combination_action(self, vectors_by_k: dict[int, np.ndarray], *, scale: float = 1.0):
        clean = {int(k): np.asarray(v) for k, v in vectors_by_k.items() if np.linalg.norm(v) != 0.0}
        if not clean:
            return np.zeros(self.n)
        if any(k < 0 for k in clean):
            raise ValueError("phi index must be nonnegative")
        if any(v.ndim != 1 or v.size != self.n for v in clean.values()):
            raise ValueError("all vectors must match the operator dimension")

        self.backend._stats["linear_combination_actions"] += 1
        p = max(clean)
        # phi_k(0)=1/k!: handle scale zero exactly.
        if float(scale) == 0.0:
            out = np.zeros(self.n, dtype=np.result_type(*[v.dtype for v in clean.values()], float))
            for k, v in clean.items():
                out += v / math.factorial(k)
            return np.real_if_close(out)

        dtype = np.result_type(*[v.dtype for v in clean.values()], np.complex128)
        b0 = np.asarray(clean.get(0, np.zeros(self.n)), dtype=dtype)
        bcols = [np.asarray(clean.get(j, np.zeros(self.n)), dtype=dtype) for j in range(1, p + 1)]
        x0 = np.zeros(self.n + p, dtype=dtype)
        x0[:self.n] = b0
        if p:
            x0[self.n] = 1.0

        sh = float(scale) * self.h

        def aug_mv(x):
            xu = x[:self.n]
            q = x[self.n:]
            top = sh * self.op.matvec(xu)
            for j, bj in enumerate(bcols):
                top = top + q[j] * bj
            bottom = np.zeros(p, dtype=dtype)
            if p > 1:
                bottom[1:] = q[:-1]
            return np.concatenate([top, bottom])

        return self._adaptive_exp_action(aug_mv, self.n + p, x0, output_size=self.n)

    def phi_combination_action(self, terms, v: np.ndarray):
        # Group by time scale; each group is one KIOPS augmented action.
        groups: dict[float, dict[int, np.ndarray]] = {}
        v = np.asarray(v)
        for term in terms:
            if term.alpha == 0:
                continue
            g = groups.setdefault(float(term.scale), {})
            if term.k not in g:
                g[term.k] = np.zeros_like(v, dtype=np.result_type(v.dtype, np.complex128))
            g[term.k] += term.alpha * v
        if not groups:
            return np.zeros_like(v)
        out = np.zeros_like(v, dtype=np.result_type(v.dtype, np.complex128))
        for scale, by_k in groups.items():
            out += self.phi_linear_combination_action(by_k, scale=scale)
        self.backend._stats["combination_actions"] += 1
        return np.real_if_close(out)

    def phi_action(self, k: int, scale: float, v: np.ndarray):
        self.backend._stats["single_phi_actions"] += 1
        return self.phi_linear_combination_action({int(k): np.asarray(v)}, scale=float(scale))

    def sum_operator_actions(self, exprs, vectors):
        from ..expressions import PhiCombination, ZeroExpr
        pairs = []
        scales = set()
        for expr, vec in zip(exprs, vectors):
            if isinstance(expr, ZeroExpr):
                continue
            if not isinstance(expr, PhiCombination):
                return None
            for term in expr.terms:
                scales.add(float(term.scale))
            pairs.append((expr, np.asarray(vec)))
        if not pairs:
            return np.zeros_like(vectors[0])
        if len(pairs) == 1 or len(scales) != 1:
            return None
        scale = next(iter(scales))
        by_k: dict[int, np.ndarray] = {}
        for expr, vec in pairs:
            for term in expr.terms:
                by_k.setdefault(
                    int(term.k), np.zeros_like(vec, dtype=np.result_type(vec.dtype, np.complex128))
                )
                by_k[int(term.k)] += term.alpha * vec
        self.backend._stats["fused_sum_actions"] += 1
        return self.phi_linear_combination_action(by_k, scale=scale)

    def shifted_solve_action(self, alpha: float, v: np.ndarray):
        a = float(alpha)
        v = np.asarray(v)
        dtype = np.result_type(v.dtype, self.op.dtype if self.op.dtype is not None else float)
        def mv(x):
            return np.asarray(x) - a * self.h * self.op.matvec(x)
        M = LinearOperator((self.n, self.n), matvec=mv, dtype=dtype)
        self.backend._stats["shifted_solves"] += 1
        x, info = gmres_compat(M, v, rtol=self.backend.options.tol, atol=0.0, restart=min(40, self.n))
        if info != 0:
            raise KiopsConvergenceError(f"GMRES shifted solve failed with info={info}")
        return np.real_if_close(x)


class KiopsBackend(Backend):
    """Adaptive incomplete-orthogonalization phi-action backend.

    This is an independent KIOPS-style implementation.  It follows the published
    augmented-matrix/IOP/residual-adaptivity design but intentionally does not
    reproduce the reference MATLAB source line-for-line.
    """

    name = "kiops"

    def __init__(self, *, tol=1e-10, m_init=12, m_min=8, m_max=64, orth_len=2, delta=1.4):
        self.options = KiopsOptions(tol, m_init, m_min, m_max, orth_len, delta)
        self.reset_stats()

    def reset_stats(self):
        self._stats = {
            "matvecs": 0,
            "accepted_substeps": 0,
            "rejected_substeps": 0,
            "krylov_steps": 0,
            "small_exponentials": 0,
            "projections": 0,
            "krylov_dim_sum": 0,
            "max_krylov_dim_used": 0,
            "linear_combination_actions": 0,
            "combination_actions": 0,
            "single_phi_actions": 0,
            "fused_sum_actions": 0,
            "shifted_solves": 0,
            "last_local_error": None,
            "last_omega": None,
        }

    def stats(self):
        out = dict(self._stats)
        p = out["projections"]
        out["mean_krylov_dim"] = out["krylov_dim_sum"] / p if p else 0.0
        out["tolerance"] = self.options.tol
        out["orth_len"] = self.options.orth_len
        return out

    def bind(self, linear_operator, h: float):
        ctx = _KiopsContext(self, linear_operator, h)
        self._stats["max_operator_dimension"] = max(
            self._stats.get("max_operator_dimension", 0), ctx.n
        )
        return ctx
