# PyEXPINT release checklist

## Blocking before public release

- [x] Reconstruct and verify source provenance.
- [x] Audit third-party software and external comparator boundaries.
- [x] Freeze the PyEXPINT 0.9 public API contract.
- [x] Validate wheel/sdist build and isolated wheel installation.
- [x] Run the full automated test suite: 128 tests passed.
- [x] Adopt MIT as the PyEXPINT software license.
- [x] Adopt CC BY 4.0 for original non-software repository content.

## Software quality

- [x] 47/47 historical method catalogue mapped.
- [x] Historical executable/specification inconsistencies regression-tested.
- [x] Dense, diagonal, sparse, and `LinearOperator` execution.
- [x] Multiple matrix-function backends.
- [x] Embedded ETD34 adaptive solver.
- [x] Generic reference step-doubling solver.
- [x] Public API stability contract.
- [x] Release changelog.
- [x] `CITATION.cff`.
- [x] Contribution guidance.
- [x] Third-party provenance document.
- [x] User installation and quickstart documentation.
- [x] GitHub Actions CI workflow for Python 3.11--3.14.
- [ ] Confirm that the CI matrix passes after publication/push.

## Packaging

- [x] Wheel builds successfully.
- [x] Source distribution builds successfully.
- [x] Wheel installs and imports in an isolated environment.
- [x] Set release-candidate version to `0.9.0rc1`.
- [x] Replace provisional license metadata with MIT.
- [x] Review final package classifiers.

## Paper-quality reproducibility

- [x] Machine-readable historical catalogue.
- [x] Stiff-order validation scripts.
- [x] 1-D work/precision/workspace scripts.
- [x] 2-D controlled benchmark script.
- [x] Picasso Slurm benchmark workflow.
- [x] Pinned external comparator manifest.
- [x] Controlled Picasso timing campaign executed.
- [x] Three independent homogeneous Leja80 replicas retained.
- [x] Raw JSON and analysis products archived.
- [x] Source provenance recorded by SHA-256 manifest.
- [x] Canonical release evidence stored under `reproducibility/toms/`.

## External comparator experiments

Pinned external comparator runs are paper-validation tasks, not software-release
requirements.

- [ ] Run `rkstiff` comparator if a manuscript claim requires it.
- [ ] Run LeXInt comparator if a manuscript claim requires it.
- [ ] Run official KIOPS comparator if a manuscript claim requires it.
- [x] Do not claim superiority over external packages without those measurements.

## Claim discipline

- [x] Separate classical, strong stiff, and weak/conditional order.
- [x] Do not claim universal backend optimality.
- [x] Treat wall-clock benchmark results as hardware-local.
- [x] Do not claim distributed-memory scalability without MPI evidence.
- [x] Preserve external software provenance and licensing boundaries.
