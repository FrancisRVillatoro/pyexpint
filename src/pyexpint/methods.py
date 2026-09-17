from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import factorial
from typing import Optional

import numpy as np

from .expressions import OperatorExpr, ZERO, I, phi, resolvent


@dataclass(frozen=True)
class MethodSpec:
    """Explicit exponential general-linear method specification.

    With external state ``X_n`` and ``G_j=h*N(t_n+c_j*h,Y_j)``, the engine uses

        Y_i       = sum_j U_ij(hL) X_n[j] + sum_{j<i} A_ij(hL) G_j,
        X_{n+1,i} = sum_j V_ij(hL) X_n[j] + sum_j B_ij(hL) G_j.

    The first external component is the physical solution.  Historical multistep
    methods use auxiliary components ``h*N`` from previous steps.
    """

    name: str
    family: str
    c: tuple[float, ...]
    U: tuple[tuple[OperatorExpr, ...], ...]
    A: tuple[tuple[OperatorExpr, ...], ...]
    V: tuple[tuple[OperatorExpr, ...], ...]
    B: tuple[tuple[OperatorExpr, ...], ...]
    classical_order: int
    stiff_order: Optional[int]
    weak_stiff_order: Optional[int] = None
    stage_order: Optional[int] = None
    quadrature_order: Optional[int] = None
    weak_quadrature_order: Optional[int] = None
    external_layout: str = "solution_only"
    nonlinear_evals_per_step: Optional[int] = None
    references: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    legacy_file: Optional[str] = None
    provenance_status: str = "published"
    historical_comparator: bool = False

    @property
    def stages(self) -> int:
        return len(self.c)

    @property
    def outputs(self) -> int:
        return len(self.V)

    @property
    def history_length(self) -> int:
        return self.outputs - 1 if self.external_layout == "nonlinear_history" else 0

    def validate(self) -> None:
        s, r = self.stages, self.outputs
        if len(self.U) != s or len(self.A) != s or len(self.B) != r:
            raise ValueError(f"{self.name}: inconsistent U/A/B row dimensions.")
        if any(len(row) != r for row in self.U):
            raise ValueError(f"{self.name}: U must have shape s x r.")
        if any(len(row) != s for row in self.A):
            raise ValueError(f"{self.name}: A must have shape s x s.")
        if any(len(row) != r for row in self.V):
            raise ValueError(f"{self.name}: V must have shape r x r.")
        if any(len(row) != s for row in self.B):
            raise ValueError(f"{self.name}: B must have shape r x s.")
        for i in range(s):
            for j in range(i, s):
                if self.A[i][j] != ZERO:
                    raise ValueError(f"{self.name}: A[{i},{j}] violates explicit stage ordering.")
        if self.c[0] != 0.0:
            raise ValueError(f"{self.name}: first stage must be at c=0.")
        if r > 1 and self.external_layout != "nonlinear_history":
            raise ValueError(f"{self.name}: r>1 requires nonlinear_history layout.")


def _M(rows):
    return tuple(tuple(row) for row in rows)


def _make(**kwargs):
    m = MethodSpec(**kwargs)
    m.validate()
    return m


def _zeros(rows: int, cols: int):
    return [[ZERO for _ in range(cols)] for _ in range(rows)]


def _history_output(first_v, first_b, r: int, s: int):
    """Add canonical h*N history shifting below the physical output row."""
    V = _zeros(r, r)
    B = _zeros(r, s)
    V[0] = list(first_v)
    B[0] = list(first_b)
    if r > 1:
        B[1][0] = I                 # X_new[1] = h*N(y_n)
        for row in range(2, r):
            V[row][row - 1] = I    # shift older nonlinear histories
    return _M(V), _M(B)


# ---------------------------------------------------------------------------
# Polynomial tools used to derive method families from published constructions.
# They use exact rational arithmetic; only the final operator coefficients are
# converted to floating scalars multiplying analytic phi expressions.
# ---------------------------------------------------------------------------

def _poly_mul(a, b):
    out = [Fraction(0) for _ in range(len(a) + len(b) - 1)]
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def _lagrange_basis(nodes: list[Fraction], j: int):
    p = [Fraction(1)]
    den = Fraction(1)
    xj = nodes[j]
    for m, xm in enumerate(nodes):
        if m == j:
            continue
        p = _poly_mul(p, [-xm, Fraction(1)])
        den *= xj - xm
    return [x / den for x in p]


def _poly_value(poly, x: Fraction) -> Fraction:
    out = Fraction(0)
    power = Fraction(1)
    for coeff in poly:
        out += coeff * power
        power *= x
    return out


def _ordinary_integral(poly, a=Fraction(0), b=Fraction(1)) -> Fraction:
    out = Fraction(0)
    for m, coeff in enumerate(poly):
        out += coeff * (b ** (m + 1) - a ** (m + 1)) / Fraction(m + 1)
    return out


