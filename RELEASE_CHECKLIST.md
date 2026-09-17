# PyEXPINT pre-release checklist

## Blocking before public release

- [ ] Resolve the licensing/copyright status of the historical EXPINT source with the original authors/rightsholder.
- [ ] Choose the final PyEXPINT license after that clarification.
- [ ] Run pinned external comparator benchmarks (`rkstiff`, LeXInt, official KIOPS).
- [ ] Run the controlled CPU/HPC benchmark campaign on stable hardware.
- [ ] Review every public docstring/reference for provenance and mathematical accuracy.

## Software quality

- [x] 47/47 historical method catalogue mapped.
- [x] Historical executable/specification inconsistencies regression-tested.
- [x] Dense, diagonal, sparse and `LinearOperator` execution.
- [x] Multiple phi-action engines.
- [x] Embedded ETD34 adaptive solver.
- [x] Generic reference step-doubling solver.
- [x] 119 automated tests passing at pre-release stage.
- [x] Editable offline installation tested.
- [x] Candidate API freeze documented.
- [ ] Add CI matrix to the eventual GitHub repository.
- [ ] Add release changelog and semantic versioning policy.
- [ ] Add final `CITATION.cff` and `codemeta.json`.

## Paper-quality reproducibility

- [x] Machine-readable historical catalogue.
- [x] Stiff-order benchmark scripts.
- [x] 1-D work/precision/workspace scripts.
- [x] 2-D controlled benchmark script.
- [x] Picasso Slurm benchmark campaign scripts.
- [x] Pinned external comparator manifest.
- [ ] Execute Picasso campaign and archive raw JSON + Slurm metadata.
- [ ] Execute external comparator harnesses from pinned snapshots.
- [ ] Generate final figures/tables from raw benchmark JSON only.

## Claim discipline

- [x] Separate classical, strong stiff and weak/conditional order.
- [x] Do not claim universal backend optimality.
- [x] Do not claim distributed-memory scalability without MPI evidence.
- [x] Do not claim superiority over external packages before pinned runtime comparisons.
