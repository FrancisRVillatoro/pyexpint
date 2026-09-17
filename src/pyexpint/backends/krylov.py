from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np
from scipy.linalg import expm
from scipy.sparse.linalg import aslinearoperator, LinearOperator

from .base import Backend
from ._scipy_compat import gmres_compat


class KrylovConvergenceError(RuntimeError):
    """Raised when the requested Krylov tolerance is not reached."""


@dataclass(frozen=True)
class KrylovOptions:
    """Parameters for the adaptive Arnoldi evaluator.

    The convergence estimator is the relative difference between projected
    approximations at successive Krylov dimensions.  This is a practical
    heuristic estimator, not a rigorous a-posteriori bound.
    """

    tol: float = 1e-10
    min_dim: int = 8
    max_dim: int = 48
    check_every: int = 4
    breakdown_tol: float = 1e-14
    reorthogonalize: bool = True

    def __post_init__(self):
        if not (self.tol > 0):
            raise ValueError("tol must be positive.")
        if self.min_dim < 1:
            raise ValueError("min_dim must be >= 1.")
        if self.max_dim < self.min_dim:
            raise ValueError("max_dim must be >= min_dim.")
        if self.check_every < 1:
            raise ValueError("check_every must be >= 1.")
        if self.breakdown_tol <= 0:
            raise ValueError("breakdown_tol must be positive.")


class _CountingOperator:
    def __init__(self, operator, on_matvec):
        self.operator = aslinearoperator(operator)
        if len(self.operator.shape) != 2 or self.operator.shape[0] != self.operator.shape[1]:
            raise ValueError("KrylovBackend requires a square linear operator.")
        self.shape = self.operator.shape
        self.dtype = self.operator.dtype
        self._on_matvec = on_matvec

    def matvec(self, v):
        self._on_matvec()
        return np.asarray(self.operator.matvec(v))


