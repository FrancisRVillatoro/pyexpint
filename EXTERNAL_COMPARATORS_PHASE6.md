# Phase 6 — external comparator/provenance boundary

PyEXPINT Phase 6 keeps external algorithms and software clearly separated from
its own implementation.

## KIOPS

Reference algorithm: Gaudreault, Rainwater & Tokman, *Journal of Computational
Physics* 372 (2018), 236–255, DOI 10.1016/j.jcp.2018.06.026.

The official reference project is hosted at:

- https://gitlab.com/stephane.gaudreault/kiops

The project identifies itself as KIOPS (Krylov with Incomplete Orthogonalization
Process Solver) and is distributed under GNU LGPL v2.1.

PyEXPINT's `KiopsBackend` is an independent implementation of the published
augmented-matrix + incomplete-orthogonalization + adaptive-substepping design.
No reference KIOPS source is shipped or translated here.

A direct runtime comparison with the official reference code is **not** part of
Phase 6 because the reference implementation is MATLAB and MATLAB/Octave is not
available in the current validation environment.  Numerical correctness is
instead cross-checked against dense/diagonal reference actions.

## LeXInt

Reference software/publications:

- Deka, Einkemmer & Tokman, SoftwareX 21 (2023), 101302.
- Deka, Moriggl & Einkemmer, SoftwareX 29 (2025), 101949 (GPU extension).
- https://github.com/Pranab-JD/LeXInt

The current public GitHub repository is MIT licensed and contains Python plus
C++/CUDA implementations centered on Leja interpolation and EXPRB/EPIRK
integrators.

PyEXPINT's `LejaBackend` is an independent real-Leja implementation and does not
copy LeXInt code.  A direct whole-integrator timing comparison would not be an
apples-to-apples test because the method catalogues differ.  A future paper
benchmark should compare the matrix-function kernels and shared methods through
a dedicated external harness.

## SciPy

Phase 6 *does* use a directly executable external anchor:
`scipy.sparse.linalg.expm_multiply` for the special action `exp(hA)v`.

The benchmark `benchmarks/scipy_exp_action_phase6.py` compares PyEXPINT's KIOPS
and Leja actions against SciPy for accuracy and wall time.  The new
`ScipyKiopsBackend` can delegate pure exponential actions to SciPy while retaining
KIOPS for higher phi functions.

## 2026 low-synchronization Arnoldi

Tafolla, Gaudreault & Tokman, *Journal of Computational and Applied Mathematics*
482 (2026), 117342, DOI 10.1016/j.cam.2026.117342, demonstrates that global
synchronization in Arnoldi orthogonalization can dominate at distributed-memory
scale and develops low-synchronization alternatives.

PyEXPINT Phase 6 is a single-node/serial validation framework.  It makes **no
parallel-scalability claim**.  Low-synchronization Arnoldi is therefore an
important future comparison/extension rather than functionality claimed here.

## Adaptive time stepping

Phase 6 provides a generic step-doubling controller for one-step methods and
couples the matrix-action tolerance to the requested temporal tolerance.

This is a correctness-oriented baseline, not a claim to state-of-the-art
adaptive efficiency.  Relevant modern work includes Deka & Einkemmer (2022),
*Efficient adaptive step size control for exponential integrators*, which shows
that iterative matrix-function costs depend on the step size and that selecting
the largest accuracy-permitted step can be suboptimal.

For a TOMS paper, PyEXPINT should therefore add an embedded/cost-aware controller
and compare it directly against this Phase-6 step-doubling baseline.