def _phi_integral(poly, c: Fraction) -> OperatorExpr:
    """Integral_0^c exp((c-s)z) p(s) ds as a phi combination."""
    out: OperatorExpr = ZERO
    for m, coeff in enumerate(poly):
        if coeff:
            alpha = coeff * factorial(m) * c ** (m + 1)
            out = out + float(alpha) * phi(m + 1, float(c))
    return out


# Common analytic operator functions.
E = phi(0, 1.0)
E2 = phi(0, 0.5)
P1, P2, P3, P4, P5, P6, P7 = [phi(k, 1.0) for k in range(1, 8)]
H1, H2, H3, H4, H5 = [phi(k, 0.5) for k in range(1, 6)]


# ---------------------------------------------------------------------------
# Lawson families
# ---------------------------------------------------------------------------

def _lawson_rk(name, Aclass, bclass, c, order, *, legacy_file, reference):
    s = len(c)
    U = _zeros(s, 1)
    A = _zeros(s, s)
    for i, ci in enumerate(c):
        U[i][0] = phi(0, ci)
        for j in range(i):
            if Aclass[i][j] != 0:
                A[i][j] = float(Aclass[i][j]) * phi(0, ci - c[j])
    B = [[float(bclass[j]) * phi(0, 1.0 - c[j]) for j in range(s)]]
    return _make(
        name=name, family="Lawson / integrating factor Runge-Kutta",
        c=tuple(c), U=_M(U), A=_M(A), V=_M([[E]]), B=_M(B),
        classical_order=order, stiff_order=1,
        external_layout="solution_only", nonlinear_evals_per_step=s,
        references=(reference, "EXPINT published documentation"),
        legacy_file=legacy_file,
    )


LAWSON_EULER = _lawson_rk(
    "LawsonEuler", [[0]], [1], [0.0], 1,
    legacy_file="lawsoneuler.m", reference="Lawson (1967)",
)

LAWSON2A = _lawson_rk(
    "Lawson2a",
    [[0, 0], [Fraction(1, 2), 0]],
    [0, 1], [0.0, 0.5], 2,
    legacy_file="lawson2a.m", reference="Classical midpoint rule after Lawson transform",
)

LAWSON2B = _lawson_rk(
    "Lawson2b",
    [[0, 0], [1, 0]],
    [Fraction(1, 2), Fraction(1, 2)], [0.0, 1.0], 2,
    legacy_file="lawson2b.m", reference="Explicit trapezoidal/Heun rule after Lawson transform",
)

LAWSON4 = _lawson_rk(
    "Lawson4",
    [[0,0,0,0], [Fraction(1,2),0,0,0], [0,Fraction(1,2),0,0], [0,0,1,0]],
    [Fraction(1,6),Fraction(1,3),Fraction(1,3),Fraction(1,6)],
    [0.0,0.5,0.5,1.0], 4,
    legacy_file="lawson4.m", reference="Classical RK4 after Lawson transform",
)


def _ab_lawson(p: int):
    nodes = [Fraction(-j) for j in range(p)]
    betas = [_ordinary_integral(_lagrange_basis(nodes, j)) for j in range(p)]
    r = p
    U = [[I] + [ZERO]*(r-1)]
    A = [[ZERO]]
    first_v = [E] + [float(betas[j]) * phi(0, float(j + 1)) for j in range(1, p)]
    first_b = [float(betas[0]) * E]
    V, B = _history_output(first_v, first_b, r, 1)
    return _make(
        name=f"ABLawson{p}", family="Adams-Bashforth-Lawson",
        c=(0.0,), U=_M(U), A=_M(A), V=V, B=B,
        classical_order=p, stiff_order=1,
        external_layout="nonlinear_history", nonlinear_evals_per_step=1,
        references=("Classical Adams-Bashforth after Lawson transform", "EXPINT published documentation"),
        notes=("Efficient one-stage mathematical form; legacy EXPINT used a redundant predictor stage.",),
        legacy_file=f"ablawson{p}.m",
    )


ABLAWSON2, ABLAWSON3, ABLAWSON4 = (_ab_lawson(p) for p in (2,3,4))


# ---------------------------------------------------------------------------
# Exponential Adams / PEC / PECEC families from interpolation and OTW (2006).
# ---------------------------------------------------------------------------

def _ab_norsett(p: int):
    nodes = [Fraction(-j) for j in range(p)]
    weights = [_phi_integral(_lagrange_basis(nodes, j), Fraction(1)) for j in range(p)]
    r = p
    U = [[I] + [ZERO]*(r-1)]
    first_v = [E] + weights[1:]
    V, B = _history_output(first_v, [weights[0]], r, 1)
    return _make(
        name=f"ABNorsett{p}", family="Exponential Adams-Bashforth",
        c=(0.0,), U=_M(U), A=_M([[ZERO]]), V=V, B=B,
        classical_order=p, stiff_order=p, quadrature_order=p,
        external_layout="nonlinear_history", nonlinear_evals_per_step=1,
        references=("Ostermann, Thalhammer & Wright (2006), exponential multistep subclass",),
        notes=("Coefficients generated from interpolation in the variation-of-constants formula.",),
        legacy_file=f"abnorsett{p}.m",
    )