class _KrylovContext:
    def __init__(self, backend: "KrylovBackend", linear_operator, h: float):
        self.backend = backend
        self.h = float(h)
        self.op = _CountingOperator(linear_operator, self._count_matvec)
        self.n = self.op.shape[0]

    def _count_matvec(self):
        self.backend._stats["matvecs"] += 1

    # ---------- small projected phi machinery ----------
    @staticmethod
    def _small_phi_columns(H: np.ndarray, scale_h: float, kmax: int) -> list[np.ndarray]:
        """Return phi_k(scale_h*H)e1, k=0..kmax.

        A single augmented exponential of dimension m+kmax is used for all
        k>=1 at a fixed scale.  This is independent of the large operator size.
        """
        m = H.shape[0]
        dtype = np.result_type(H.dtype, np.complex128)
        Z = scale_h * np.asarray(H, dtype=dtype)
        e1 = np.zeros(m, dtype=dtype)
        e1[0] = 1

        if kmax == 0:
            return [expm(Z) @ e1]

        M = np.zeros((m + kmax, m + kmax), dtype=dtype)
        M[:m, :m] = Z
        M[:m, m] = e1
        if kmax > 1:
            for j in range(kmax - 1):
                M[m + j, m + j + 1] = 1
        EM = expm(M)

        cols = [EM[:m, :m] @ e1]
        # appended column j (0-based) is phi_{j+1}(Z)e1
        for j in range(kmax):
            cols.append(EM[:m, m + j])
        return cols

    @classmethod
    def _projected_combination(
        cls,
        V: np.ndarray,
        H: np.ndarray,
        beta: float,
        terms: tuple[tuple[float, int, float], ...],
        h: float,
    ) -> np.ndarray:
        m = H.shape[0]
        coeff = np.zeros(m, dtype=np.result_type(H.dtype, np.complex128))

        # Group by scale so all phi_k at the same scale use one small expm.
        groups: dict[float, list[tuple[float, int]]] = {}
        for alpha, k, scale in terms:
            groups.setdefault(float(scale), []).append((float(alpha), int(k)))

        for scale, gterms in groups.items():
            kmax = max(k for _, k in gterms)
            cols = cls._small_phi_columns(H, scale * h, kmax)
            for alpha, k in gterms:
                coeff += alpha * cols[k]

        return np.real_if_close(beta * (V[:, :m] @ coeff))

    # ---------- Arnoldi ----------
    def _arnoldi_combination(
        self,
        terms: tuple[tuple[float, int, float], ...],
        v: np.ndarray,
    ) -> np.ndarray:
        opts = self.backend.options
        v = np.asarray(v)
        if v.ndim != 1 or v.size != self.n:
            raise ValueError("Vector shape does not match the LinearOperator.")

        beta = float(np.linalg.norm(v))
        if beta == 0.0:
            self.backend._stats["zero_actions"] += 1
            return np.zeros_like(v)

        dtype = np.result_type(v.dtype, self.op.dtype if self.op.dtype is not None else float, np.complex128)
        max_m = min(opts.max_dim, self.n)
        V = np.zeros((self.n, max_m + 1), dtype=dtype)
        H = np.zeros((max_m + 1, max_m), dtype=dtype)
        V[:, 0] = v / beta

        previous = None
        last = None
        last_err = math.inf
        converged = False
        used_m = 0

        for j in range(max_m):
            w = np.asarray(self.op.matvec(V[:, j]), dtype=dtype)

            # Modified Gram-Schmidt.
            for i in range(j + 1):
                hij = np.vdot(V[:, i], w)
                H[i, j] += hij
                w -= hij * V[:, i]

            if opts.reorthogonalize:
                for i in range(j + 1):
                    corr = np.vdot(V[:, i], w)
                    H[i, j] += corr
                    w -= corr * V[:, i]

            hnext = float(np.linalg.norm(w))
            H[j + 1, j] = hnext
            m = j + 1
            used_m = m

            breakdown = hnext <= opts.breakdown_tol
            if not breakdown and m < max_m:
                V[:, m] = w / hnext

            should_check = (
                m >= opts.min_dim
                and (m == opts.min_dim or (m - opts.min_dim) % opts.check_every == 0)
            ) or breakdown or m == max_m

            if should_check:
                Hm = H[:m, :m]
                current = self._projected_combination(V, Hm, beta, terms, self.h)
                self.backend._stats["projection_evaluations"] += 1
                last = current

                if breakdown:
                    converged = True
                    last_err = 0.0
                    self.backend._stats["happy_breakdowns"] += 1
                    break

                if previous is not None:
                    denom = max(float(np.linalg.norm(current)), beta, 1.0)
                    last_err = float(np.linalg.norm(current - previous)) / denom
                    if last_err <= opts.tol:
                        converged = True
                        break
                previous = current

        if last is None:
            Hm = H[:used_m, :used_m]
            last = self._projected_combination(V, Hm, beta, terms, self.h)
            self.backend._stats["projection_evaluations"] += 1

        self.backend._stats["krylov_projections"] += 1
        self.backend._stats["krylov_dim_sum"] += used_m
        self.backend._stats["max_krylov_dim_used"] = max(
            self.backend._stats["max_krylov_dim_used"], used_m
        )
        self.backend._stats["last_error_estimate"] = last_err

        if not converged:
            self.backend._stats["nonconverged_actions"] += 1
            if self.backend.fail_on_nonconvergence:
                raise KrylovConvergenceError(
                    f"Krylov action did not reach tol={opts.tol:g} by m={used_m}; "
                    f"last relative successive-projection estimate={last_err:.3e}."
                )

        return np.asarray(np.real_if_close(last))

    def _arnoldi_exp_action(self, matvec, dimension: int, v: np.ndarray, *, output_size: int) -> np.ndarray:
        """Adaptive Arnoldi approximation to exp(M)v for a matrix-free M.

        ``matvec`` is deliberately generic; in the augmented phi-combination
        use case, each call performs exactly one matvec with the original A.
        Convergence is monitored only on the first ``output_size`` components.
        """
        opts = self.backend.options
        v = np.asarray(v)
        beta = float(np.linalg.norm(v))
        if beta == 0.0:
            return np.zeros(output_size, dtype=v.dtype)

        dtype = np.result_type(v.dtype, np.complex128)
        max_m = min(opts.max_dim, dimension)
        V = np.zeros((dimension, max_m + 1), dtype=dtype)
        H = np.zeros((max_m + 1, max_m), dtype=dtype)
        V[:, 0] = v / beta

        previous = None
        last_top = None
        last_err = math.inf
        converged = False
        used_m = 0

        for j in range(max_m):
            w = np.asarray(matvec(V[:, j]), dtype=dtype)
            for i in range(j + 1):
                hij = np.vdot(V[:, i], w)
                H[i, j] += hij
                w -= hij * V[:, i]
            if opts.reorthogonalize:
                for i in range(j + 1):
                    corr = np.vdot(V[:, i], w)
                    H[i, j] += corr
                    w -= corr * V[:, i]

            hnext = float(np.linalg.norm(w))
            H[j + 1, j] = hnext
            m = j + 1
            used_m = m
            breakdown = hnext <= opts.breakdown_tol
            if not breakdown and m < max_m:
                V[:, m] = w / hnext

            should_check = (
                m >= opts.min_dim
                and (m == opts.min_dim or (m - opts.min_dim) % opts.check_every == 0)
            ) or breakdown or m == max_m

            if should_check:
                e1 = np.zeros(m, dtype=dtype)
                e1[0] = 1
                coeff = expm(H[:m, :m]) @ e1
                current = beta * (V[:, :m] @ coeff)
                top = np.asarray(np.real_if_close(current[:output_size]))
                self.backend._stats["projection_evaluations"] += 1
                last_top = top

                if breakdown:
                    converged = True
                    last_err = 0.0
                    self.backend._stats["happy_breakdowns"] += 1
                    break
                if previous is not None:
                    denom = max(float(np.linalg.norm(top)), 1.0)
                    last_err = float(np.linalg.norm(top - previous)) / denom
                    if last_err <= opts.tol:
                        converged = True
                        break
                previous = top

        self.backend._stats["krylov_projections"] += 1
        self.backend._stats["augmented_krylov_projections"] += 1
        self.backend._stats["krylov_dim_sum"] += used_m
        self.backend._stats["max_krylov_dim_used"] = max(
            self.backend._stats["max_krylov_dim_used"], used_m
        )
        self.backend._stats["last_error_estimate"] = last_err

        if not converged:
            self.backend._stats["nonconverged_actions"] += 1
            if self.backend.fail_on_nonconvergence:
                raise KrylovConvergenceError(
                    f"Augmented Krylov action did not reach tol={opts.tol:g} by m={used_m}; "
                    f"last relative successive-projection estimate={last_err:.3e}."
                )
        return np.asarray(last_top)

    def phi_linear_combination_action(
        self,
        vectors_by_k: dict[int, np.ndarray],
        *,
        scale: float = 1.0,
    ) -> np.ndarray:
        """Compute sum_k phi_k(scale*h*A) b_k with one augmented projection.

        This is the large-scale combination primitive needed by exponential
        integrators.  It follows the standard polynomial-forcing augmentation:

            u' = Z u + sum_{j>=1} t^(j-1)/(j-1)! b_j,

        whose value at t=1 is exp(Z)b_0 + sum phi_j(Z)b_j.
        """
        clean = {
            int(k): np.asarray(v)
            for k, v in vectors_by_k.items()
            if np.linalg.norm(v) != 0.0
        }
        if not clean:
            return np.zeros(self.n)
        if any(k < 0 for k in clean):
            raise ValueError("phi index must be nonnegative.")
        if any(v.ndim != 1 or v.size != self.n for v in clean.values()):
            raise ValueError("All b_k vectors must match the operator dimension.")

        self.backend._stats["linear_combination_actions"] += 1
        self.backend._stats["phi_terms_requested"] += len(clean)

        if len(clean) == 1:
            k, vec = next(iter(clean.items()))
            return self.phi_action(k, scale, vec)

        p = max(clean)

        dtype = np.result_type(*[v.dtype for v in clean.values()], np.complex128)
        b0 = np.asarray(clean.get(0, np.zeros(self.n)), dtype=dtype)
        bcols = [np.asarray(clean.get(j, np.zeros(self.n)), dtype=dtype) for j in range(1, p + 1)]

        x0 = np.zeros(self.n + p, dtype=dtype)
        x0[:self.n] = b0
        x0[self.n] = 1.0  # q(0)=e1

        def augmented_matvec(x):
            xu = x[:self.n]
            q = x[self.n:]
            top = float(scale) * self.h * self.op.matvec(xu)
            for j, bj in enumerate(bcols):
                top = top + q[j] * bj
            bottom = np.zeros(p, dtype=dtype)
            if p > 1:
                bottom[1:] = q[:-1]  # nilpotent Jordan chain
            return np.concatenate([top, bottom])

        return self._arnoldi_exp_action(
            augmented_matvec,
            self.n + p,
            x0,
            output_size=self.n,
        )

    def sum_operator_actions(self, exprs, vectors):
        """Try to fuse sum expr_j(A) v_j into one augmented phi action.

        Fusion is possible when all nonzero expressions are PhiCombinations and
        all their terms use one common scale.  Otherwise return ``None`` and the
        generic solver falls back to independent expression applications.
        """
        from ..expressions import PhiCombination, ZeroExpr

        if not self.backend.fuse_sums:
            return None

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
        # One coefficient acting on one vector is already optimally handled by
        # PhiCombination.apply using one standard Arnoldi basis.  The augmented
        # route is reserved for genuinely distinct right-hand sides.
        if len(pairs) == 1:
            return None
        if len(scales) != 1:
            return None
        scale = next(iter(scales))

        by_k: dict[int, np.ndarray] = {}
        for expr, vec in pairs:
            for term in expr.terms:
                if term.k not in by_k:
                    by_k[term.k] = np.zeros_like(vec, dtype=np.result_type(vec.dtype, np.complex128))
                by_k[term.k] = by_k[term.k] + term.alpha * vec

        self.backend._stats["fused_sum_actions"] += 1
        return self.phi_linear_combination_action(by_k, scale=scale)

    def phi_combination_action(self, terms, v: np.ndarray) -> np.ndarray:
        """Apply a linear combination of phi-functions using one Arnoldi basis."""
        packed = tuple((float(t.alpha), int(t.k), float(t.scale)) for t in terms if t.alpha != 0.0)
        if not packed:
            return np.zeros_like(v)
        self.backend._stats["combination_actions"] += 1
        self.backend._stats["phi_terms_requested"] += len(packed)
        return self._arnoldi_combination(packed, v)

    def phi_action(self, k: int, scale: float, v: np.ndarray) -> np.ndarray:
        self.backend._stats["single_phi_actions"] += 1
        return self._arnoldi_combination(((1.0, int(k), float(scale)),), v)

    def shifted_solve_action(self, alpha: float, v: np.ndarray) -> np.ndarray:
        """Solve (I-alpha*h*A)x=v using matrix-free GMRES.

        This path exists for the historical Crank--Nicolson comparator; it is
        not part of the exponential phi-action machinery.
        """
        v = np.asarray(v)
        if v.ndim != 1 or v.size != self.n:
            raise ValueError("Vector shape does not match the LinearOperator.")
        a = float(alpha)
        dtype = np.result_type(v.dtype, self.op.dtype if self.op.dtype is not None else float)

        def mv(x):
            return np.asarray(x) - a*self.h*self.op.matvec(x)

        M = LinearOperator((self.n, self.n), matvec=mv, dtype=dtype)
        self.backend._stats["shifted_solves"] += 1
        x, info = gmres_compat(M, v, rtol=self.backend.options.tol, atol=0.0, restart=min(40, self.n))
        if info != 0:
            self.backend._stats["nonconverged_shifted_solves"] += 1
            if self.backend.fail_on_nonconvergence:
                raise KrylovConvergenceError(f"GMRES shifted solve failed with info={info}.")
        return np.real_if_close(x)


