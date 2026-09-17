# PyEXPINT Phase 4 — complete historical-catalogue report

## Executive result

Phase 4 completes the historical EXPINT scheme catalogue on the PyEXPINT
backend-independent architecture.

- **Catalogue:** 47/47 schemes.
- **Automated tests:** 96 passed.
- **Matrix-free catalogue exercise:** all 47 methods execute post-startup main steps.
- **Maximum discrepancy, Krylov vs diagonal reference:** approximately 5.3e-12.

The scientific result is not merely the count 47: one mathematical `MethodSpec`
abstraction and one general EGLM engine represent the complete historical catalogue.
High-order families are generated from mathematical constructions and verified by
order conditions rather than transcribed from old source.

## 1. Catalogue closure

Every canonical historical scheme filename has exactly one PyEXPINT entry; there are
no unmatched or duplicate names. `phase4_catalogue.json` is the authoritative map.

The catalogue includes Lawson/Adams–Lawson, exponential Adams, PEC/PECEC, standalone
EGLM, ETD/exponential Runge–Kutta, affine Lie-group-related methods, generalized
Lawson, modified generalized Lawson, and the historical Crank–Nicolson comparator.

## 2. Independent generation of high-order PEC/PECEC

For order p, set q=p-1 and interpolate the nonlinear term at the historical nodes in
the variation-of-constants formula. The two-stage PEC family uses an exponential
Adams predictor of order p-1 and an exponential Adams–Moulton corrector of order p;
PECEC evaluates and reapplies that corrector.

Generated in Phase 4:

- PEC524, PEC625, PEC726;
- PECEC534, PECEC635, PECEC736.

The automated OTW checker verifies for p=3,...,7

    Q = p-1,  P = p,

hence full parabolic order p under the OTW hypotheses. This independently resolves
the old `pec726.m` header: the actual method is order 7 with six external components,
not “order 6, r=5”.

## 3. Generalized Lawson family from Krogstad

The family is generated from Krogstad's published ETDq/RK4 construction:

1. interpolate the nonlinear term through the current and previous q-1 nodes;
2. build its exponentially propagated interpolation flow;
3. apply classical RK4 to the residual transformed equation.

The resulting order signatures are:

| q | method | Q | strong P | weak P | stiff order |
|---:|---|---:|---:|---:|---:|
| 1 | GenLawson41 | 1 | 1 | 2 | 2 |
| 2 | GenLawson42 | 2 | 2 | 3 | 3 |
| 3 | GenLawson43 | 3 | 3 | 4 | 4 |
| 4 | GenLawson44 | 4 | 4 | — | 4 |
| 5 | GenLawson45 | 5 | 5 | — | 5 |

The generated GenLawson43 reproduces the previously hand-audited Phase-2/3
specification to approximately 1.1e-16 at independent complex test points.

## 4. Modified generalized Lawson family

The Krogstad internal stages are retained. Physical-output weights B,V are generated
by imposing the strong OTW quadrature conditions through P=q+1 while retaining the
RK4 middle-stage weights.

| method | Q | strong P | stiff order | classical order |
|---|---:|---:|---:|---:|
| ModGenLawson41 | 1 | 2 | 2 | 4 |
| ModGenLawson42 | 2 | 3 | 3 | 4 |
| ModGenLawson43 | 3 | 4 | 4 | 4 |
| ModGenLawson44 | 4 | 5 | 5 | 5 |
| ModGenLawson45 | 5 | 6 | 6 | 6 |

The generated ModGenLawson43 reproduces the previously hand-audited documented
coefficients to about 8e-17.

## 5. Executable legacy defects identified

### ETD2RK

The supplied legacy `.m` uses

    b1 = phi1 - 2 phi2,

whereas Cox–Matthews and the EXPINT README require

    b1 = phi1 - phi2.

The legacy expression fails first-order consistency at L=0.

### ETD2CF3

The documented tableau has c2=1/3, so stage consistency requires

    A21(z) = (1/3) phi1(z/3).

The supplied `.m` evaluates `phi1(z/2)` in that coefficient. PyEXPINT uses the
mathematically consistent documented value.

