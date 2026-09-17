#!/usr/bin/env python3
"""
PyEXPINT Phase-0 symbolic verification for the 13 P0 legacy methods.

This is an independent mathematical specification/checker.  It does not parse,
translate, or execute EXPINT MATLAB source.  Coefficients are transcribed from
the published EXPINT documentation and the primary papers.

Checks implemented here:
  * exact stage/quadrature order conditions (2.7) of
    Ostermann--Thalhammer--Wright, BIT 46 (2006), for applicable EGLMs;
  * weak quadrature condition (3.15) at the highest order;
  * classical Runge--Kutta order conditions through order 4 in the L -> 0 limit;
  * explicit diagnostic of the documented-vs-legacy ETD2RK coefficient discrepancy.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional
import sympy as sp

# ---------------------------------------------------------------------------
# Formal phi symbols
# ---------------------------------------------------------------------------

F = {k: sp.Symbol(f"phi{k}") for k in range(0, 8)}       # phi_k(z)
H = {k: sp.Symbol(f"phi{k}_half") for k in range(0, 8)}  # phi_k(z/2)

def phi_symbol(k: int, c: sp.Rational):
    if c == 0:
        return sp.Rational(1, math.factorial(k))
    if c == 1:
        return F[k]
    if c == sp.Rational(1, 2):
        return H[k]
    return sp.Symbol(f"phi{k}_at_{c}")

f0, f1, f2, f3, f4, f5 = (F[k] for k in range(6))
h0, h1, h2, h3 = (H[k] for k in range(4))
ONE = sp.Integer(1)

@dataclass
class EGLMSpec:
    name: str
    c: List[sp.Rational]
    A: List[List[sp.Expr]]
    U: List[List[sp.Expr]]   # history coefficients; q-1 columns
    B: List[sp.Expr]         # solution output row
    V: List[sp.Expr]         # solution history coefficients; q-1 entries
    q: int
    expected_order: int
    note: str = ""

def _r(x):
    return sp.Rational(x)

# ---------------------------------------------------------------------------
# Published/documented EGLM specifications
# ---------------------------------------------------------------------------

METHODS = {}

METHODS["ABNorsett4"] = EGLMSpec(
    "ABNorsett4",
    c=[_r(0)],
    A=[[0]],
    U=[[0, 0, 0]],
    B=[f1 + sp.Rational(11,6)*f2 + 2*f3 + f4],
    V=[
        -3*f2 - 5*f3 - 3*f4,
        sp.Rational(3,2)*f2 + 4*f3 + 3*f4,
        -sp.Rational(1,3)*f2 - f3 - f4,
    ],
    q=4,
    expected_order=4,
    note="Four-step exponential Adams--Bashforth / EGLM414."
)

METHODS["PEC423"] = EGLMSpec(
    "PEC423",
    c=[_r(0), _r(1)],
    A=[
        [0, 0],
        [f1 + sp.Rational(3,2)*f2 + f3, 0],
    ],
    U=[
        [0, 0],
        [-2*f2 - 2*f3, sp.Rational(1,2)*f2 + f3],
    ],
    B=[
        f1 + sp.Rational(1,2)*f2 - 2*f3 - 3*f4,
        sp.Rational(1,3)*f2 + f3 + f4,
    ],
    V=[
        -f2 + f3 + 3*f4,
        sp.Rational(1,6)*f2 - f4,
    ],
    q=3,
    expected_order=4,
    note="Same mathematical scheme as EGLM423 in BIT 46 (2006)."
)

METHODS["PECEC433"] = EGLMSpec(
    "PECEC433",
    c=[_r(0), _r(1), _r(1)],
    A=[
        [0, 0, 0],
        [f1 + sp.Rational(3,2)*f2 + f3, 0, 0],
        [
            f1 + sp.Rational(1,2)*f2 - 2*f3 - 3*f4,
            sp.Rational(1,3)*f2 + f3 + f4,
            0,
        ],
    ],
    U=[
        [0, 0],
        [-2*f2 - 2*f3, sp.Rational(1,2)*f2 + f3],
        [-f2 + f3 + 3*f4, sp.Rational(1,6)*f2 - f4],
    ],
    B=[
        f1 + sp.Rational(1,2)*f2 - 2*f3 - 3*f4,
        0,
        sp.Rational(1,3)*f2 + f3 + f4,
    ],
    V=[
        -f2 + f3 + 3*f4,
        sp.Rational(1,6)*f2 - f4,
    ],
    q=3,
    expected_order=4,
    note="PEC423 corrector evaluated and applied a second time."
)

METHODS["EGLM332"] = EGLMSpec(
    "EGLM332",
    c=[_r(0), sp.Rational(1,2), _r(1)],
    A=[
        [0, 0, 0],
        [sp.Rational(1,2)*h1 + sp.Rational(1,4)*h2, 0, 0],
        [f1 - f2 - 4*f3, sp.Rational(4,3)*f2 + sp.Rational(8,3)*f3, 0],
    ],
    U=[
        [0],
        [-sp.Rational(1,4)*h2],
        [-sp.Rational(1,3)*f2 + sp.Rational(4,3)*f3],
    ],
    B=[
        f1 - 2*f2 - 2*f3 + 12*f4,
        sp.Rational(8,3)*f2 - 16*f4,
        -sp.Rational(1,2)*f2 + f3 + 6*f4,
    ],
    V=[-sp.Rational(1,6)*f2 + f3 - 2*f4],
    q=2,
    expected_order=3,
    note="EXPINT header says order 4, but order conditions give p=3."
)

METHODS["EGLM433"] = EGLMSpec(
    "EGLM433",
    c=[_r(0), sp.Rational(1,2), _r(1)],
    A=[
        [0, 0, 0],
        [
            sp.Rational(1,2)*h1 + sp.Rational(3,8)*h2 + sp.Rational(1,8)*h3,
            0, 0
        ],
        [
            f1 - sp.Rational(1,2)*f2 - 5*f3 - 6*f4,
            sp.Rational(16,15)*f2 + sp.Rational(16,5)*f3 + sp.Rational(16,5)*f4,
            0
        ],
    ],
    U=[
        [0, 0],
        [
            -sp.Rational(1,2)*h2 - sp.Rational(1,4)*h3,
            sp.Rational(1,8)*h2 + sp.Rational(1,8)*h3
        ],
        [
            -sp.Rational(2,3)*f2 + 2*f3 + 4*f4,
            sp.Rational(1,10)*f2 - sp.Rational(1,5)*f3 - sp.Rational(6,5)*f4
        ],
    ],
    B=[
        f1 - sp.Rational(3,2)*f2 - 4*f3 + 9*f4 + 24*f5,
        sp.Rational(32,15)*f2 + sp.Rational(32,15)*f3
        - sp.Rational(64,5)*f4 - sp.Rational(128,5)*f5,
        -sp.Rational(1,3)*f2 + sp.Rational(1,3)*f3 + 5*f4 + 8*f5,
    ],
    V=[
        -sp.Rational(1,3)*f2 + sp.Rational(5,3)*f3 - f4 - 8*f5,
        sp.Rational(1,30)*f2 - sp.Rational(2,15)*f3
        - sp.Rational(1,5)*f4 + sp.Rational(8,5)*f5,
    ],
    q=3,
    expected_order=4,
    note="Not the EGLM432 printed in BIT 2006; distinct EXPINT scheme."
)

GEN_A = [
    [0,0,0,0],
    [sp.Rational(1,2)*h1 + sp.Rational(3,8)*h2 + sp.Rational(1,8)*h3,0,0,0],
    [
        sp.Rational(1,2)*h1 + sp.Rational(3,8)*h2 + sp.Rational(1,8)*h3
        - sp.Rational(15,16),
        sp.Rational(1,2),0,0
    ],
    [f1 + sp.Rational(3,2)*f2 + f3 - sp.Rational(15,8)*h0, 0, h0, 0],
]
GEN_U = [
    [0,0],
    [
        -sp.Rational(1,2)*h2 - sp.Rational(1,4)*h3,
        sp.Rational(1,8)*h2 + sp.Rational(1,8)*h3,
    ],
    [
        -sp.Rational(1,2)*h2 - sp.Rational(1,4)*h3 + sp.Rational(5,8),
        sp.Rational(1,8)*h2 + sp.Rational(1,8)*h3 - sp.Rational(3,16),
    ],
    [
        -2*f2 - 2*f3 + sp.Rational(5,4)*h0,
        sp.Rational(1,2)*f2 + f3 - sp.Rational(3,8)*h0,
    ],
]

METHODS["GenLawson43"] = EGLMSpec(
    "GenLawson43",
    c=[_r(0), sp.Rational(1,2), sp.Rational(1,2), _r(1)],
    A=GEN_A,
    U=GEN_U,
    B=[
        f1 + sp.Rational(3,2)*f2 + f3 - sp.Rational(5,4)*h0 - sp.Rational(1,2),
        sp.Rational(1,3)*h0,
        sp.Rational(1,3)*h0,
        sp.Rational(1,6),
    ],
    V=[
        -2*f2 - 2*f3 + sp.Rational(5,6)*h0 + sp.Rational(1,2),
        sp.Rational(1,2)*f2 + f3 - sp.Rational(1,4)*h0 - sp.Rational(1,6),
    ],
    q=3,
    expected_order=4,
    note="Strong Q=P=3 and weak quadrature order 4."
)

METHODS["ModGenLawson43"] = EGLMSpec(
    "ModGenLawson43",
    c=[_r(0), sp.Rational(1,2), sp.Rational(1,2), _r(1)],
    A=GEN_A,
    U=GEN_U,
    B=[
        f1 + sp.Rational(1,2)*f2 - 2*f3 - 3*f4 - sp.Rational(5,8)*h0,
        sp.Rational(1,3)*h0,
        sp.Rational(1,3)*h0,
        sp.Rational(1,3)*f2 + f3 + f4 - sp.Rational(5,24)*h0,
    ],
    V=[
        -f2 + f3 + 3*f4 + sp.Rational(5,24)*h0,
        sp.Rational(1,6)*f2 - f4 - sp.Rational(1,24)*h0,
    ],
    q=3,
    expected_order=4,
    note="Same internal stages as GenLawson43; output modification raises strong P to 4."
)

# ---------------------------------------------------------------------------
# BIT (2006) order-condition checker
# ---------------------------------------------------------------------------

def stage_residual(spec: EGLMSpec, i: int, ell: int):
    ci = spec.c[i]
    lhs = ci**ell * phi_symbol(ell, ci)
    rhs = sum(
        spec.c[j]**(ell-1) / sp.factorial(ell-1) * spec.A[i][j]
        for j in range(i)
    )
    rhs += sum(
        sp.Rational((-k)**(ell-1), sp.factorial(ell-1)) * spec.U[i][k-1]
        for k in range(1, spec.q)
    )
    return sp.expand(lhs-rhs)

def quadrature_residual(spec: EGLMSpec, ell: int):
    lhs = F[ell]
    rhs = sum(
        spec.c[i]**(ell-1) / sp.factorial(ell-1) * spec.B[i]
        for i in range(len(spec.c))
    )
    rhs += sum(
        sp.Rational((-k)**(ell-1), sp.factorial(ell-1)) * spec.V[k-1]
        for k in range(1, spec.q)
    )
    return sp.expand(lhs-rhs)

def stage_order(spec: EGLMSpec, max_order=7):
    # Stage 1 is exactly y_n and imposes no effective limitation.
    qvals = []
    for i in range(1, len(spec.c)):
        q_i = 0
        for ell in range(1, max_order+1):
            if stage_residual(spec, i, ell) == 0:
                q_i = ell
            else:
                break
        qvals.append(q_i)
    return min(qvals) if qvals else math.inf

def quadrature_order(spec: EGLMSpec, max_order=7):
    p = 0
    for ell in range(1, max_order+1):
        if quadrature_residual(spec, ell) == 0:
            p = ell
        else:
            break
    return p

ZERO_SUBS = {F[k]: sp.Rational(1, math.factorial(k)) for k in F}
ZERO_SUBS.update({H[k]: sp.Rational(1, math.factorial(k)) for k in H})

def weak_quadrature_holds(spec: EGLMSpec, P: int):
    # (3.15): strong through P-1; P-th residual only required to vanish at z=0.
    if any(quadrature_residual(spec, ell) != 0 for ell in range(1, P)):
        return False
    return sp.simplify(quadrature_residual(spec, P).subs(ZERO_SUBS)) == 0

# ---------------------------------------------------------------------------
# Classical RK L->0 checks for one-step P0 methods
# ---------------------------------------------------------------------------

def rk_order(A, b, c):
    A = sp.Matrix(A)
    b = sp.Matrix(b)
    c = sp.Matrix(c)
    one = sp.ones(len(c),1)
    C = sp.diag(*list(c))
    c2 = sp.Matrix([x*x for x in c])
    c3 = sp.Matrix([x*x*x for x in c])

    cond1 = (b.T*one)[0] == 1
    cond2 = (b.T*c)[0] == sp.Rational(1,2)
    cond3 = (
        (b.T*c2)[0] == sp.Rational(1,3)
        and (b.T*A*c)[0] == sp.Rational(1,6)
    )
    cond4 = (
        (b.T*c3)[0] == sp.Rational(1,4)
        and (b.T*A*c2)[0] == sp.Rational(1,12)
        and (b.T*C*A*c)[0] == sp.Rational(1,8)
        and (b.T*A*A*c)[0] == sp.Rational(1,24)
    )
    if not cond1: return 0
    if not cond2: return 1
    if not cond3: return 2
    if not cond4: return 3
    return 4

RK_LIMITS = {
    "LawsonEuler": (
        [[0]], [1], [0]
    ),
    "NorsettEuler": (
        [[0]], [1], [0]
    ),
    # Published ETD2RK / EXPINT README:
    "ETD2RK_documented": (
        [[0,0],[1,0]], [sp.Rational(1,2),sp.Rational(1,2)], [0,1]
    ),
    # Coefficient appearing in the 2005 MATLAB file supplied by the user:
    "ETD2RK_legacy_matlab": (
        [[0,0],[1,0]], [0,sp.Rational(1,2)], [0,1]
    ),
    "ETD4RK": (
        [[0,0,0,0],
         [sp.Rational(1,2),0,0,0],
         [0,sp.Rational(1,2),0,0],
         [0,0,1,0]],
        [sp.Rational(1,6),sp.Rational(1,3),sp.Rational(1,3),sp.Rational(1,6)],
        [0,sp.Rational(1,2),sp.Rational(1,2),1],
    ),
    "Krogstad": (
        [[0,0,0,0],
         [sp.Rational(1,2),0,0,0],
         [0,sp.Rational(1,2),0,0],
         [0,0,1,0]],
        [sp.Rational(1,6),sp.Rational(1,3),sp.Rational(1,3),sp.Rational(1,6)],
        [0,sp.Rational(1,2),sp.Rational(1,2),1],
    ),
    "HochOst4": (
        [[0,0,0,0,0],
         [sp.Rational(1,2),0,0,0,0],
         [0,sp.Rational(1,2),0,0,0],
         [0,sp.Rational(1,2),sp.Rational(1,2),0,0],
         [sp.Rational(1,4),sp.Rational(1,8),sp.Rational(1,8),0,0]],
        [sp.Rational(1,6),0,0,sp.Rational(1,6),sp.Rational(2,3)],
        [0,sp.Rational(1,2),sp.Rational(1,2),1,sp.Rational(1,2)],
    ),
}

def main():
    print("=== EGLM exact order-condition audit ===")
    for name, spec in METHODS.items():
        Q = stage_order(spec)
        P = quadrature_order(spec)
        weak_next = weak_quadrature_holds(spec, P+1)
        if Q is math.inf:
            theorem_order = P
        else:
            theorem_order = min(P, Q+1)
            if weak_quadrature_holds(spec, spec.expected_order) and Q == spec.expected_order-1:
                theorem_order = max(theorem_order, spec.expected_order)
        print(f"{name:18s} Q={Q!s:>3s}  P={P}  weak(P+1)={weak_next}  "
              f"certified p={theorem_order}  expected={spec.expected_order}")
        assert theorem_order == spec.expected_order, name

    print("\n=== L -> 0 classical RK audit ===")
    for name, (A,b,c) in RK_LIMITS.items():
        p = rk_order(A,b,c)
        print(f"{name:24s} classical order = {p}")

    assert rk_order(*RK_LIMITS["ETD2RK_documented"]) == 2
    assert rk_order(*RK_LIMITS["ETD2RK_legacy_matlab"]) == 0
    assert rk_order(*RK_LIMITS["ETD4RK"]) == 4
    assert rk_order(*RK_LIMITS["Krogstad"]) == 4
    assert rk_order(*RK_LIMITS["HochOst4"]) == 4

    print("\nAll Phase-0 assertions passed.")
    print("The legacy ETD2RK MATLAB coefficient fails even first-order consistency at L=0;")
    print("the published/README coefficient is the one that must be used in PyEXPINT.")

if __name__ == "__main__":
    main()
