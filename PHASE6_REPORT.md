# PyEXPINT Phase 6 — adaptive control, calibrated dispatch, and paper-quality evidence

## Executive result

Phase 6 turns the Phase-5 fixed-step research prototype into an adaptive,
measurable computational framework.

**Version:** `0.6.0.dev0`  
**Historical catalogue:** 47 methods  
**Automated tests:** **115 passed**  
**Editable installation / compileall:** passed

New capabilities:

1. generic adaptive time stepping for one-step methods by step doubling;
2. explicit coupling of temporal tolerance and matrix-function tolerance;
3. algorithmic work and workspace metrics;
4. a measured/calibrated KIOPS-vs-Leja selector;
5. a hybrid SciPy-exponential/KIOPS backend;
6. reproducible work–precision–workspace benchmarks on periodic and nonperiodic
   semilinear PDE semidiscretizations;
7. an explicit provenance boundary against current KIOPS/LeXInt software.

The main negative result is scientifically useful: **no simple static selector is
universally optimal**.  The best matrix-function engine depends on dimension,
scaled spectral width, integrator, tolerance and problem-specific action mix.

## 1. Adaptive one-step solver

Phase 6 adds

```python
solve_adaptive(problem, method, backend, options=AdaptiveOptions(...))
```

for methods with one external solution component.

For a trial step of size `h`, the solver computes one full step and two half
steps.  For a method of order `p`,

\[
e_h \approx \frac{y_{h/2,h/2}-y_h}{2^p-1}.
\]

The normalized error uses

\[
\mathrm{scale}_i=\mathrm{atol}+\mathrm{rtol}
\max(|y_{n,i}|,|y_{n+1,i}|),
\]

and an RMS or infinity norm.  Accepted steps use the two-half-step value; optional
Richardson extrapolation exists but is disabled by default because stiff order
reduction can invalidate a correction based on classical order.

The controller is deliberately **not** enabled for multistep/multi-output EGLMs.
Variable-step versions of those methods require step-ratio-dependent coefficient
functions and a transformed external history.  Restarting at every step would
hide that mathematical issue and is not used.

### Scalar validation

On

\[
y'=-y+y^2,\qquad y(0)=0.2,\qquad
 y(t)=\frac{1}{1+4e^t},\quad T=2,
\]

all one-step reference methods respond correctly to tighter tolerances.  Examples:

| method | rtol | accepted | rejected | final error |
|---|---:|---:|---:|---:|
| ETD2RK | 1e-3 | 5 | 0 | 9.44e-5 |
| ETD2RK | 1e-5 | 20 | 1 | 5.29e-6 |
| ETD2RK | 1e-7 | 94 | 2 | 2.43e-7 |
| Krogstad | 1e-3 | 4 | 0 | 9.89e-8 |
| Krogstad | 1e-7 | 6 | 1 | 1.31e-8 |
| HochOst4 | 1e-7 | 6 | 1 | 1.20e-8 |

The unusually small errors of the fourth-order methods at loose tolerances reflect
that this smooth scalar problem is easy; the benchmark is a controller sanity
check rather than a tolerance-equals-global-error theorem.

## 2. Coupling temporal and matrix-function tolerances

`AdaptiveOptions` contains

```python
action_rtol_fraction = 0.05
```

and the matrix-function backend is cloned with

\[
\mathrm{tol}_{\mathrm{action}}
=\mathrm{clip}(f\,\mathrm{rtol},
                \mathrm{tol}_{\min},\mathrm{tol}_{\max}).
\]

A Phase-6 sweep at temporal `rtol=1e-6` gives:

### KIOPS-style

Changing `f` from 1 to 0.003 leaves the final error at `8.80e-8` and the counted
matvec total at 888 in this test.  KIOPS is already over-resolving the action in
this regime.

### Leja

| action fraction | action tol | error | matvecs |
|---:|---:|---:|---:|
| 1.0 | 1e-6 | 6.64e-7 | 1793 |
| 0.1 | 1e-7 | 6.39e-8 | 1991 |
| 0.03 | 3e-8 | 9.40e-8 | 2095 |
| 0.01 | 1e-8 | 9.04e-8 | 2190 |
| 0.003 | 3e-9 | 8.85e-8 | 2266 |

