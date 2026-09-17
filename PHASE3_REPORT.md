# PyEXPINT — Phase 3 matrix-free/Krylov report

## 1. Status

**Phase 3 completed successfully.**

Validation status: **35/35 tests passed** after editable installation.

Version: `0.3.0.dev0`.

The central result is that the general Phase-2 EGLM engine now runs unchanged
on dense matrices, diagonal operators, SciPy sparse matrices and arbitrary
`LinearOperator` objects.

## 2. New backend abstraction

`KrylovBackend` accepts only a matrix-vector product interface.  No dense or
sparse matrix is required when a `LinearOperator` is provided.

For one vector `v`, a coefficient

\[
g(hL)=\sum_j \alpha_j\varphi_{k_j}(c_jhL)
\]

is approximated by an Arnoldi basis

\[
K_m(L,v)=\operatorname{span}\{v,Lv,\ldots,L^{m-1}v\}
\]

and a small projected Hessenberg matrix `H_m`:

\[
g(hL)v \approx \|v\|V_m g(hH_m)e_1.
\]

All \(\varphi_k\) at a common scale use one small augmented exponential.

## 3. Multivector phi-combination primitive

Phase 3 also implements the more important exponential-integrator primitive

\[
\boxed{\displaystyle
\sum_{k=0}^{p}\varphi_k(\tau hL)b_k
}
\]

with distinct vectors `b_k`.

Introduce auxiliary polynomial variables

\[
q_1=1,\quad q_2=t,\quad q_3=t^2/2!,\ldots
\]

with a nilpotent Jordan chain.  Then the desired combination is the physical
part of one exponential of the augmented operator

\[
\widetilde L=
\begin{pmatrix}
\tau hL & b_1 & b_2 & \cdots & b_p\\
0        &     & J   &        &
\end{pmatrix}
\]

acting on `[b_0; e_1]`.

The augmented operator is itself matrix-free.  Each augmented Krylov matvec
requires exactly one matvec with the original `L`, plus vector axpy operations.

## 4. Automatic EGLM fusion

The generic EGLM engine frequently evaluates sums such as

\[
\sum_j B_{ij}(hL)G_j.
\]

When all nonzero coefficient expressions are `PhiCombination`s at the same
scale, PyEXPINT now collects coefficients by phi index and forms vectors

\[
b_k=\sum_j \alpha_{jk}G_j.
\]

The entire sum is then evaluated in **one augmented Krylov projection**.

If scales differ, or a coefficient contains an operator product, the engine
falls back automatically to independent actions.  Thus fusion is an
optimization, not a change of mathematical semantics.

## 5. Adaptive Arnoldi controls

Current controls:

- `tol` — requested relative successive-projection tolerance;
- `min_dim` — first Krylov dimension at which convergence is inspected;
- `max_dim` — hard Krylov dimension cap;
- `check_every` — dimension increment between convergence checks;
- `breakdown_tol` — happy-breakdown threshold;
- optional full reorthogonalization;
- `fail_on_nonconvergence`.

The estimator is

\[
\eta_m=
\frac{\|y_m-y_{m-\Delta m}\|}
     {\max(1,\|y_m\|,\|v\|)}.
\]

This is a **practical Phase-3 estimator**, not a rigorous error bound and not
the KIOPS/phipm adaptive algorithm.

## 6. Statistics

Every solve can report:

- matrix-vector products;
- Krylov projections;
- projected-matrix evaluations;
- same-vector phi-combination actions;
- multivector linear-combination actions;
- automatically fused EGLM sums;
- augmented Krylov projections;
- mean/max Krylov dimension;
- happy breakdowns;
- nonconverged actions;
- last action-error estimate.

These counters are necessary for fair work-precision comparisons: stages alone
are not a meaningful cost metric once matrix-function actions are matrix-free.

## 7. Validation

### 7.1 Sparse diagonal vs exact diagonal backend

Sparse diagonal operators agree with the elementwise diagonal oracle for
individual phi functions and nontrivial linear combinations.

### 7.2 `LinearOperator` vs dense backend

Random non-diagonal `LinearOperator` actions agree with the dense reference
backend to the requested tolerance.

