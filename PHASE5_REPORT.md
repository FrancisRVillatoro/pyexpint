# PyEXPINT Phase 5 — stiff-order audit and modern backend layer

## Executive result

Phase 5 moves PyEXPINT beyond historical catalogue reproduction and into modern
matrix-function algorithmics.

Main results:

- Hochbruck–Ostermann stiff-order/order-reduction benchmark implemented from the
  published PDEs, with the finite-difference Laplacian diagonalized by DST-I so
  time-discretization errors are not polluted by a Krylov tolerance;
- historical `RKMK2e` / `RKMK4t` inconsistency resolved by separating **strong
  stiff order** from weak/conditional observed order;
- independent `KiopsBackend` implementing the augmented-matrix + incomplete
  orthogonalization + adaptive-substep design of KIOPS;
- independent real `LejaBackend` using Newton interpolation at real Leja points;
- `AutoBackend` selecting diagonal, dense, Leja or KIOPS-style execution from
  operator structure and a calibrated crossover rule;
- both modern matrix-free backends execute the complete 47-method catalogue;
- complete automated test suite: **105 passed**.

## 1. Stiff-order benchmark

The two benchmark PDEs are those of Hochbruck & Ostermann (2005), with exact
solution

\[
U(x,t)=x(1-x)e^t,\qquad 0<x<1,
\]

and homogeneous Dirichlet boundary conditions.

### Problem 1 — local nonlinearity

\[
U_t-U_{xx}=\frac{1}{1+U^2}+\Phi(x,t).
\]

### Problem 2 — nonlocal nonlinearity

\[
U_t-U_{xx}=\int_0^1 U(x,t)\,dx+\Phi(x,t).
\]

The source is generated from the exact solution at the **semidiscrete** level.
The second derivative is discretized on 200 interior points.  Since the
Dirichlet finite-difference Laplacian is exactly diagonalized by DST-I, all
phi-actions are evaluated by `DiagonalBackend` in sine space.

This isolates time-order reduction from matrix-function approximation error.

Stepsizes used in the final benchmark:

\[
h=1/20,1/40,1/80,1/160,1/320,1/640.
\]

### Final pairwise slopes

| method | local problem | nonlocal problem |
|---|---:|---:|
| Cox–Matthews ETD4RK | 3.279 | **2.502** |
| Krogstad | **3.995** | 3.365 |
| HochOst4 | **3.947** | **4.022** |
| RKMK2e | 1.965 | 1.989 |
| RKMK4t | 2.160 | 2.160 |
| Cfree4 | 2.028 | 2.028 |

The expected asymptotic signatures from the original analysis are recovered:
Cox–Matthews tends toward order 3 in the first problem and 2.5 in the second;
Krogstad is order 4 in the local example and approaches the predicted reduced
order 3.5 in the nonlocal case; HochOst4 stays at order 4.

Krogstad's 3.5 regime is approached slowly before floating-point effects become
relevant, exactly as one expects for a fractional order-reduction asymptotic.

## 2. Resolution of RKMK metadata conflict

For a one-step exponential RK representation, the strong second-order moment is

\[
\sum_i c_i b_i(z)=\varphi_2(z).
\]

Both `RKMK2e` and `RKMK4t` fail this identity for generic \(z\ne0\), while

\[
\sum_i c_i b_i(0)=\frac12=\varphi_2(0).
\]

Therefore Phase 5 records

\[
\boxed{p_{\rm stiff,strong}=1,\qquad p_{\rm stiff,weak}=2}
\]

for both methods.

This resolves the historical source/README disagreement:

- `RKMK2e`: README's label 1 is the strong stiff-order classification; the old
  source comment 2 corresponds only to the weak/classical behavior.
- `RKMK4t`: the old source comment 1 is the strong stiff order; README's label 2
  is weak/conditional.

The Hochbruck–Ostermann PDE tests show approximately second-order convergence for
both, which is entirely consistent with the weak condition and does **not** imply
that the strong second-order moment is satisfied.

`MethodSpec` now has a separate `weak_stiff_order` field.

## 3. `KiopsBackend`

Phase 5 adds a fresh Python implementation based on the algorithmic structure of
Gaudreault–Rainwater–Tokman KIOPS:

1. represent a linear combination
   \[
   \sum_{k=0}^p \varphi_k(hA)b_k
   \]
   as one augmented exponential action;
2. form a Krylov basis using **incomplete orthogonalization** with default
   orthogonalization length 2;
3. obtain a residual-style local error estimator from the projected exponential;
4. adapt Krylov dimension and, when necessary, split the exponential action into
   substeps;
5. retain fused distinct-right-hand-side phi combinations from the Phase-3 EGLM
   engine.

This module was written independently from the mathematical algorithm.  It is not
line-by-line derived from the LGPL MATLAB reference code.

Default research settings:

```python
KiopsBackend(
    tol=1e-10,
    m_init=12,
    m_min=8,
    m_max=64,
    orth_len=2,
)
```

Statistics include matvecs, accepted/rejected substeps, Krylov steps, small
exponentials, maximum and mean Krylov dimensions, and final residual indicator.

## 4. `LejaBackend`

The second modern engine is independent real-Leja interpolation.

For an operator with real spectral interval \([a,b]\), coefficients

\[
f(A)v,\qquad
f(z)=\sum_j\alpha_j\varphi_{k_j}(c_jhz),
\]

are approximated directly by Newton interpolation on a real Leja sequence mapped
from \([-1,1]\) to \([a,b]\).