NORSETT_EULER = _make(
    name="NorsettEuler", family="Exponential Euler", c=(0.0,),
    U=_M([[I]]), A=_M([[ZERO]]), V=_M([[E]]), B=_M([[P1]]),
    classical_order=1, stiff_order=1, quadrature_order=1,
    external_layout="solution_only", nonlinear_evals_per_step=1,
    references=("Variation-of-constants exponential Euler; EXPINT documentation",),
    legacy_file="norsetteuler.m",
)
ABNORSETT2, ABNORSETT3, ABNORSETT4 = (_ab_norsett(p) for p in (2,3,4))


def _pec_family(p: int, *, twice: bool):
    q = p - 1
    pred_nodes = [Fraction(-j) for j in range(q)]
    pred = [_phi_integral(_lagrange_basis(pred_nodes, j), Fraction(1)) for j in range(q)]

    corr_nodes = [Fraction(1)] + [Fraction(-j) for j in range(q)]
    corr = [_phi_integral(_lagrange_basis(corr_nodes, j), Fraction(1)) for j in range(p)]
    w_future = corr[0]
    w_now = corr[1]
    w_hist = corr[2:]

    r = q
    s = 3 if twice else 2
    U = _zeros(s, r)
    A = _zeros(s, s)
    U[0][0] = I
    U[1][0] = E
    A[1][0] = pred[0]
    for j in range(1, q):
        U[1][j] = pred[j]
    if twice:
        U[2][0] = E
        A[2][0] = w_now
        A[2][1] = w_future
        for j in range(1, q):
            U[2][j] = w_hist[j-1]

    first_v = [E] + list(w_hist)
    first_b = [w_now, ZERO, w_future] if twice else [w_now, w_future]
    V, B = _history_output(first_v, first_b, r, s)
    prefix = "PECEC" if twice else "PEC"
    name = f"{prefix}{p}{s}{q}"
    return _make(
        name=name, family="Exponential GLM / " + prefix,
        c=tuple([0.0,1.0] + ([1.0] if twice else [])),
        U=_M(U), A=_M(A), V=V, B=B,
        classical_order=p, stiff_order=p, stage_order=p-1, quadrature_order=p,
        external_layout="nonlinear_history", nonlinear_evals_per_step=s,
        references=("Ostermann, Thalhammer & Wright (2006), two-stage family and order conditions",),
        notes=("Generated algebraically from exponential Adams predictor/corrector interpolation.",),
        legacy_file=name.lower()+".m",
    )


PEC322, PEC423, PEC524, PEC625, PEC726 = (_pec_family(p, twice=False) for p in range(3,8))
PECEC332, PECEC433, PECEC534, PECEC635, PECEC736 = (_pec_family(p, twice=True) for p in range(3,8))

# Audit notes for the two README prose errors discovered in Phase 0.
PEC423 = MethodSpec(**{**PEC423.__dict__, "notes": PEC423.notes + ("README prose says stiff order 3; OTW conditions certify order 4.",)})
PECEC433 = MethodSpec(**{**PECEC433.__dict__, "notes": PECEC433.notes + ("README prose says stiff order 3; independent OTW audit certifies order 4.",)})


# ---------------------------------------------------------------------------
# Two standalone EXPINT EGLMs already audited in Phase 0.
# ---------------------------------------------------------------------------
EGLM332 = _make(
    name="EGLM332", family="Exponential GLM", c=(0.0,0.5,1.0),
    U=_M([
        [I,ZERO],
        [E2,-0.25*H2],
        [E,-(1/3)*P2+(4/3)*P3],
    ]),
    A=_M([
        [ZERO,ZERO,ZERO],
        [0.5*H1+0.25*H2,ZERO,ZERO],
        [P1-P2-4*P3,(4/3)*P2+(8/3)*P3,ZERO],
    ]),
    V=_M([
        [E,-(1/6)*P2+P3-2*P4],
        [ZERO,ZERO],
    ]),
    B=_M([
        [P1-2*P2-2*P3+12*P4,(8/3)*P2-16*P4,-0.5*P2+P3+6*P4],
        [I,ZERO,ZERO],
    ]),
    classical_order=3, stiff_order=3, stage_order=2, quadrature_order=4,
    external_layout="nonlinear_history", nonlinear_evals_per_step=3,
    references=("EXPINT published mathematical documentation; OTW (2006) order conditions",),
    notes=("Audited Q=2, P=4 => p=3; legacy MATLAB header incorrectly says order 4, s=2, r=3.",),
    legacy_file="eglm332.m", provenance_status="EXPINT-documentation",
)

