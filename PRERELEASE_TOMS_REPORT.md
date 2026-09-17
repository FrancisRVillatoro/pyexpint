# PyEXPINT pre-release / TOMS benchmark campaign

## Executive status

This stage is a **pre-release evidence campaign**, not a new numerical-method phase.
The software core remains the Phase-7 architecture and now carries development version
`0.8.0.dev0` for benchmark packaging.

Automated regression status:

```text
119 passed
```

The package also passes `compileall`, editable offline installation and import tests.

## 1. Controlled 2-D development benchmark

Problem: periodic two-dimensional reaction-diffusion with manufactured solution

\[
u(x,y,t)=0.2e^{-t}\sin x\sin y,
\]

using a sparse Kronecker-sum Laplacian and adaptive ETD34.  Each timing point uses one
warm-up followed by three measured repetitions; median and IQR are retained.

| unknowns | rtol | backend | median [s] | IQR [s] | inf error | matvecs |
|---:|---:|---|---:|---:|---:|---:|
| 1024 | 1e-05 | kiops | 0.2479 | 0.0080 | 1.46e-07 | 226 |
| 1024 | 1e-05 | leja | 0.0360 | 0.0075 | 1.46e-07 | 378 |
| 1024 | 1e-05 | hybrid | 0.1560 | 0.0467 | 1.46e-07 | 170 |
| 1024 | 1e-05 | auto | 0.0296 | 0.0420 | 1.46e-07 | 378 |
| 4096 | 1e-05 | kiops | 0.2719 | 0.0199 | 1.46e-07 | 226 |
| 4096 | 1e-05 | leja | 0.0591 | 0.0029 | 1.46e-07 | 382 |
| 4096 | 1e-05 | hybrid | 0.1720 | 0.0114 | 1.46e-07 | 170 |
| 4096 | 1e-05 | auto | 0.0531 | 0.0023 | 1.46e-07 | 382 |
| 16384 | 1e-05 | kiops | 1.2124 | 0.4982 | 1.46e-07 | 226 |
| 16384 | 1e-05 | leja | 0.2430 | 0.0102 | 1.45e-07 | 477 |
| 16384 | 1e-05 | hybrid | 1.2802 | 0.1360 | 1.46e-07 | 170 |
| 16384 | 1e-05 | auto | 0.2558 | 0.0201 | 1.45e-07 | 477 |
| 4096 | 1e-07 | kiops | 0.6479 | 0.0403 | 7.01e-09 | 542 |
| 4096 | 1e-07 | leja | 0.1290 | 0.0030 | 7.00e-09 | 884 |
| 4096 | 1e-07 | hybrid | 0.4038 | 0.0460 | 7.01e-09 | 400 |
| 4096 | 1e-07 | auto | 0.1170 | 0.0051 | 7.00e-09 | 884 |

At `rtol=1e-5` the development-environment speed ratios relative to KIOPS-style are:

| unknowns | Leja/KIOPS speedup | Auto/KIOPS speedup | Hybrid/KIOPS speedup |
|---:|---:|---:|---:|
| 1024 | 6.89x | 8.39x | 1.59x |
| 4096 | 4.60x | 5.12x | 1.58x |
| 16384 | 4.99x | 4.74x | 0.95x |

The important observation is qualitative: as dimension grows, Leja becomes strongly
favorable on this real-spectrum diffusion problem even though it performs more matrix-vector
products.  At 16,384 unknowns Leja is about 5x faster than the present KIOPS-style backend
in this container while matching the temporal error.  The automatic selector chooses Leja
and tracks that regime.

These are **not final paper timings**.  They establish that a 2-D crossover exists and
justify the controlled Picasso campaign.

## 2. What the local 2-D benchmark adds

The earlier crossover result was one-dimensional.  This test shows the same phenomenon for
a genuine 2-D sparse Kronecker operator:

- `matvec` count alone does not predict wall time;
- Arnoldi/IOP costs grow through vector orthogonalization and reductions;
- real-Leja interpolation can remain inexpensive when usable spectral bounds are available;
- the hybrid SciPy+KIOPS strategy is competitive at moderate size but is not monotonically
  better as dimension increases;
- a structure-aware selector can be useful, but its thresholds remain machine-dependent.

## 3. Pinned external comparators

The benchmark manifest now pins:

- `rkstiff`: commit `ccf11f4c8dac3e0b6f8fd23ac357c633c1623a0f`;
- LeXInt: commit `90319e940aec256eec9e340f7469c52054ae33fe`;
- official KIOPS: to be pinned when the MATLAB comparator environment is prepared.

The source trees were inspected through their public repositories, but this execution
container cannot clone/install from the network.  Consequently **no external runtime claim
is made in this stage**.  `external/GET_EXTERNAL_SNAPSHOTS.md` gives the exact offline
workflow for transferring pinned snapshots to a benchmark machine.

## 4. Picasso benchmark campaign

`hpc/picasso_prerelease_array.slurm` defines a 24-case CPU campaign:

\[
N_{side}\in\{64,128,256\},\qquad
rtol\in\{10^{-5},10^{-7}\},
\]

with KIOPS-style, Leja, SciPy+KIOPS and Auto backends.

Each task:

- runs on one CPU thread;
- performs one warm-up and seven measured repetitions;
- emits raw JSON rather than only formatted tables;
- records timing, error, matvecs, nonlinear evaluations and software/environment metadata.

This is the minimum campaign I would regard as suitable for the principal CPU timing table
in a TOMS manuscript.

## 5. Claim discipline after the pre-release audit

The manuscript can already make strong claims about:

1. complete verified 47-method historical reproduction;
2. one common backend-independent EGLM execution model;
3. interchangeable phi-action engines and automatic algebraic fusion;
4. embedded ETD34 adaptivity versus generic step doubling;
5. real backend crossovers and the insufficiency of matvec counts as a universal cost metric;
6. documented historical EXPINT inconsistencies found by machine-verifiable tests.

It **cannot yet** make strong claims that PyEXPINT is faster than `rkstiff`, LeXInt or official
KIOPS, nor that it has distributed-memory scalability.  Those claims remain explicitly
blocked in `TOMS_CLAIMS_MATRIX.md`.

## 6. Release blockers

The most important non-numerical blocker remains the unresolved historical EXPINT
license/copyright status.  Even though PyEXPINT is being implemented independently from
published mathematics, the public release license should be chosen after the authors/rightsholder
clarify the old package status.

Other blockers are external benchmark execution and the controlled Picasso campaign.

## 7. Recommendation

**Do not add more historical integrators before the paper.**  The next useful work is to run
the benchmark package on stable hardware and external comparators, then freeze figures/tables
and draft the manuscript.  Low-synchronization Arnoldi should be added only if distributed
scaling becomes a central claim; otherwise it is better positioned as future work.
