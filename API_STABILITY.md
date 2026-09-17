# Public API stability — PyEXPINT 0.9

PyEXPINT 0.9 introduces a release-facing public API contract.

Public availability and API stability are deliberately distinguished:
some advanced objects remain importable for research convenience without
yet receiving the same compatibility guarantee as the core interface.

## Stable API for the 0.9 series

The following names should not be removed or changed incompatibly within
the 0.9 release series without a deprecation cycle.

### Problems, solutions, and external states

- `SemilinearProblem`
- `Solution`
- `ExternalState`

### Method catalogue

- `MethodSpec`
- `get_method`
- `list_methods`
- `ALL_METHODS`

Individual all-caps method constants are retained as public convenience
aliases.  The canonical catalogue interface is `get_method`,
`list_methods`, and `ALL_METHODS`.

### Fixed and adaptive integration

- `solve_fixed`
- `step_external`
- `AdaptiveOptions`
- `solve_adaptive`
- `ETD34Options`
- `solve_etd34`

### Startup policies

- `ExactStartup`
- `OneStepStartup`

### Expression construction helpers

- `ZERO`
- `I`
- `phi`
- `resolvent`

### Matrix-function backends

- `DenseBackend`
- `DiagonalBackend`
- `KrylovBackend`
- `KrylovOptions`
- `KrylovConvergenceError`
- `KiopsBackend`
- `KiopsOptions`
- `KiopsConvergenceError`
- `LejaBackend`
- `LejaOptions`
- `LejaConvergenceError`
- `ScipyKiopsBackend`
- `AutoBackend`

### Backend selection and instrumentation

- `SelectorCalibration`
- `fit_threshold_selector`
- `CalibratedAutoBackend`
- `estimated_backend_workspace_bytes`

## Public but not yet structurally frozen

The following objects remain importable and may be useful for advanced
research workflows, but their detailed structure is not frozen for the
0.9 series:

- `OperatorExpr`
- `PhiTerm`
- `PhiCombination`
- `ProductExpr`
- `ResolventExpr`
- concrete expression-tree implementation classes not exported at the
  package top level;
- individual all-caps method constants as a catalogue access mechanism;
- backend statistics dictionary keys and nesting;
- the serialized selector-calibration schema.

Removing a currently public object should nevertheless use a deprecation
cycle when practical.

## Not part of the 0.9 API contract

The following are explicitly outside the current compatibility guarantee:

- private names beginning with `_`;
- variable-step multistep/EGLM support, which is not yet implemented;
- distributed/MPI backend interfaces;
- benchmark and Picasso workflow scripts;
- internal JSON schemas other than release reproducibility artifacts.

## Numerical policy

1. A backend failure to converge inside an adaptive one-step method is a
   rejected time step whenever reducing the step size can reasonably
   resolve it.
2. Error-control metadata distinguishes temporal tolerance from
   matrix-function action tolerance.
3. Strong stiff order, weak/conditional order, and classical order remain
   distinct method metadata fields.
4. External comparator code is not vendored into the core package.

## Compatibility policy

The 0.9 series may add optional keyword arguments, new methods, new
backends, and new statistics fields.

Existing stable names, required parameters, return-object semantics, and
documented meanings should not change incompatibly without a deprecation
cycle.