Important implementation choice: Phase 5 interpolates the analytic coefficient
**directly on the original operator**, rather than applying Leja to a high-order
augmented Jordan block.  The latter was found to be unnecessarily fragile for the
high-order PEC/PECEC catalogue because spectral bounds alone do not describe the
nonnormal augmented block well.

For distinct right-hand sides Leja currently evaluates the terms independently;
there is no fused RHS implementation yet.  This is deliberately different from
the Krylov engines.

Automatic spectral intervals are supported for real/Hermitian sparse matrices by
cheap conservative Gershgorin bounds.  A generic `LinearOperator` requires the
user to supply `spectral_bounds=(lambda_min,lambda_max)`.

## 5. Complete-catalogue backend validation

Test problem:

- 32-dimensional diagonal operator exposed only as a `LinearOperator`;
- nonlinear term \(0.1y^2\);
- \(T=0.35\), \(h=0.05\), so history methods execute genuine post-startup EGLM
  steps;
- direct diagonal execution is the reference.

| backend | 47/47 execute | max error vs diagonal | total matvecs |
|---|---:|---:|---:|
| KIOPS-style | yes | **2.81e-11** | 30,230 |
| real Leja | yes | **2.81e-11** | 43,864 |

The wall times in this tiny-dimensional catalogue test favor KIOPS-style, but that
is not the regime for which Leja is expected to shine.

## 6. Crossover benchmark

A sparse one-dimensional diffusion operator

\[
A=\sigma\,\mathrm{tridiag}(1,-2,1)
\]

was integrated with Krogstad for two steps using three explicit backends plus
`AutoBackend`.  Tolerance was \(10^{-9}\).  Timings below are container-local and
are used only for selector calibration, not as publication-quality performance
claims.

### Dimension 256

| scaled width | Arnoldi | KIOPS-style | Leja | Auto |
|---:|---:|---:|---:|---:|
| 10 | 0.0151 s | **0.0065** | 0.0229 | **0.0062** |
| 40 | 0.0248 | **0.0085** | 0.0349 | **0.0073** |

### Dimension 1024

| scaled width | Arnoldi | KIOPS-style | Leja | Auto |
|---:|---:|---:|---:|---:|
| 10 | 0.4427 | 0.1479 | **0.0237** | 0.0330 |
| 40 | 0.4030 | 0.1199 | 0.0412 | **0.0289** |

### Dimension 4096

| scaled width | Arnoldi | KIOPS-style | Leja | Auto |
|---:|---:|---:|---:|---:|
| 10 | 0.3657 | 0.1399 | 0.0471 | **0.0330** |
| 40 | 0.3435 | 0.1339 | 0.0548 | **0.0347** |

The central observation is that **matvec count is not a sufficient cost model**.
At large dimension, Leja can be much faster while performing more matvecs because
it avoids Krylov orthogonalization/global inner-product work.

This motivates the Phase-5 selector rule:

- diagonal vector -> diagonal backend;
- small dense operator -> dense reference backend;
- sufficiently large real/Hermitian sparse operator with bounded scaled spectral
  width -> Leja;
- otherwise -> KIOPS-style.

The thresholds remain explicit parameters because they are hardware- and
operator-dependent.

## 7. `AutoBackend`

Current default research policy:

```python
AutoBackend(
    tol=1e-10,
    dense_cutoff=96,
    leja_min_size=512,
    leja_width_threshold=200,
)
```

The selector records its choices and the statistics of the selected child backend.
It is intentionally simple and inspectable rather than a black-box ML selector.

## 8. Automated validation

The Phase-5 suite contains **105 tests**, all passing.

New tests cover:

- KIOPS-style phi actions against exact diagonal actions;
- KIOPS-style combinations with distinct right-hand sides;
- Leja phi actions against exact diagonal actions;
- Krogstad integration with both new backends;
- automatic backend selection;
- two Hochbruck–Ostermann order-reduction PDEs;
- strong-vs-weak RKMK order condition;
- preservation of all 96 Phase-4 tests.

## 9. What Phase 5 establishes

PyEXPINT now has a substantive modern computational story:

\[
\boxed{
\text{one verified 47-method EGLM catalogue}
\;\times\;
\text{multiple interchangeable phi engines}
}
\]

with

- dense reference;
- diagonal exact/action backend;
- full-Arnoldi Krylov;
- adaptive incomplete-orthogonalization KIOPS-style;
- real-Leja polynomial interpolation;
- rule-based automatic selection.

It also has a reproducible order-reduction benchmark that distinguishes classical,
strong stiff, weak stiff, and problem-dependent observed orders.

## 10. Remaining work for a strong TOMS paper

Phase 5 is a major threshold, but it is not yet the final paper benchmark.
The next phase should focus on **error control and publication-grade comparisons**:

1. adaptive time stepping with a clean separation between time-discretization and
   matrix-function tolerances;
2. reference KIOPS/LeXInt comparisons under their actual licenses, without copying
   their code into PyEXPINT;
3. work–precision maps on the historical EXPINT PDE set plus modern larger
   sparse/matrix-free PDEs;
4. memory and synchronization/inner-product accounting, not only matvecs;
5. backend-selector calibration across operator classes;
6. optional rational-Krylov or BAMPHI comparison;
7. API/documentation stabilization and package release engineering.

The paper framing is now stronger than after Phase 4: PyEXPINT is no longer merely a
modern execution framework for old methods; it is becoming an experimentally
validated **backend-independent algebra for exponential GLMs with automatic
matrix-function execution strategies**.
