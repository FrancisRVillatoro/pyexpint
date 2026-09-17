# PyEXPINT — Phase 1 implementation report

## Status

**Phase 1 completed successfully.**

The milestone implements the minimal independent one-step core needed to validate
the PyEXPINT architecture before adding multistep/multi-output EGLM machinery.

Test status: **14 passed**.

## Implemented architecture

### `OperatorExpr`

Method coefficients are symbolic operator expressions rather than precomputed matrices.

Supported expression types:

- `PhiCombination`: linear combinations of
  \[
  \alpha\,\varphi_k(c hL);
  \]
- sums and scalar multiples;
- `ProductExpr`: composition of analytic operator coefficients;
- identity and zero operators.

This is required already by Cox–Matthews ETD4RK: one internal coefficient contains

\[
\frac12\varphi_1(z/2)\,[e^{z/2}-I].
\]

A future matrix-free backend can therefore choose whether to evaluate a coefficient
as a fused action or as sequential actions without changing the method definition.

### `MethodSpec`

Phase-1 one-step form:

\[
Y_i=U_i(hL)y_n
+h\sum_{j<i}A_{ij}(hL)N(t_n+c_jh,Y_j),
\]

\[
y_{n+1}=V(hL)y_n
+h\sum_i B_i(hL)N(t_n+c_ih,Y_i).
\]

Metadata already records classical and stiff order, stage/quadrature order where useful,
references, and audit notes.

### Backends

#### `DiagonalBackend`

For diagonal/Fourier operators.

- elementwise phi evaluation;
- stable power series for \(|z|\le 1\);
- recurrence outside this region;
- cached phi values within a step;
- real and complex arguments.

The series branch is essential: a naive recurrence at \(z\approx 10^{-5}\) loses many
digits for higher phi functions.

#### `DenseBackend`

Reference backend for small/moderate dense matrices.

It evaluates phi matrices through an augmented block exponential using
`scipy.linalg.expm`. It is intentionally a validation backend rather than the final
large-scale algorithm.

### Fixed-step engine

`solve_fixed(problem, method, h, backend)`

Current scope:

- constant step size;
- semilinear `y' = L y + N(t,y)`;
- one-step methods only;
- real or complex states;
- backend-independent method definitions.

## Methods implemented

| Method | Classical order | Stiff order | Stages |
|---|---:|---:|---:|
| LawsonEuler | 1 | 1 | 1 |
| NorsettEuler | 1 | 1 | 1 |
| ETD2RK | 2 | 2 | 2 |
| ETD4RK | 4 | 2 | 4 |
| Krogstad | 4 | 3 | 4 |
| HochOst4 | 4 | 4 | 5 |

The ETD2RK implementation deliberately uses the published coefficient

\[
b_1=\varphi_1-\varphi_2
\]

rather than the inconsistent `phi1-2*phi2` line found in the supplied legacy MATLAB file.

## Validation

### 1. Phi-function limits

For \(0\le k\le7\),

\[
\varphi_k(0)=\frac1{k!}
\]

is tested to near machine precision.

Small real and complex arguments are compared with an independent power-series oracle.

### 2. Backend agreement

On diagonal matrices, `DenseBackend` and `DiagonalBackend` agree for:

- exponentials;
- individual phi functions;
- linear phi combinations;
- composed operator expressions.

### 3. Exact linear propagation

For \(N=0\), all six methods reduce exactly to

\[
y_{n+1}=e^{hL}y_n.
\]

This is tested both for diagonal \(L\) and for a non-diagonal dense matrix.

### 4. Classical order

Test problem:

\[
y'=-y+y^2,\qquad y(0)=\frac15,
\]

with exact solution

\[
y(t)=\frac{1}{1+4e^t}.
\]

Measured slopes from the last three refinements:

| Method | Expected | Measured |
|---|---:|---:|
| LawsonEuler | 1 | 0.998324 |
| NorsettEuler | 1 | 1.009915 |
| ETD2RK | 2 | 1.992719 |
| ETD4RK | 4 | 3.962050 |
| Krogstad | 4 | 3.981937 |
| HochOst4 | 4 | 4.002884 |

At \(h=0.025\), the ETD4RK error on this test is approximately \(3.73\times10^{-12}\).

### 5. Historical ETD2RK regression

At \(L=0\), PyEXPINT asserts

\[
(b_1,b_2)=\left(\frac12,\frac12\right).
\]

This test specifically prevents reintroduction of the legacy EXPINT typo.

## Packaging validation

- source compilation succeeds;
- editable installation succeeds with
  `pip install -e . --no-build-isolation --no-deps`;
- no network is required when build dependencies are already present.

The ordinary isolated pip build attempted to contact the package index to create a fresh
build environment. This is expected pip behavior, not a PyEXPINT numerical issue.

## Deliberate limitations of Phase 1

Not implemented yet:

- multistep external state;
- multi-output EGLMs;
- startup policies;
- variable/adaptive steps;
- sparse matrices;
- `LinearOperator`;
- Krylov/Leja/KIOPS phi-action engines;
- backend tolerance/error estimates;
- performance scheduling of multiple phi combinations.

The expression and method APIs were designed so these additions do not require changing
the mathematical definitions of the six Phase-1 methods.

## Phase 2 target

Phase 2 should add the true EGLM state engine and the remaining P0 structural methods:

- ABNorsett4;
- PEC423;
- PECEC433;
- EGLM332;
- EGLM433;
- GenLawson43;
- ModGenLawson43.

The key new abstraction will be an **external state vector** carrying solution/history
components, together with an explicit interchangeable startup policy.

Only after that is stable should the project proceed to Phase 3 matrix-free Krylov actions.