EGLM433 = _make(
    name="EGLM433", family="Exponential GLM", c=(0.0,0.5,1.0),
    U=_M([
        [I,ZERO,ZERO],
        [E2,-0.5*H2-0.25*H3,0.125*H2+0.125*H3],
        [E,-(2/3)*P2+2*P3+4*P4,0.1*P2-0.2*P3-1.2*P4],
    ]),
    A=_M([
        [ZERO,ZERO,ZERO],
        [0.5*H1+(3/8)*H2+(1/8)*H3,ZERO,ZERO],
        [P1-0.5*P2-5*P3-6*P4,(16/15)*P2+(16/5)*P3+(16/5)*P4,ZERO],
    ]),
    V=_M([
        [E,-(1/3)*P2+(5/3)*P3-P4-8*P5,(1/30)*P2-(2/15)*P3-(1/5)*P4+(8/5)*P5],
        [ZERO,ZERO,ZERO],
        [ZERO,I,ZERO],
    ]),
    B=_M([
        [P1-1.5*P2-4*P3+9*P4+24*P5,(32/15)*P2+(32/15)*P3-(64/5)*P4-(128/5)*P5,-(1/3)*P2+(1/3)*P3+5*P4+8*P5],
        [I,ZERO,ZERO],
        [ZERO,ZERO,ZERO],
    ]),
    classical_order=4, stiff_order=4, stage_order=3, quadrature_order=5,
    external_layout="nonlinear_history", nonlinear_evals_per_step=3,
    references=("EXPINT mathematical specification; OTW (2006) order conditions",),
    notes=("Distinct from BIT's EGLM432; independent audit gives Q=3, P=5 => p=4.",),
    legacy_file="eglm433.m", provenance_status="EXPINT-documentation",
)


# ---------------------------------------------------------------------------
# Exponential Runge-Kutta and related one-step methods.
# ---------------------------------------------------------------------------
ETD2RK = _make(
    name="ETD2RK", family="Exponential Runge-Kutta", c=(0.0,1.0),
    U=_M([[I],[E]]), A=_M([[ZERO,ZERO],[P1,ZERO]]),
    V=_M([[E]]), B=_M([[P1-P2,P2]]),
    classical_order=2, stiff_order=2, stage_order=1, quadrature_order=2,
    external_layout="solution_only", nonlinear_evals_per_step=2,
    references=("Cox & Matthews (2002), Eq. (22)",),
    notes=("Published b1=phi1-phi2; supplied legacy MATLAB contains inconsistent phi1-2phi2 typo.",),
    legacy_file="etd2rk.m",
)

ETD3RK = _make(
    name="ETD3RK", family="Exponential Runge-Kutta", c=(0.0,0.5,1.0),
    U=_M([[I],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO],[-P1,2*P1,ZERO]]),
    V=_M([[E]]), B=_M([[P1-3*P2+4*P3,4*P2-8*P3,-P2+4*P3]]),
    classical_order=3, stiff_order=3,
    external_layout="solution_only", nonlinear_evals_per_step=3,
    references=("Friedli (1978); Cox & Matthews (2002), Eqs. (23)-(25)",),
    legacy_file="etd3rk.m",
)

EHLE_LAWSON = _make(
    name="EhleLawson", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO,ZERO],[ZERO,0.5*H1,ZERO,ZERO],[ZERO,ZERO,P1,ZERO]]),
    V=_M([[E]]),
    B=_M([[P1-3*P2+P3,2*P2-P3,2*P2-P3,-P2+P3]]),
    classical_order=2, stiff_order=2,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Ehle & Lawson (1975); EXPINT documentation",),
    legacy_file="ehlelawson.m",
)

CM_A41 = 0.5 * (H1 @ (E2 - I))
ETD4RK = _make(
    name="ETD4RK", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO,ZERO],[ZERO,0.5*H1,ZERO,ZERO],[CM_A41,ZERO,H1,ZERO]]),
    V=_M([[E]]),
    B=_M([[P1-3*P2+4*P3,2*P2-4*P3,2*P2-4*P3,-P2+4*P3]]),
    classical_order=4, stiff_order=2, stage_order=1, quadrature_order=4,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Cox & Matthews (2002), Eqs. (26)-(29)",),
    legacy_file="etd4rk.m",
)

KROGSTAD = _make(
    name="Krogstad", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO,ZERO],[0.5*H1-H2,H2,ZERO,ZERO],[P1-2*P2,ZERO,2*P2,ZERO]]),
    V=_M([[E]]), B=_M([[P1-3*P2+4*P3,2*P2-4*P3,2*P2-4*P3,-P2+4*P3]]),
    classical_order=4, stiff_order=3, stage_order=1, quadrature_order=4,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Krogstad (2005), Eq. (51), ETDRK4-B",), legacy_file="krogstad.m",
)