This demonstrates why the matrix-action tolerance must not simply be set equal to
the time tolerance.  For the current Leja implementation, roughly `0.1*rtol` or
tighter prevents action error from dominating this benchmark.  The package default
`0.05*rtol` is therefore a conservative Phase-6 choice.

## 3. Selector calibration

Phase 5 used hand-chosen dispatch thresholds.  Phase 6 adds

- `SelectorCalibration`;
- `fit_threshold_selector`;
- `CalibratedAutoBackend`.

The training benchmark contains 30 KIOPS/Leja pairs:

- Krogstad and HochOst4;
- N = 128, 256, 512, 1024, 2048;
- scaled spectral widths 5, 20, 60.

The fitted rule is

\[
\boxed{
\text{choose Leja if }N\ge512
\text{ and }h(\lambda_{\max}-\lambda_{\min})\le60,
}
\]

otherwise choose KIOPS (apart from the existing dense/diagonal shortcuts).

Calibration diagnostics on this machine:

- training cases: 30;
- mean log-regret: **0.0839**;
- worst slowdown: **2.80**;
- machine label: `Linux-x86_64-Python3.13.5`.

The worst case matters.  It shows that a two-feature threshold is not a universal
performance model.  Method-specific action patterns and timing noise can move the
crossover substantially.

The calibration object is serialized so another machine can regenerate and save
its own dispatch rule without changing PyEXPINT source.

## 4. Work–precision–workspace maps

Two semidiscrete manufactured PDE problems are used:

1. a periodic reaction-diffusion problem on a periodic finite-difference grid;
2. a Dirichlet semilinear diffusion problem with manufactured exact solution.

The linear diffusion strengths are chosen so both KIOPS and the current real-Leja
backend operate in a meaningful matrix-free regime.  The much stiffer
Hochbruck–Ostermann order-reduction problems remain a separate Phase-5 benchmark.

The compact Phase-6 map has 24 adaptive runs:

- 2 PDE problems;
- Krogstad and HochOst4;
- rtol 1e-4 and 1e-7;
- KIOPS, Leja, calibrated Auto.

All runs reach the final time and all three backends agree at the requested
matrix-function accuracy.

Representative periodic Krogstad results:

| backend | rtol | error | wall s | matvecs | estimated backend workspace |
|---|---:|---:|---:|---:|---:|
| KIOPS | 1e-4 | 1.29e-7 | 0.054 | 648 | 26.9 kB |
| Leja | 1e-4 | 1.74e-7 | 0.128 | 1452 | 6.1 kB |
| calibrated Auto | 1e-4 | 1.29e-7 | 0.077 | 776 | 31.8 kB |
| KIOPS | 1e-7 | 2.24e-8 | 0.158 | 1296 | 26.9 kB |
| Leja | 1e-7 | 2.24e-8 | 0.247 | 3332 | 6.1 kB |

The workspace estimate is algorithmic rather than RSS: it counts the dominant
basis/work vectors and projected matrices, excluding problem storage and Python
object overhead.  It exposes a genuine tradeoff: Leja can use substantially less
workspace even when it performs more matvecs.

A nonperiodic loose-tolerance Krogstad case also shows that Leja can beat KIOPS
in wall time despite more matvecs, reinforcing that matvec count alone is not a
sufficient cost metric.

## 5. SciPy as an external executable anchor

For pure exponential actions `exp(hA)v`, Phase 6 compares against
`scipy.sparse.linalg.expm_multiply` (SciPy 1.17.0 in this environment).

For a tridiagonal diffusion operator:

| N | engine | wall s | max error vs SciPy |
|---:|---|---:|---:|
| 256 | SciPy expm_multiply | 0.00162 | reference |
| 256 | KIOPS-style | 0.03197 | 4.71e-14 |
| 256 | Leja | 0.00174 | 5.49e-12 |
| 1024 | SciPy expm_multiply | 0.00223 | reference |
| 1024 | KIOPS-style | 0.06810 | 6.68e-14 |
| 1024 | Leja | 0.00252 | 4.59e-12 |

The conclusion is not that SciPy replaces a phi backend—it computes a different,
simpler kernel—but that PyEXPINT should exploit this mature special case.

