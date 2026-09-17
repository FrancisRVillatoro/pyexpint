from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol
import numbers
import numpy as np


class BoundBackend(Protocol):
    def phi_action(self, k: int, scale: float, v: np.ndarray) -> np.ndarray: ...
    def phi_combination_action(self, terms, v: np.ndarray) -> np.ndarray: ...
    def shifted_solve_action(self, alpha: float, v: np.ndarray) -> np.ndarray: ...


class OperatorExpr:
    """Abstract analytic operator coefficient acting on a vector."""

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def __add__(self, other):
        return SumExpr.make(self, as_expr(other))

    def __radd__(self, other):
        return SumExpr.make(as_expr(other), self)

    def __sub__(self, other):
        return SumExpr.make(self, -as_expr(other))

    def __rsub__(self, other):
        return SumExpr.make(as_expr(other), -self)

    def __neg__(self):
        return ScaledExpr(-1.0, self)

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            return ScaledExpr(float(other), self)
        return ProductExpr(self, as_expr(other))

    def __rmul__(self, other):
        if isinstance(other, numbers.Number):
            return ScaledExpr(float(other), self)
        return ProductExpr(as_expr(other), self)

    def __matmul__(self, other):
        """Composition: (left @ right) v = left(right(v))."""
        return ProductExpr(self, as_expr(other))


@dataclass(frozen=True)
class PhiTerm:
    alpha: float
    k: int
    scale: float = 1.0

    def __post_init__(self):
        if self.k < 0:
            raise ValueError("phi index k must be nonnegative.")


@dataclass(frozen=True)
class PhiCombination(OperatorExpr):
    """Linear combination sum alpha * phi_k(scale*z)."""

    terms: tuple[PhiTerm, ...]

    def __post_init__(self):
        # Remove exact zero terms and canonicalize ordering without changing semantics.
        clean = tuple(t for t in self.terms if t.alpha != 0.0)
        object.__setattr__(self, "terms", clean)

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        if not self.terms:
            return np.zeros_like(v)
        # Backends with native combination support (e.g. Krylov) can build a
        # single projection/basis for all terms.  Reference backends may simply
        # expose phi_action and use the fallback below.
        combine = getattr(ctx, "phi_combination_action", None)
        if combine is not None:
            return np.real_if_close(combine(self.terms, v))
        out = np.zeros_like(v, dtype=np.result_type(v.dtype, np.complex128))
        for term in self.terms:
            out = out + term.alpha * ctx.phi_action(term.k, term.scale, v)
        return np.real_if_close(out)

    def __neg__(self):
        return PhiCombination(tuple(PhiTerm(-t.alpha, t.k, t.scale) for t in self.terms))

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            return PhiCombination(tuple(PhiTerm(float(other)*t.alpha, t.k, t.scale) for t in self.terms))
        return ProductExpr(self, as_expr(other))

    def __rmul__(self, other):
        if isinstance(other, numbers.Number):
            return self.__mul__(other)
        return ProductExpr(as_expr(other), self)

    @classmethod
    def single(cls, k: int, scale: float = 1.0, alpha: float = 1.0):
        return cls((PhiTerm(float(alpha), int(k), float(scale)),))


@dataclass(frozen=True)
class ZeroExpr(OperatorExpr):
    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        return np.zeros_like(v)


@dataclass(frozen=True)
class ScaledExpr(OperatorExpr):
    alpha: float
    expr: OperatorExpr

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        return self.alpha * self.expr.apply(ctx, v)


@dataclass(frozen=True)
class SumExpr(OperatorExpr):
    terms: tuple[OperatorExpr, ...]

    @staticmethod
    def make(*items: OperatorExpr):
        flat = []
        for x in items:
            if isinstance(x, ZeroExpr):
                continue
            if isinstance(x, SumExpr):
                flat.extend(x.terms)
            else:
                flat.append(x)
        if not flat:
            return ZERO
        if all(isinstance(x, PhiCombination) for x in flat):
            terms = []
            for x in flat:
                terms.extend(x.terms)
            return PhiCombination(tuple(terms))
        if len(flat) == 1:
            return flat[0]
        return SumExpr(tuple(flat))

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        out = np.zeros_like(v, dtype=np.result_type(v.dtype, np.complex128))
        for term in self.terms:
            out = out + term.apply(ctx, v)
        return np.real_if_close(out)


@dataclass(frozen=True)
class ResolventExpr(OperatorExpr):
    """Action of (I - alpha*h*L)^(-1).

    This is intentionally separate from the phi algebra.  It is needed only
    for the historical Crank--Nicolson comparator retained from EXPINT.
    """

    alpha: float

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        solve = getattr(ctx, "shifted_solve_action", None)
        if solve is None:
            raise NotImplementedError(
                "This backend does not support shifted linear solves required by ResolventExpr."
            )
        return np.real_if_close(solve(float(self.alpha), np.asarray(v)))


@dataclass(frozen=True)
class ProductExpr(OperatorExpr):
    left: OperatorExpr
    right: OperatorExpr

    def apply(self, ctx: BoundBackend, v: np.ndarray) -> np.ndarray:
        return self.left.apply(ctx, self.right.apply(ctx, v))


ZERO = ZeroExpr()

# Identity is phi_0(0*z) = I.
I = PhiCombination.single(k=0, scale=0.0)


def phi(k: int, scale: float = 1.0, alpha: float = 1.0) -> PhiCombination:
    return PhiCombination.single(k=k, scale=scale, alpha=alpha)


def resolvent(alpha: float) -> ResolventExpr:
    return ResolventExpr(float(alpha))


def as_expr(x) -> OperatorExpr:
    if isinstance(x, OperatorExpr):
        return x
    if isinstance(x, numbers.Number):
        if x == 0:
            return ZERO
        return float(x) * I
    raise TypeError(f"Cannot convert {type(x)!r} to OperatorExpr.")