STREHMEL_WEINER = _make(
    name="StrehmelWeiner", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([
        [ZERO,ZERO,ZERO,ZERO], [0.5*H1,ZERO,ZERO,ZERO],
        [0.5*H1-0.5*H2,0.5*H2,ZERO,ZERO],
        [P1-2*P2,-2*P2,4*P2,ZERO],
    ]),
    V=_M([[E]]), B=_M([[P1-3*P2+4*P3,ZERO,4*P2-8*P3,-P2+4*P3]]),
    classical_order=4, stiff_order=3,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Strehmel & Weiner (1992), Example 4.5.5; EXPINT documentation",),
    legacy_file="strehmelweiner.m",
)

FRIEDLI = _make(
    name="Friedli", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([
        [ZERO,ZERO,ZERO,ZERO], [0.5*H1,ZERO,ZERO,ZERO],
        [0.5*H1-0.5*H2,0.5*H2,ZERO,ZERO],
        [P1-2*P2,-(26/25)*P1+(2/25)*P2,(26/25)*P1+(48/25)*P2,ZERO],
    ]),
    V=_M([[E]]), B=_M([[P1-3*P2+4*P3,ZERO,4*P2-8*P3,-P2+4*P3]]),
    classical_order=4, stiff_order=3,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Friedli (1978), Section 5; EXPINT documentation",), legacy_file="friedli.m",
)

A52 = 0.5*H2 - P3 + 0.25*P2 - 0.5*H3
A54 = 0.25*H2 - A52
A51 = 0.5*H1 - 2*A52 - A54
HOCHOST4 = _make(
    name="HochOst4", family="Exponential Runge-Kutta", c=(0.0,0.5,0.5,1.0,0.5),
    U=_M([[I],[E2],[E2],[E],[E2]]),
    A=_M([
        [ZERO,ZERO,ZERO,ZERO,ZERO], [0.5*H1,ZERO,ZERO,ZERO,ZERO],
        [0.5*H1-H2,H2,ZERO,ZERO,ZERO], [P1-2*P2,P2,P2,ZERO,ZERO],
        [A51,A52,A52,A54,ZERO],
    ]),
    V=_M([[E]]), B=_M([[P1-3*P2+4*P3,ZERO,ZERO,-P2+4*P3,4*P2-8*P3]]),
    classical_order=4, stiff_order=4, stage_order=1, quadrature_order=4,
    external_layout="solution_only", nonlinear_evals_per_step=5,
    references=("Hochbruck & Ostermann (2005), Section 5",), legacy_file="hochost4.m",
)

# Fehlberg-based fifth-order exponential method as printed in the public EXPINT
# documentation.  phihat2 denotes phi_2(3z/5).  The documented stage node is
# c4=3/4; a scalar-only exp(3z/5) line in the legacy .m is treated as a bug.
PHI2_35 = phi(2, 3/5)
ETD5_A = _zeros(6,6)
ETD5_A[1][0] = -(2/3)*P2 + (10/9)*PHI2_35
ETD5_A[2][0] = (569/11544)*P2 + (1355/11544)*PHI2_35
ETD5_A[2][1] = -(831/3848)*P2 + (2755/3848)*PHI2_35
ETD5_A[3][0] = -(77157/61568)*P2 + (143535/61568)*PHI2_35
ETD5_A[3][1] = (587979/61568)*P2 - (821745/61568)*PHI2_35
ETD5_A[3][2] = -(405/64)*P2 + (675/64)*PHI2_35
ETD5_A[4][0] = (655263/7696)*P2 - (2031205/23088)*PHI2_35
ETD5_A[4][1] = -(1148769/7696)*P2 + (1252665/7696)*PHI2_35
ETD5_A[4][2] = (1593/40)*P2 - (405/8)*PHI2_35
ETD5_A[4][3] = (144/5)*P2 - (80/3)*PHI2_35
ETD5_A[5][0] = -(2212835/277056)*P2 + (6888625/831168)*PHI2_35
ETD5_A[5][1] = (477285/30784)*P2 - (496525/30784)*PHI2_35
ETD5_A[5][2] = -(39/16)*P2 + (65/16)*PHI2_35
ETD5_A[5][3] = -(4/9)*P2 + (20/27)*PHI2_35
ETD5_A[5][4] = -(185/96)*P2 + (575/288)*PHI2_35
ETD5RKF = _make(
    name="ETD5RKF", family="Exponential Runge-Kutta (nonstiff order 5)",
    c=(0.0,2/9,1/3,3/4,1.0,5/6),
    U=_M([[phi(0,c)] for c in (0.0,2/9,1/3,3/4,1.0,5/6)]), A=_M(ETD5_A),
    V=_M([[E]]),
    B=_M([[
        (47/150)*P1-(188/75)*P2+(94/15)*P3,
        ZERO,
        -(43/25)*P1+(132/5)*P2-66*P3,
        (4124/75)*P1-(6152/15)*P2+(2704/3)*P3,
        (189/10)*P1-(662/5)*P2+284*P3,
        -(1787/25)*P1+(12966/25)*P2-(5628/5)*P3,
    ]]),
    classical_order=5, stiff_order=None,
    external_layout="solution_only", nonlinear_evals_per_step=6,
    references=("Berland, Owren & Skaflestad, B-series/order conditions; EXPINT documentation",),
    notes=("Historical nonstiff fifth-order method; EXPINT documentation notes a poor error constant.",
           "PyEXPINT uses documented c4=3/4; legacy scalar MATLAB branch used exp(3z/5), inconsistent with its c-vector and matrix/vector branches."),
    legacy_file="etd5rkf.m", provenance_status="EXPINT-documentation",
)