class KrylovBackend(Backend):
    """Matrix-free Arnoldi backend for phi-actions and phi-combinations.

    This backend is deliberately *not* branded KIOPS/phipm.  It uses a
    clean independent Arnoldi projection and a successive-projection convergence
    estimator.  Sparse matrices and scipy.sparse.linalg.LinearOperator are both
    accepted through ``aslinearoperator``.
    """

    name = "krylov"

    def __init__(
        self,
        *,
        tol: float = 1e-10,
        min_dim: int = 8,
        max_dim: int = 48,
        check_every: int = 4,
        breakdown_tol: float = 1e-14,
        reorthogonalize: bool = True,
        fail_on_nonconvergence: bool = True,
        fuse_sums: bool = True,
    ):
        self.options = KrylovOptions(
            tol=tol,
            min_dim=min_dim,
            max_dim=max_dim,
            check_every=check_every,
            breakdown_tol=breakdown_tol,
            reorthogonalize=reorthogonalize,
        )
        self.fail_on_nonconvergence = bool(fail_on_nonconvergence)
        self.fuse_sums = bool(fuse_sums)
        self.reset_stats()

    def reset_stats(self) -> None:
        self._stats = {
            "matvecs": 0,
            "krylov_projections": 0,
            "projection_evaluations": 0,
            "combination_actions": 0,
            "linear_combination_actions": 0,
            "fused_sum_actions": 0,
            "augmented_krylov_projections": 0,
            "single_phi_actions": 0,
            "phi_terms_requested": 0,
            "zero_actions": 0,
            "happy_breakdowns": 0,
            "nonconverged_actions": 0,
            "krylov_dim_sum": 0,
            "max_krylov_dim_used": 0,
            "last_error_estimate": None,
            "shifted_solves": 0,
            "nonconverged_shifted_solves": 0,
        }

    def stats(self) -> dict:
        out = dict(self._stats)
        nproj = out["krylov_projections"]
        out["mean_krylov_dim"] = (
            out["krylov_dim_sum"] / nproj if nproj else 0.0
        )
        out["tolerance"] = self.options.tol
        out["max_dim"] = self.options.max_dim
        out["fuse_sums"] = self.fuse_sums
        return out

    def bind(self, linear_operator, h: float):
        ctx = _KrylovContext(self, linear_operator, h)
        self._stats["max_operator_dimension"] = max(
            self._stats.get("max_operator_dimension", 0), ctx.n
        )
        return ctx