## 6. `ScipyKiopsBackend`

The new hybrid backend delegates only pure `phi_0=exp` actions to SciPy and uses
KIOPS for higher phi functions and mixed combinations.

For two fixed Krogstad steps at N=1024:

- KIOPS: 0.152 s, 124 counted KIOPS matvecs;
- SciPy+KIOPS: 0.114 s, 80 counted KIOPS matvecs + 10 SciPy exp calls;
- Leja: 0.092 s.

For HochOst4 at N=1024:

- KIOPS: 0.508 s;
- SciPy+KIOPS: 0.313 s;
- Leja: 0.048 s.

At N=256, however, the hybrid is slower than plain KIOPS because the delegated
calls add overhead.  Therefore the hybrid is another candidate kernel, not a
universal replacement.

## 7. What Phase 6 establishes scientifically

### Established

- A generic backend-independent one-step adaptive driver works across several
  exponential RK methods.
- Matrix-function tolerance must be treated as part of the temporal error budget.
- KIOPS/Leja crossover is real and measurable.
- A calibrated selector can reduce arbitrary hand tuning, but a static two-feature
  rule still has nontrivial regret.
- Workspace and synchronization/orthogonalization costs matter in addition to
  matvec count.
- Mature specialized kernels such as SciPy `expm_multiply` can usefully coexist
  with general phi engines behind the same method API.

### Not established / no claim

- The step-doubling controller is **not** state-of-the-art adaptive ETD; it triples
  method work per trial and is a correctness-oriented baseline.
- There is no direct runtime comparison yet with the official MATLAB KIOPS code.
- There is no direct whole-solver timing comparison with LeXInt because its method
  catalogue centers on EXPRB/EPIRK rather than the EXPINT EGLM catalogue.
- There is no distributed-memory scalability result.
- The calibrated threshold is machine-specific and must not be presented as a
  universal constant.

## 8. Relation to current literature

Modern results strengthen rather than weaken the need for this architecture:

- KIOPS shows the value of augmented phi combinations, incomplete
  orthogonalization and adaptive Krylov parameters.
- LeXInt demonstrates that Leja interpolation is a competitive alternative and
  has an MIT-licensed Python/C++/CUDA codebase.
- Deka & Einkemmer's adaptive-step work shows that maximizing the accuracy-allowed
  step is not necessarily cost-optimal for iterative exponential integrators.
- Deka, Tokman & Einkemmer's KIOPS-vs-Leja comparison reports that performance
  depends strongly on the interaction between integrator and iterative engine,
  with no universal winner.
- Tafolla, Gaudreault & Tokman (2026) show that global synchronization can become
  the dominant Arnoldi bottleneck on distributed systems; Phase 6 does not yet
  address this parallel regime.

## 9. TOMS assessment after Phase 6

The project now has a plausible TOMS-level software/methodology story:

1. a verified 47-method historical EGLM catalogue;
2. a backend-independent operator-action algebra;
3. dense/diagonal/full-Arnoldi/KIOPS-style/Leja/hybrid execution;
4. matrix-free sparse and LinearOperator support;
5. automatic fusion of compatible phi actions;
6. adaptive time stepping with an explicit matrix-action error budget;
7. measurable/calibratable dispatch rather than hard-wired backend choice;
8. reproducible stiff-order and work–precision–workspace experiments.

A manuscript is **not yet ready**.  The principal missing numerical-method item is
an efficient embedded or cost-aware adaptive controller to replace the expensive
step-doubling baseline.  The principal benchmarking item is a controlled external
harness against official KIOPS/LeXInt and, for parallel relevance, modern
low-synchronization Krylov implementations.

## 10. Recommended next phase

Phase 7 should be narrower than Phases 4–6:

1. obtain/implement a published embedded ETD pair (e.g. Krogstad-based ETD34) or a
   carefully derived equivalent;
2. implement a cost-aware controller and compare against Phase-6 step doubling;
3. build direct external comparator harnesses where licensing/runtime permits;
4. run paper-scale CPU/HPC benchmarks with controlled hardware and repeated timings;
5. freeze the public API, documentation and reproducibility scripts;
6. then draft the TOMS manuscript around only the results that survive those tests.
