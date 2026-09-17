# PyEXPINT — pre-release TOMS benchmark candidate

PyEXPINT is an independent, from-scratch modernization of the mathematical
framework of EXPINT for exponential general linear integrators.

**Development version:** `0.8.1.dev0`

## Current status

- complete 47-method historical EXPINT catalogue;
- verified classical/stiff/weak order metadata;
- one generic explicit EGLM execution engine;
- dense, diagonal, sparse and `LinearOperator` operation;
- full-Arnoldi, KIOPS-style, real-Leja and SciPy+KIOPS backends;
- automatic fusion of compatible phi actions;
- fixed-step integration for the historical catalogue;
- generic reference step-doubling adaptivity for one-step methods;
- embedded Krogstad ETD34 adaptive solver with FSAL;
- coupled temporal/matrix-action tolerances;
- calibrated/automatic backend dispatch;
- work, matvec and algorithmic-workspace diagnostics;
- stiff-order/order-reduction, 1-D and 2-D benchmark suites;
- pre-release CPU/HPC benchmark protocol and Picasso Slurm campaign.

## Validation

```text
119 passed
```

The current benchmark candidate also passes source compilation and editable offline installation.

## Release and reproducibility documents

- `BENCHMARK_PROTOCOL_TOMS.md`
- `RELEASE_CHECKLIST.md`
- `API_STABILITY.md`
- `TOMS_CLAIMS_MATRIX.md`
- `TOMS_MANUSCRIPT_BLUEPRINT.md`
- `external/pinned_comparators.json`
- `hpc/README.md`
- `reproducibility/README.md`
- `reproducibility/toms/README.md`

## Canonical reproducibility path

The canonical release-facing backend benchmark evidence is stored under
`reproducibility/toms/`.

It contains three independent homogeneous Leja80 replicas, including the raw
JSON data, analysis products, source manifests, campaign identifiers, and
Slurm job identifiers.

The three replicas were generated from the same 132-file source manifest:

`ffc203e8eca9e2ad160505f3c10b0bc8fa5e2072ee50ce6a6a4e23c47abe7dda`.

Wall-clock timings are machine-local demonstrations of the benchmarking
infrastructure and are not intended as universal backend rankings.

The canonical Picasso workflow is implemented by:

- `hpc/picasso/scripts/02_stage_campaign.sh`
- `hpc/picasso/scripts/03_submit_toms_timing.sh`
- `hpc/picasso/scripts/04_status_campaign.sh`
- `hpc/picasso/scripts/05_collect_campaign.sh`
- `hpc/picasso/slurm/toms_timing_single.slurm`
- `hpc/picasso/python/toms_timing_balanced.py`
- `hpc/picasso/python/analyze_toms_timing.py`

See `BENCHMARK_PROTOCOL_TOMS.md` and
`reproducibility/toms/README.md`.

## Development and validation benchmarks

The scripts under `benchmarks/` and the root-level `phase*.json` and
`prerelease*.json` files are retained as development and validation history.
They are not the canonical final TOMS timing evidence.

## Licensing status

The historical EXPINT package available to this project contains no explicit source
license. PyEXPINT is therefore being developed independently from published mathematical
formulas and documentation while clarification from the original authors/rightsholder is
pending.

This snapshot uses `LicenseRef-Provisional` and should **not** yet be published as a formal
public release.


## Picasso v0.8.2 timing workflow

See `docs/picasso/TOMS_TIMING_PROTOCOL.md`.