# ---------------------------------------------------------------------------
# Affine Lie-group-related methods, represented in the same semilinear EGLM form.
# ---------------------------------------------------------------------------
RKMK2E = _make(
    name="RKMK2e", family="Affine Lie-group", c=(0.0,1.0),
    U=_M([[I],[E]]), A=_M([[ZERO,ZERO],[P1,ZERO]]), V=_M([[E]]),
    B=_M([[0.5*P1,0.5*P1]]), classical_order=2, stiff_order=1, weak_stiff_order=2,
    external_layout="solution_only", nonlinear_evals_per_step=2,
    references=("Munthe-Kaas (1999), affine action; PASSA literature; EXPINT documentation",),
    notes=("Strong exponential-RK order-two moment fails; weak z=0 condition holds, and HO-type tests show conditional order about 2. README labels stiff order 1; a legacy source comment says 2."),
    legacy_file="rkmk2e.m",
)

P1_13 = phi(1,1/3); P1_23 = phi(1,2/3); P2_23 = phi(2,2/3)
ETD2CF3 = _make(
    name="ETD2CF3", family="Affine Lie-group / ETD", c=(0.0,1/3,2/3),
    U=_M([[I],[phi(0,1/3)],[phi(0,2/3)]]),
    A=_M([[ZERO,ZERO,ZERO],[(1/3)*P1_13,ZERO,ZERO],[(2/3)*P1_23-(4/3)*P2_23,(4/3)*P2_23,ZERO]]),
    V=_M([[E]]), B=_M([[P1-(9/2)*P2+9*P3,6*P2-18*P3,-1.5*P2+9*P3]]),
    classical_order=3, stiff_order=3,
    external_layout="solution_only", nonlinear_evals_per_step=3,
    references=("Hochbruck & Ostermann ETD construction; Celledoni, Marthinsen & Owren commutator-free lineage; EXPINT documentation",),
    notes=("A21 uses phi1(z/3), as required by the documented c2=1/3 tableau. The legacy .m evaluates phi1(z/2), which violates the stage consistency identity and is treated as a bug."),
    legacy_file="etd2cf3.m",
)

CF_A41 = 0.5 * (H1 @ (E2 - I))
CFREE4 = _make(
    name="Cfree4", family="Affine Lie-group / commutator-free", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO,ZERO],[ZERO,0.5*H1,ZERO,ZERO],[CF_A41,ZERO,H1,ZERO]]),
    V=_M([[E]]), B=_M([[0.5*P1-(1/3)*H1,(1/3)*P1,(1/3)*P1,-(1/6)*P1+(1/3)*H1]]),
    classical_order=4, stiff_order=2,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Celledoni, Marthinsen & Owren (2003), Eq. (7), affine action; EXPINT documentation",),
    legacy_file="cfree4.m",
)

# Rewrite z*phi_1 terms using z*phi_1(z)=exp(z)-I, avoiding a separate z-expression.
RKMK_A31 = 0.25*(E2-I)  # (z/8)*phi1(z/2)
RKMK_A32 = 0.5*H1 - 0.25*(E2-I)
RKMK_B1 = (1/6)*P1 + (1/12)*(E-I)
RKMK_B4 = (1/6)*P1 - (1/12)*(E-I)
RKMK4T = _make(
    name="RKMK4t", family="Affine Lie-group / RKMK", c=(0.0,0.5,0.5,1.0),
    U=_M([[I],[E2],[E2],[E]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[0.5*H1,ZERO,ZERO,ZERO],[RKMK_A31,RKMK_A32,ZERO,ZERO],[ZERO,ZERO,P1,ZERO]]),
    V=_M([[E]]), B=_M([[RKMK_B1,(1/3)*P1,(1/3)*P1,RKMK_B4]]),
    classical_order=4, stiff_order=1, weak_stiff_order=2,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Munthe-Kaas (1999), truncated dexp^{-1}; EXPINT documentation",),
    notes=("Strong exponential-RK order-two moment fails, while its z=0 weak condition holds; HO-type tests show conditional order about 2. The legacy source comment (1) is consistent with strong stiff order; README label (2) is weak/conditional.",),
    legacy_file="rkmk4t.m",
)


