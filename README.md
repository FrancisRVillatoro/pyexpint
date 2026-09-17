# PyEXPINT — exponential integrators in Python

PyEXPINT is an independent, from-scratch modernization of the mathematical
framework of EXPINT for exponential general linear integrators.

**Release candidate:** `0.9.0rc1`

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
- reproducible CPU/HPC benchmark protocol with archived three-replica Picasso evidence.

## Installation

PyEXPINT requires Python 3.11 or newer with NumPy and SciPy.

From a source checkout:

    python -m pip install .

For development and testing:

    python -m pip install -e ".[test]"

See `docs/QUICKSTART.md` for a worked example.

## Validation

```text
128 passed
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
- `docs/QUICKSTART.md`
- `THIRD_PARTY.md`
- `CHANGELOG.md`
- `CITATION.cff`
- `CONTRIBUTING.md`

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

## Licensing

PyEXPINT software is distributed under the MIT License; see `LICENSE`.

Original non-software repository content, including documentation, figures,
tables, benchmark reports, and retained numerical reproducibility data, is
licensed under CC BY 4.0; see `CONTENT-LICENSE.md`.

External software and third-party provenance are documented in
`THIRD_PARTY.md`.


## Picasso v0.8.2 timing workflow

See `docs/picasso/TOMS_TIMING_PROTOCOL.md`.
