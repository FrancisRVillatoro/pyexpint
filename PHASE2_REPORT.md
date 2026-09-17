# PyEXPINT — Phase 2 implementation report

## Result

Phase 2 is complete: the Phase-1 one-step prototype has been generalized to a true explicit exponential general-linear-method (EGLM) engine with arbitrary internal stages `s` and external outputs `r`.

**Validation status: 26 tests passed.**

Package version: `0.2.0.dev0`.

## 1. Generic external-state engine

The numerical core now advances an external state

\[
X_n=(X_n^{[1]},\ldots,X_n^{[r]}),
\]

through

\[
Y_i=\sum_{j=1}^{r}U_{ij}(hL)X_n^{[j]}
    +\sum_{j<i}A_{ij}(hL)G_j,
\qquad
G_j=hN(t_n+c_jh,Y_j),
\]

and

\[
X_{n+1}^{[i]}=\sum_{j=1}^{r}V_{ij}(hL)X_n^{[j]}
    +\sum_{j=1}^{s}B_{ij}(hL)G_j.
\]

The first external component is the numerical solution.  For the historical P0 multistep/EGLM catalogue, the auxiliary layout is

\[
X_n=[y_n,\;hN(y_{n-1}),\;hN(y_{n-2}),\ldots].
\]

This layout is tested explicitly after every step.

## 2. Startup is now a policy, not a hard-coded solver choice

Two policies are implemented:

- `ExactStartup`: uses `problem.exact_solution` if supplied;
- `OneStepStartup(starter)`: builds the required nonlinear history with an arbitrary one-step method.

Default behavior:

- exact startup when an exact solution is available;
- otherwise `HochOst4` as the default fourth-order stiff starter.

This removes the historical coupling between the generic GLM driver and a single specific startup implementation.

## 3. Complete 13-method P0 catalogue

### One-step methods retained from Phase 1

- LawsonEuler — classical/stiff order 1/1
- NorsettEuler — 1/1
- ETD2RK — 2/2
- ETD4RK — 4/2
- Krogstad — 4/3
- HochOst4 — 4/4

### New Phase-2 multistep/multi-output methods

- ABNorsett4 — 4/4, `s=1`, `r=4`
- PEC423 — 4/4, `s=2`, `r=3`
- PECEC433 — 4/4, `s=3`, `r=3`
- EGLM332 — 3/3, `s=3`, `r=2`
- EGLM433 — 4/4, `s=3`, `r=3`
- GenLawson43 — 4/4, `s=4`, `r=3`
- ModGenLawson43 — 4/4, `s=4`, `r=3`

`ABNorsett4` is represented in the mathematically efficient one-stage form.  PyEXPINT does not reproduce the redundant second stage that the historical MATLAB package used only to fit a common driver representation.

## 4. Observed orders — exact history startup

Test problem:

\[
y'=-y+y^2,\qquad y(0)=0.2,
\qquad y(t)=\frac{1}{1+4e^t},\qquad T=0.8.
\]

Using `h = 0.1, 0.05, 0.025, 0.0125`, slopes fitted on the last three refinements:

| Method | Expected | Observed |
|---|---:|---:|
| ABNorsett4 | 4 | 3.93293 |
| PEC423 | 4 | 3.92588 |
| PECEC433 | 4 | 3.96370 |
| EGLM332 | 3 | 2.95890 |
| EGLM433 | 4 | 3.92060 |
| GenLawson43 | 4 | 4.03973 |
| ModGenLawson43 | 4 | 3.97481 |

## 5. Observed orders — numerical HochOst4 startup

The same experiment with no exact solution supplied gives:

| Method | Expected | Observed |
|---|---:|---:|
| ABNorsett4 | 4 | 3.93295 |
| PEC423 | 4 | 3.92588 |
| PECEC433 | 4 | 3.96369 |
| EGLM332 | 3 | 2.95889 |
| EGLM433 | 4 | 3.92060 |
| GenLawson43 | 4 | 4.04040 |
| ModGenLawson43 | 4 | 3.97454 |

There is no measurable order degradation from the numerical startup in this benchmark.

## 6. Structural tests

The test suite now checks:

1. all 13 `MethodSpec` objects have consistent `s x r`, `s x s`, `r x r`, and `r x s` dimensions;
2. explicit lower-triangular stage structure;
3. exact linear propagation for all 13 methods with diagonal operators;
4. exact linear propagation for all 13 methods with a non-diagonal dense operator;
5. diagonal/dense backend agreement for phi expressions and compositions;
6. stable phi evaluation near zero for real and complex arguments;
7. classical observed orders for all 13 methods;
8. external-history initialization semantics;
9. external-history shift semantics after a generic EGLM step;
10. fourth-order preservation under automatic HochOst4 startup;
11. the historical ETD2RK coefficient regression;
12. Phase-0 metadata invariants (`Q`, `P`, weak `P`).

## 7. Dense-backend nonlinear smoke test

All seven new Phase-2 methods have also been run successfully on the nonlinear Riccati test with `DenseBackend`, not only the diagonal backend.  At `h=0.05`, `T=0.4`, all produce finite errors consistent with their expected orders.

## 8. Packaging checks

- `python -m compileall src`: passed;
- editable install with `pip install -e . --no-build-isolation --no-deps`: passed;
- import and registry: 13 methods available;
- pytest: 26 passed.

## 9. Important architectural consequence

Phase 2 demonstrates the core claim needed for PyEXPINT: a single backend-independent stepping engine can execute, without method-specific branching,

- exponential Runge–Kutta;
- exponential Adams multistep;
- predictor-corrector PEC/PECEC;
- multi-output EGLMs;
- generalized Lawson and modified generalized Lawson schemes.

The next scientific/computational bottleneck is therefore no longer the integrator representation.  It is the evaluation of analytic operator actions.

## 10. Recommended Phase 3

Phase 3 should add the matrix-free layer:

1. `scipy.sparse` / `LinearOperator` support;
2. a Krylov `phi_action`/`phi_combination` backend;
3. backend tolerances and error estimates;
4. work counters (`matvecs`, Krylov dimension, rejected substeps, operator calls);
5. dense/diagonal/Krylov cross-validation;
6. first large sparse stiff-order benchmark.

That is the point at which PyEXPINT begins to test the principal TOMS-level hypothesis: the same verified EGLM catalogue running efficiently across dense, diagonal, sparse, and matrix-free operator representations.