# ---------------------------------------------------------------------------
# Generalized Lawson ETDq/RK4 family derived directly from Krogstad (2005).
# ---------------------------------------------------------------------------

def _genlawson(q: int, *, modified: bool):
    nodes = [Fraction(-j) for j in range(q)]
    lag = [_lagrange_basis(nodes,j) for j in range(q)]
    cmid = [_phi_integral(p, Fraction(1,2)) for p in lag]
    cfull = [_phi_integral(p, Fraction(1)) for p in lag]
    lmid = [_poly_value(p, Fraction(1,2)) for p in lag]
    lone = [_poly_value(p, Fraction(1)) for p in lag]

    r, s = q, 4
    U = _zeros(s,r); A = _zeros(s,s)
    U[0][0] = I
    U[1][0] = E2; A[1][0] = cmid[0]
    for j in range(1,q): U[1][j] = cmid[j]

    U[2][0] = E2
    A[2][0] = cmid[0] - 0.5*float(lmid[0])*I
    A[2][1] = 0.5*I
    for j in range(1,q): U[2][j] = cmid[j] - 0.5*float(lmid[j])*I

    U[3][0] = E
    A[3][0] = cfull[0] - float(lmid[0])*E2
    A[3][2] = E2
    for j in range(1,q): U[3][j] = cfull[j] - float(lmid[j])*E2

    if not modified:
        b0 = cfull[0] - (2/3)*float(lmid[0])*E2 - (1/6)*float(lone[0])*I
        first_b = [b0,(1/3)*E2,(1/3)*E2,(1/6)*I]
        first_v = [E] + [cfull[j] - (2/3)*float(lmid[j])*E2 - (1/6)*float(lone[j])*I for j in range(1,q)]
        # Symbolic Phase-4 audit: strong P=q; weak q+1 only for q<=3.
        stiff = {1:2,2:3,3:4,4:4,5:5}[q]
        classical = {1:4,2:4,3:4,4:4,5:5}[q]
        weak = q+1 if q <= 3 else None
        name = f"GenLawson4{q}"
        references = ("Krogstad (2005), Section 3, ETDq/RK4 construction", "OTW (2006) order framework")
        notes = ("Generated from Krogstad's interpolation/flow construction, not from the legacy MATLAB coefficients.",)
        P = q
    else:
        # Keep Krogstad's stages, but determine the physical output weights by
        # enforcing the full OTW quadrature conditions through P=q+1 while
        # retaining the RK4 middle weights B2=B3=exp(z/2)/3.
        P = q + 1
        # Unknowns are [B1, B4, V1,...,V_{q-1}] at nodes 0,1,-1,...
        xnodes = [Fraction(0),Fraction(1)] + [Fraction(-k) for k in range(1,q)]
        M = np.array([[float(x**m) for x in xnodes] for m in range(P)], dtype=float)
        # Invert once as rational arithmetic using sympy-free Fraction Gaussian elimination.
        aug = [[Fraction(xnodes[col]**row) for col in range(P)] + [Fraction(int(row==rhs)) for rhs in range(P)] for row in range(P)]
        # Gauss-Jordan inverse.
        for col in range(P):
            pivot = next(i for i in range(col,P) if aug[i][col] != 0)
            aug[col],aug[pivot] = aug[pivot],aug[col]
            fac=aug[col][col]; aug[col]=[x/fac for x in aug[col]]
            for i in range(P):
                if i==col: continue
                fac=aug[i][col]
                if fac: aug[i]=[a-fac*b for a,b in zip(aug[i],aug[col])]
        inv = [row[P:] for row in aug]
        rhs_expr=[]
        for m in range(P):
            # moment m corresponds ell=m+1: m!*phi_{m+1}
            rhs = float(factorial(m))*phi(m+1,1.0)
            # fixed B2+B3 = 2/3 E2 at c=1/2
            rhs = rhs - float(2*Fraction(1,3)*Fraction(1,2)**m)*E2
            rhs_expr.append(rhs)
        sol=[]
        for i in range(P):
            expr: OperatorExpr=ZERO
            for j in range(P):
                if inv[i][j]: expr=expr+float(inv[i][j])*rhs_expr[j]
            sol.append(expr)
        B1,B4=sol[0],sol[1]
        Vhist=sol[2:]
        first_b=[B1,(1/3)*E2,(1/3)*E2,B4]
        first_v=[E]+Vhist
        stiff=P; classical=max(4, P); weak=None
        name=f"ModGenLawson4{q}"
        references=("Krogstad (2005) internal stages; OTW quadrature conditions", "EXPINT modified generalized Lawson documentation")
        notes=("Output B,V generated uniquely from strong quadrature order P=q+1; no translation of unlisted legacy coefficients.",)

    V,B=_history_output(first_v, first_b, r, s)
    return _make(
        name=name, family=("Modified generalized Lawson" if modified else "Generalized Lawson")+" / exponential GLM",
        c=(0.0,0.5,0.5,1.0), U=_M(U), A=_M(A), V=V, B=B,
        classical_order=classical, stiff_order=stiff, stage_order=q, quadrature_order=P,
        weak_quadrature_order=weak,
        external_layout=("solution_only" if q==1 else "nonlinear_history"), nonlinear_evals_per_step=4,
        references=references, notes=notes,
        legacy_file=("mod" if modified else "")+f"genlawson4{q}.m",
        provenance_status="derived-from-published-construction",
    )


