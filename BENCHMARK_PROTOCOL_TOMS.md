# PyEXPINT benchmark protocol for a TOMS submission

## Purpose

The final paper must separate **algorithmic accuracy/work** from **machine-dependent wall time**. Development timings in previous phases are diagnostic only.

## Reproducible timing protocol

For each `(problem, dimension, method, backend, tolerance)` case:

1. fix the exact PyEXPINT commit and external-comparator commit;
2. pin BLAS/OpenMP threading to one thread unless the experiment is explicitly parallel;
3. perform one untimed warm-up;
4. perform at least **7 timed repetitions** for CPU results;
5. report median wall time and IQR; retain all raw repetitions;
6. record error, accepted/rejected time steps, nonlinear evaluations, matrix-vector products, Krylov/Leja degrees, and estimated algorithmic workspace;
7. record Python/NumPy/SciPy versions, CPU model, node, compiler/BLAS information, and environment variables;
8. randomize or cyclically interleave backend order when all competitors execute on the same node;
9. use identical mathematical tolerances where the APIs permit it and explicitly document non-equivalent tolerance semantics;
10. never infer superiority from a single wall-time sample.

## Required benchmark classes

### A. Accuracy / order
- scalar exact problem;
- Hochbruck--Ostermann local and nonlocal stiff-order problems;
- at least one non-periodic PDE.

### B. Matrix-function engines
- pure `exp(A)v` versus SciPy `expm_multiply`;
- common `phi_k(A)v` and `sum phi_k(A)b_k` kernels;
- KIOPS-style, Leja, full Arnoldi and hybrid kernels.

### C. Full integrators
- ETD34/Krogstad adaptive;
- HochOst4 fixed/adaptive-reference cases;
- a representative EGLM multistep family member.

### D. Scale
- 1-D periodic problem;
- 2-D periodic reaction-diffusion;
- 2-D non-periodic or mixed-boundary problem;
- optional distributed/HPC case if communication-aware Krylov is implemented.

## External-comparator policy

External code is executed from pinned snapshots in isolated environments. It is not vendored into PyEXPINT. Results must identify exact commit/version and license.

The primary external comparisons planned are:
- `rkstiff` ETD34/ETD35;
- LeXInt Leja kernels/integrators on mathematically common cases;
- official KIOPS on common phi-combination kernels;
- SciPy `expm_multiply` for the pure exponential action.

## Claim threshold

A performance claim enters the manuscript only if it is reproduced on controlled hardware and the raw JSON data plus scripts are included in the reproducibility repository.

## Canonical release evidence

The release-facing realization of this protocol is stored in
`reproducibility/toms/`.

The retained timing evidence consists of three independent homogeneous Leja80
replicas, each with 24 raw JSON configuration files and the corresponding
analysis products.  All three replicas use the same source manifest:

`ffc203e8eca9e2ad160505f3c10b0bc8fa5e2072ee50ce6a6a4e23c47abe7dda`.

Wall-clock results are reported as hardware-local benchmark observations.
Portable scientific interpretation should rely primarily on accuracy and work
metrics rather than on universal timing rankings.
