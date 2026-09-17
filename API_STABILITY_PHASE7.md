# Candidate public API freeze — PyEXPINT 0.7

Phase 7 freezes the **shape** of the core public API for paper benchmarking.
Names may still gain optional arguments before 1.0, but the following abstractions
should not be broken without a deprecation cycle:

- `SemilinearProblem`
- `MethodSpec`
- `solve_fixed`
- `step_external`
- `AdaptiveOptions`
- `solve_adaptive` (generic step-doubling reference controller)
- `ETD34Options`
- `solve_etd34` (embedded Krogstad 4(3))
- `DenseBackend`
- `DiagonalBackend`
- `KrylovBackend`
- `KiopsBackend`
- `LejaBackend`
- `ScipyKiopsBackend`
- `AutoBackend`
- `CalibratedAutoBackend`
- `SelectorCalibration`

## Explicitly not frozen

- internal expression classes beyond their documented construction helpers;
- backend statistics dictionary details;
- selector calibration schema;
- variable-step multistep/EGLM API (not implemented);
- distributed/MPI backend API.

## Numerical policy

1. A backend failure to converge inside an adaptive one-step method is a rejected
   time step whenever reducing \(h\) can reasonably resolve it.
2. Error-control metadata must distinguish temporal tolerance from matrix-function
   action tolerance.
3. Strong stiff order, weak/conditional order, and classical order remain separate
   metadata fields.
4. External comparator code is not vendored into the core package.