### 7.3 Distinct-right-hand-side combination

For independently generated vectors `b_0,...,b_3`, the augmented action

\[
\sum_{k=0}^3\varphi_k(hA)b_k
\]

agrees with the sum of four dense-reference actions.

### 7.4 All 13 P0 methods

All 13 methods run with a matrix-free `LinearOperator` and match their
`DiagonalBackend` solutions on a common semilinear test problem.

### 7.5 Sparse non-diagonal integration

ETD4RK with a sparse tridiagonal operator agrees with `DenseBackend` on the
corresponding dense matrix.

### 7.6 Zero-vector fast path

A zero right-hand side triggers no matvec.

## 8. Fused vs unfused benchmark

Benchmark:

- dimension `n=256`;
- sparse tridiagonal linear operator;
- semilinear reaction `N(y)=0.08 y^2`;
- `T=0.30`, `h=0.05`;
- Arnoldi tolerance `1e-10`;
- identical algorithm with fusion disabled/enabled.

| Method | matvec unfused | matvec fused | reduction |
|---|---:|---:|---:|
| ETD4RK | 756 | 594 | 21.4% |
| Krogstad | 756 | 486 | **35.7%** |
| HochOst4 | 1026 | 756 | 26.3% |
| PEC423 | 774 | 522 | **32.6%** |
| EGLM433 | 990 | 621 | **37.3%** |
| GenLawson43 | 1206 | 1044 | 13.4% |
| ModGenLawson43 | 1206 | 1044 | 13.4% |

Fused and unfused final states differed only at approximately machine roundoff
(~`0` to `4e-16` relative).

Wall-clock behavior is more nuanced.  Fusion was faster for Krogstad, PEC423,
EGLM433 and both generalized-Lawson tests, but slightly slower in some runs for
ETD4RK/HochOst4 because the sparse matvec is extremely cheap and the larger
projected augmented exponential has non-negligible overhead.

**Important consequence:** future automatic fusion should use a cost model; a
matvec reduction alone is not sufficient to predict elapsed-time improvement.

## 9. Large matrix-free smoke test

A `LinearOperator` of dimension **10,000** was integrated for one Krogstad step
without materializing a matrix.

Observed:

- elapsed time ~0.40 s in the current container;
- `81` large-operator matvecs;
- `9` Krylov projections;
- mean/max Krylov dimension `9`;
- `3` augmented multivector projections;
- no nonconverged actions;
- final action estimator ~`3.2e-14` for requested tolerance `1e-9`.

This is a functionality/scaling smoke test, not a performance claim.

## 10. What Phase 3 deliberately is not

The current backend should not be described as KIOPS or `phipm`.

KIOPS adds, among other ideas, incomplete orthogonalization and a specialized
adaptive strategy for both substeps and Krylov dimensions.  `phipm` likewise
uses time stepping to prevent uncontrolled Krylov growth.

PyEXPINT Phase 3 instead establishes a clean backend contract and a correct
matrix-free reference Krylov implementation on which those algorithms can be
added and compared later.

## 11. Scientific consequence

After Phase 3, the architecture separates three independent objects:

\[
\boxed{
\text{MethodSpec}
\longleftrightarrow
\text{generic EGLM engine}
\longleftrightarrow
\text{matrix-function action backend}
}
\]

The same 13 mathematical method specifications now run without modification on
four operator regimes:

1. diagonal;
2. dense;
3. sparse;
4. arbitrary matrix-free `LinearOperator`.

That is the first milestone that clearly exceeds the computational model of
EXPINT 2007 rather than merely reproducing it.

## 12. Recommended Phase 4

The next phase should **not** immediately add more Krylov sophistication.
First complete the historical EXPINT method catalogue under the now-stable
architecture, while retaining tests for metadata/order/provenance.

In parallel, define the backend-comparison protocol needed later for

- full Arnoldi vs incomplete orthogonalization;
- KIOPS-style adaptive substepping;
- Leja;
- rational Krylov;
- dense/scaling-recovering algorithms.

This prevents a new backend from forcing changes to `MethodSpec` or the EGLM
engine.