### ETD5RKF

The documented c-vector contains c4=3/4. Matrix and vector branches of the legacy
code evaluate exp(3z/4), but the scalar branch evaluates exp(3z/5). PyEXPINT uses
exp(3z/4) uniformly.

## 6. Metadata anomalies retained in the audit trail

- EGLM332 legacy header: “Order 4, s=2, r=3”; independent audit gives p=3, s=3, r=2.
- PEC726 legacy header: “Order 6, r=5”; actual arrays use r=6 and order conditions give p=7.
- README prose calls PEC423 and PECEC433 stiff order 3; OTW conditions give order 4.
- RKMK2e/RKMK4t source comments conflict with the README about stiff order. Phase 4
  follows the README values (1 and 2) but flags both for a dedicated stiff-PDE audit.

## 7. Classical-order benchmark

Test problem:

    y' = -y + y^2,   y(0)=0.4,
    y(t)=1/(1+1.5 exp(t)),   T=1.6.

Stepsizes: 0.2, 0.1, 0.05, 0.025.

Every method demonstrates at least its expected classical order on a clean refinement
pair before roundoff contamination. Selected best clean slopes:

| method | expected | observed |
|---|---:|---:|
| ABLawson4 | 4 | 4.15 |
| ABNorsett4 | 4 | 3.90 |
| PEC524 | 5 | 4.90 |
| PEC625 | 6 | 5.95 |
| PEC726 | 7 | 7.66 |
| PECEC534 | 5 | 4.99 |
| PECEC635 | 6 | 6.15 |
| PECEC736 | 7 | 6.59 |
| EGLM332 | 3 | 2.97 |
| EGLM433 | 4 | 3.97 |
| ETD4RK | 4 | 4.00 |
| Krogstad | 4 | 4.00 |
| HochOst4 | 4 | 3.98 |
| ETD5RKF | 5 | 4.98 |
| GenLawson45 | 5 | 5.07 |
| ModGenLawson44 | 5 | 4.92 |
| ModGenLawson45 | 6 | 5.97 |
| CrankNicolson | 2 | 2.04 |

High-order methods can reach the double-precision floor on the finest pair; tests use
a clean-pair criterion rather than blindly fitting roundoff-contaminated points.

## 8. Matrix-free full-catalogue test

A 64-dimensional diagonal operator is hidden behind `LinearOperator`; the Krylov
backend never sees its diagonal. With T=0.35 and h=0.05 there are seven total steps,
so even r=6 methods perform true main EGLM steps after startup.

All 47 methods agree with the direct diagonal backend within the requested matrix-
function tolerance. The maximum observed discrepancy is about

    5.3e-12.

The largest discrepancy is the rational Crank–Nicolson comparator, which uses shifted
linear solves rather than exact exponential/phi actions.

## 9. Test architecture

Phase 4 tests:

- 47/47 catalogue mapping;
- `MethodSpec` dimensions and explicitness;
- stable phi functions and dense/diagonal consistency;
- exact-linear propagation for all true exponential methods;
- Crank–Nicolson second-order linear convergence;
- classical observed order for all 47 entries;
- OTW quadrature conditions for ABNorsett;
- OTW stage/quadrature conditions through order 7 for PEC/PECEC;
- strong/weak OTW conditions for generalized Lawson;
- strong P=q+1 conditions for modified generalized Lawson;
- external-history shift semantics;
- all-47 matrix-free execution and Krylov fusion;
- ETD2RK, ETD2CF3 and ETD5RKF regression guards.

Final result:

    96 passed

## 10. TOMS assessment after Phase 4

The historical reproduction component is now demonstrated, not speculative: all 47
schemes fit one modern backend-independent architecture and are automatically
validated.

A TOMS submission would still be premature if work stopped here. The next scientific
claim must come from modern computation: robust stiff-order benchmarks, multiple
phi-action engines, cost-aware backend/fusion selection, error control, matrix-free
scaling, and systematic comparisons with current approaches.

The appropriate framing remains:

> PyEXPINT: A backend-independent framework for exponential general linear integrators

rather than “a Python port of EXPINT”.