GENLAWSON41, GENLAWSON42, GENLAWSON43, GENLAWSON44, GENLAWSON45 = (_genlawson(q,modified=False) for q in range(1,6))
MODGENLAWSON41, MODGENLAWSON42, MODGENLAWSON43, MODGENLAWSON44, MODGENLAWSON45 = (_genlawson(q,modified=True) for q in range(1,6))


# ---------------------------------------------------------------------------
# Historical Crank-Nicolson comparator.
# Four explicit fixed-point/Newton-like iterations reproduce the EXPINT design;
# rational actions are handled by backend shifted solves rather than phi functions.
# ---------------------------------------------------------------------------
CN_R = resolvent(0.5)              # (I - z/2)^(-1)
CN_CAYLEY = 2*CN_R - I             # (I-z/2)^(-1)(I+z/2)
CN_PHI = 0.5*CN_R                  # (2I-z)^(-1)
CRANK_NICOLSON = _make(
    name="CrankNicolson", family="Historical comparator / fixed-point Crank-Nicolson",
    c=(0.0,1.0,1.0,1.0), U=_M([[I],[CN_CAYLEY],[CN_CAYLEY],[CN_CAYLEY]]),
    A=_M([[ZERO,ZERO,ZERO,ZERO],[2*CN_PHI,ZERO,ZERO,ZERO],[CN_PHI,CN_PHI,ZERO,ZERO],[CN_PHI,ZERO,CN_PHI,ZERO]]),
    V=_M([[CN_CAYLEY]]), B=_M([[CN_PHI,ZERO,ZERO,CN_PHI]]),
    classical_order=2, stiff_order=None,
    external_layout="solution_only", nonlinear_evals_per_step=4,
    references=("Classical Crank-Nicolson; EXPINT historical four-iteration comparator",),
    notes=("Not an exponential integrator; retained only for historical EXPINT catalogue completeness.",),
    legacy_file="cranknicolson.m", provenance_status="EXPINT-documentation/source-description", historical_comparator=True,
)


# Complete 47-entry EXPINT 1.1 catalogue, ordered by the historical package families.
ALL_METHODS = (
    LAWSON_EULER, ABLAWSON2, ABLAWSON3, ABLAWSON4, LAWSON2A, LAWSON2B, LAWSON4,
    NORSETT_EULER, ABNORSETT2, ABNORSETT3, ABNORSETT4,
    PEC322, PEC423, PEC524, PEC625, PEC726,
    PECEC332, PECEC433, PECEC534, PECEC635, PECEC736,
    EGLM332, EGLM433,
    ETD2RK, ETD3RK, EHLE_LAWSON, ETD4RK, KROGSTAD, STREHMEL_WEINER, FRIEDLI, HOCHOST4, ETD5RKF,
    RKMK2E, ETD2CF3, CFREE4, RKMK4T,
    GENLAWSON41, GENLAWSON42, GENLAWSON43, GENLAWSON44, GENLAWSON45,
    MODGENLAWSON41, MODGENLAWSON42, MODGENLAWSON43, MODGENLAWSON44, MODGENLAWSON45,
    CRANK_NICOLSON,
)

assert len(ALL_METHODS) == 47
assert len({m.name.lower() for m in ALL_METHODS}) == 47
for _m in ALL_METHODS:
    _m.validate()

_REGISTRY = {m.name.lower(): m for m in ALL_METHODS}
# Legacy filename aliases and a few common spelling aliases.
for _m in ALL_METHODS:
    if _m.legacy_file:
        _REGISTRY[_m.legacy_file.removesuffix('.m').lower()] = _m
_REGISTRY.update({
    "hochbruckostermann": HOCHOST4,
    "hochbruck-ostermann": HOCHOST4,
    "ehlelawson": EHLE_LAWSON,
    "strehmelweiner": STREHMEL_WEINER,
    "crank-nicolson": CRANK_NICOLSON,
})


def get_method(name: str) -> MethodSpec:
    try:
        return _REGISTRY[name.lower()]
    except KeyError as exc:
        raise KeyError(f"Unknown method {name!r}; available: {list_methods()}") from exc


def list_methods() -> tuple[str, ...]:
    return tuple(m.name for m in ALL_METHODS)
